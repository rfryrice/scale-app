from flask import request, jsonify, send_file, Response
from config import app, db
from flask_cors import CORS
from models import User
from video_streamer import VideoStreamer, CameraBusyException
from sensor import (
    calibrate_start, calibrate_weight_read, calibrate_set_known_weight,
    calibrate_status, set_hx, load_calibration_ratio
)
import sensor
from hx711_gpiod import HX711
import csv
import os
import re
import time
import threading
from system_monitor import system_monitor
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# Accept requests from the configured frontend origin (set FRONTEND_ORIGIN in .env for remote deployments)
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
CORS(app, resources={r"/*": {"origins": FRONTEND_ORIGIN}})

# ── HX711 setup ───────────────────────────────────────────────────────────────
DOUT_PIN   = 21
PD_SCK_PIN = 20
GPIO_CHIP  = '/dev/gpiochip0'
hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN, chip=GPIO_CHIP)

calibration_ratio = load_calibration_ratio()
if calibration_ratio is not None:
    hx.set_scale(calibration_ratio)

set_hx(hx)

# ── Shared state ──────────────────────────────────────────────────────────────
video_lock     = threading.Lock()
video_streamer = None
video_mode     = None   # None | 'livestream' | 'record'
video_filename = None
sensor_thread  = None


# =============================================================================
# Auth
# =============================================================================

@app.route("/register", methods=["POST"])
def register():
    data     = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"message": "Username already exists"}), 400

    new_user = User(username=username)
    new_user.set_password(password)
    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "User registered!"}), 201


@app.route("/login", methods=["POST"])
def login():
    data     = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return jsonify({"message": "Login successful!"}), 200
    return jsonify({"message": "Invalid username or password"}), 401


# =============================================================================
# Dashboard
# =============================================================================

@app.route("/list-files", methods=["GET"])
def list_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

    videos_dir = os.path.join(DATA_DIR, "videos")
    os.makedirs(videos_dir, exist_ok=True)
    mp4_files = [
        os.path.join("videos", f)
        for f in os.listdir(videos_dir)
        if f.endswith('.mp4')
    ]
    return jsonify({"csv_files": csv_files, "mp4_files": mp4_files})


@app.route("/dashboard", methods=["GET"])
def dashboard():
    os.makedirs(DATA_DIR, exist_ok=True)
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

    filename = request.args.get('file')
    if not filename or filename not in csv_files:
        if csv_files:
            filename = csv_files[0]
        else:
            return jsonify({"data": [], "csv_files": []})

    data = []
    with open(os.path.join(DATA_DIR, filename), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            data.append({'Timestamp': row['Timestamp'], 'Value': float(row['Value'])})

    return jsonify({"data": data, "csv_files": csv_files})


@app.route('/system-status', methods=['GET'])
def system_status():
    return jsonify(system_monitor.get_data()), 200


# =============================================================================
# Sensor Control
# =============================================================================

@app.route('/sensor/status', methods=['GET'])
def sensor_status():
    return jsonify({"running": sensor.sensor_thread_running,
                    "last_calibration": calibration_ratio}), 200


@app.route('/sensor/value', methods=['GET'])
def sensor_value():
    if not sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor is not running."}), 400
    value = sensor.get_sensor_value()
    if value is None:
        return jsonify({"message": "No sensor value available."}), 204
    return jsonify({"value": value}), 200


@app.route('/sensor/start', methods=['POST'])
def start_sensor_loop():
    global sensor_thread
    if sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor already running."}), 400
    sensor.sensor_thread_running = True
    sensor.sensor_thread_event.set()
    sensor_thread = threading.Thread(target=sensor.read_sensor_loop, daemon=True)
    sensor_thread.start()
    return jsonify({"message": "Sensor started."}), 200


@app.route('/sensor/stop', methods=['POST'])
def stop_sensor_loop():
    global sensor_thread
    if not sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor is not running."}), 400
    sensor.sensor_thread_event.clear()
    sensor_thread = None
    filename = f"{time.strftime('%Y-%m-%d')}.csv"
    return jsonify({"message": "Sensor stopped.", "filename": filename}), 200


@app.route('/sensor/tare', methods=['POST'])
def sensor_tare():
    try:
        if hasattr(sensor, 'tare_sensor'):
            sensor.tare_sensor()
        elif hasattr(hx, 'tare'):
            hx.tare()
        else:
            return jsonify({"message": "Tare not implemented."}), 501
        return jsonify({"message": "Sensor tared."}), 200
    except Exception as e:
        return jsonify({"message": f"Tare error: {e}"}), 500


@app.route('/sensor/calibrate/start', methods=['POST'])
def api_calibrate_start():
    ok     = calibrate_start()
    status = calibrate_status()
    return jsonify({"message": status["message"], "step": status["step"]}), (200 if ok else 400)


@app.route('/sensor/calibrate/read_weight', methods=['POST'])
def api_calibrate_weight_read():
    ok     = calibrate_weight_read()
    status = calibrate_status()
    return jsonify({"message": status["message"], "step": status["step"]}), (200 if ok else 400)


@app.route('/sensor/calibrate/set_known_weight', methods=['POST'])
def api_calibrate_set_known_weight():
    weight = request.json.get("weight")
    ok     = calibrate_set_known_weight(weight)
    status = calibrate_status()
    return jsonify({"message": status["message"], "step": status["step"]}), (200 if ok else 400)


# =============================================================================
# Video Control
# =============================================================================

@app.route('/video/status', methods=['GET'])
def video_status():
    return jsonify({"running": video_streamer is not None,
                    "mode": video_mode,
                    "filename": video_filename}), 200


@app.route('/video/start', methods=['POST'])
def start_video():
    global video_streamer, video_mode, video_filename
    data     = request.json or {}
    mode     = data.get('mode')  # 'record' | 'livestream'
    filename = data.get('filename', f"{time.strftime('%Y-%m-%d')}.mp4")

    with video_lock:
        if video_streamer is not None:
            return jsonify({"message": f"Video already running in {video_mode} mode."}), 400
        try:
            video_streamer = VideoStreamer()
            if mode == 'record':
                video_streamer.start_recording(filename)
                video_mode     = 'record'
                video_filename = filename
            elif mode == 'livestream':
                video_mode     = 'livestream'
                video_filename = None
            else:
                video_streamer.release()
                video_streamer = None
                return jsonify({"message": "Invalid mode. Use 'record' or 'livestream'."}), 400
        except CameraBusyException:
            video_streamer = None
            return jsonify({"message": "Camera is in use."}), 503

    return jsonify({"message": f"{mode.capitalize()} started.",
                    "mode": video_mode, "filename": video_filename}), 200


@app.route('/video/stop', methods=['POST'])
def stop_video():
    global video_streamer, video_mode, video_filename
    with video_lock:
        if video_streamer is None:
            return jsonify({"message": "No video in progress."}), 400
        try:
            if video_mode == 'record':
                video_streamer.stop_recording()
            video_streamer.release()
        except Exception as e:
            return jsonify({"message": f"Error stopping video: {e}"}), 500

        stopped_mode     = video_mode
        stopped_filename = video_filename
        video_streamer   = None
        video_mode       = None
        video_filename   = None

    return jsonify({"message": f"{stopped_mode.capitalize()} stopped.",
                    "mode": stopped_mode, "filename": stopped_filename}), 200


@app.route('/video_feed')
def video_feed():
    def generate():
        streamer = video_streamer
        if streamer is None:
            yield b'--frame\r\nContent-Type: text/plain\r\n\r\nNo stream running.\r\n'
            return
        try:
            while True:
                frame = streamer.get_jpeg()
                if frame:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    time.sleep(0.1)
        except Exception:
            pass
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video-file')
def video_file():
    file = request.args.get('file')
    if not file or not file.endswith('.mp4'):
        return jsonify({'error': 'Invalid file'}), 400

    # Prevent path traversal
    video_path = os.path.realpath(os.path.join(DATA_DIR, file))
    if not video_path.startswith(os.path.realpath(DATA_DIR) + os.sep):
        return jsonify({'error': 'Invalid file path'}), 400
    if not os.path.isfile(video_path):
        return jsonify({'error': 'File not found'}), 404

    size         = os.path.getsize(video_path)
    range_header = request.headers.get('Range')

    if not range_header:
        return send_file(video_path, mimetype='video/mp4')

    m = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if not m:
        return send_file(video_path, mimetype='video/mp4')

    byte1 = int(m.group(1))
    byte2 = int(m.group(2)) if m.group(2) else size - 1
    byte2 = min(byte2, size - 1)

    if byte1 > byte2:
        return Response(status=416)

    length = byte2 - byte1 + 1
    with open(video_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range',  f'bytes {byte1}-{byte2}/{size}')
    rv.headers.add('Accept-Ranges',  'bytes')
    rv.headers.add('Content-Length', str(length))
    return rv


# =============================================================================
# Sync — start sensor + video recording together
# =============================================================================

@app.route('/sync/start', methods=['POST'])
def start_sensor_and_video():
    global sensor_thread, video_streamer, video_mode, video_filename
    data = request.json or {}

    # Start sensor
    if not sensor.sensor_thread_event.is_set():
        sensor.sensor_thread_running = True
        sensor.sensor_thread_event.set()
        sensor_thread = threading.Thread(target=sensor.read_sensor_loop, daemon=True)
        sensor_thread.start()
        sensor_resp = {"message": "Sensor started."}
    else:
        sensor_resp = {"message": "Sensor already running."}

    # Start video recording
    filename   = data.get('filename', f"{time.strftime('%Y-%m-%d')}.mp4")
    video_resp = {}
    with video_lock:
        if video_streamer is not None:
            video_resp = {"message": f"Video already running in {video_mode} mode.",
                          "mode": video_mode, "filename": video_filename}
        else:
            try:
                video_streamer = VideoStreamer()
                video_streamer.start_recording(filename)
                video_mode     = 'record'
                video_filename = filename
                video_resp     = {"message": "Recording started.",
                                  "mode": video_mode, "filename": video_filename}
            except CameraBusyException:
                video_streamer = None
                video_resp     = {"message": "Camera is in use."}
            except Exception as e:
                video_streamer = None
                video_resp     = {"error": str(e)}

    return jsonify({"sensor": sensor_resp, "video": video_resp}), 200


# =============================================================================
# Entry point
# =============================================================================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False)