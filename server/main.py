from flask import request, jsonify, send_file, Response
from config import app, db
from models import Contact, User
from video_streamer import VideoStreamer, CameraBusyException
from sensor import (
    calibrate_start, calibrate_weight_read, calibrate_set_known_weight,
    calibrate_status, set_hx, load_calibration_ratio
)
import sensor
from hx711_gpiod import HX711
import csv
import os
import time
import threading
import re
from system_monitor import system_monitor
#from thread_report import report_gpiochip0_users

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# --- Video state ---
video_lock = threading.Lock()
video_streamer = None
video_mode = None  # None, 'livestream', or 'record'
video_filename = None

# -- Sensor thread --
sensor_thread = None

# --- Instantiate HX711 and inject into sensor module ---
DOUT_PIN = 21
PD_SCK_PIN = 20
GPIO_CHIP = '/dev/gpiochip0'
hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN, chip=GPIO_CHIP)

# Load calibration on startup
calibration_ratio = load_calibration_ratio()
if calibration_ratio is not None:
    hx.set_scale(calibration_ratio)
    print(f"[DEBUG] Loaded and applied calibration ratio on startup: {calibration_ratio}")

set_hx(hx)  # Make hx available in sensor module

@app.route("/register", methods=["POST"])
def register():
    data = request.json
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
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        return jsonify({"message": "Login successful!"}), 200
    else:
        return jsonify({"message": "Invalid username or password"}), 401

@app.route("/contacts", methods=["GET"])
def get_contacts():
    contacts = Contact.query.all()
    json_contacts = list(map(lambda x: x.to_json(), contacts))
    return jsonify({"contacts": json_contacts})

@app.route("/create_contact", methods=["POST"])
def create_contact():
    username = request.json.get("username")
    password = request.json.get("password")

    if not username or not password:
        return (
            jsonify({"message": "You mus include a username and password"}),
            400,
        )
    
    new_user = Contact(username=username, password=password)
    try:
        db.session.add(new_user)
        db.session.commit
    except Exception as e:
        return jsonify({"message": str(e)}), 400
    
    return jsonify({"message": "User created!"}), 201

@app.route("/update_contact/<int:user_id>", methods=["PATCH"])
def update_contact(user_id):
    contact = Contact.query.get(user_id)

    if not contact:
        return jsonify({"message": "User not found"}), 404
    
    data = request.json
    contact.username = data.get("username", contact.username)
    contact.password = data.get("password", contact.password)

    db.session.commit()

    return jsonify({"message": "User updated!"}), 200

@app.route("/delete_contact/<int:user_id>", methods=["DELETE"])
def delete_contact(user_id):
    contact = Contact.query.get(user_id)

    if not contact:
        return jsonify({"message": "User not found"}), 404
    
    db.session.delete(contact)
    db.session.commit()

    return jsonify({"message": "User deleted!"}), 200

# System status endpoint
@app.route('/system-status', methods=['GET'])
def system_status():
    return jsonify(system_monitor.get_data()), 200

# Called from ListData component
@app.route("/list-files", methods=["GET"])
def list_files():
    # Ensure the data directory exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # List .csv files in the data directory
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

    # List .mp4 files in the data/videos directory
    videos_dir = os.path.join(DATA_DIR, "videos")
    if not os.path.exists(videos_dir):
        os.makedirs(videos_dir)
    mp4_files = [os.path.join("videos", f) for f in os.listdir(videos_dir) if f.endswith('.mp4')]

    # Return both lists, with relative paths
    return jsonify({
        "csv_files": csv_files,
        "mp4_files": mp4_files
   })

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]

    # Get filename from query parameter, default to first csv file if not present
    filename = request.args.get('file')
    if not filename or filename not in csv_files:
        if csv_files:
            filename = csv_files[0]
        else:
            return jsonify({"data": [], "csv_files": []})
    

    data = []
    with open(os.path.join(DATA_DIR, filename), newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            # Adapt to your column names, here we assume 'Timestamp' and 'Value'
            for row in reader:
                data.append({
                    'Timestamp': row['Timestamp'],
                    'Value': float(row['Value'])
                })
    return jsonify({"data": data, "csv_files": csv_files})

# Sensor Calibration API (multi-step for frontend)
@app.route('/sensor/calibrate/start', methods=['POST'])
def api_calibrate_start():
    if calibrate_start():
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 200
    else:
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 400

@app.route('/sensor/calibrate/read_weight', methods=['POST'])
def api_calibrate_weight_read():
    if calibrate_weight_read():
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 200
    else:
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 400

@app.route('/sensor/calibrate/set_known_weight', methods=['POST'])
def api_calibrate_set_known_weight():
    weight = request.json.get("weight")
    if calibrate_set_known_weight(weight):
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 200
    else:
        return jsonify({"message": calibrate_status()["message"], "step": calibrate_status()["step"]}), 400

@app.route('/sensor/calibrate/status', methods=['GET'])
def api_calibrate_status():
    return jsonify(calibrate_status()), 200

# Sensor recoding thread control
@app.route('/sensor/start', methods=['POST'])
def start_sensor_loop():
    global sensor_thread
    if sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor reading loop already running."}), 400
    print("[DEBUG] /sensor/start: Creating and starting sensor thread...")
    sensor.sensor_thread_running = True
    sensor.sensor_thread_event.set()
    sensor_thread = threading.Thread(target=sensor.read_sensor_loop, daemon=True)
    sensor_thread.start()
    return jsonify({"message": "Sensor reading loop started."}), 200

@app.route('/sensor/stop', methods=['POST'])
def stop_sensor_loop():
    global sensor_thread
    if not sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor is not running."}), 400
    # Set a flag to stop the loop (implement this in your read_sensor_loop)
    sensor.sensor_thread_event.clear()
    sensor_thread = None
    filename = f"{time.strftime('%Y-%m-%d')}.csv"
    return jsonify({"message": "Sensor reading loop stopped.", "filename": filename}), 200

@app.route('/sensor/status', methods=['GET'])
def sensor_status():
    return jsonify({"running": sensor.sensor_thread_running,
                    "last_calibration":calibration_ratio}), 200

@app.route('/sensor/value', methods=['GET'])
def sensor_value():
    global sensor_thread
    if not sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor is not running."}), 400
    value = sensor.get_sensor_value()
    if value is None:
        return jsonify({"message": "No sensor value available."}), 204
    return jsonify({"value": value}), 200

@app.route('/sensor/tare', methods=['POST'])
def sensor_tare():
    try:
        # Tare the sensor (zero the scale)
        if hasattr(sensor, 'tare_sensor'):
            sensor.tare_sensor()
        elif hasattr(hx, 'tare'):
            hx.tare()
        else:
            return jsonify({"message": "Tare function not implemented."}), 501
        return jsonify({"message": "Sensor tared (zeroed)."}), 200
    except Exception as e:
        return jsonify({"message": f"Error taring sensor: {e}"}), 500

@app.route('/video/start', methods=['POST'])
def start_video():
    global video_streamer, video_mode, video_filename
    data = request.json or {}
    mode = data.get('mode')  # "livestream" or "record"
    timestamp_str = time.strftime('%Y-%m-%d')
    filename = data.get('filename', f"{timestamp_str}.mp4")
    with video_lock:
        if video_streamer is not None:
            return jsonify({"message": f"Video already running in {video_mode} mode."}), 400
        try:
            video_streamer = VideoStreamer()
            if mode == 'record':
                video_streamer.start_recording(filename)
                video_mode = 'record'
                video_filename = filename
            elif mode == 'livestream':
                video_mode = 'livestream'
                video_filename = None
            else:
                video_streamer.release()
                video_streamer = None
                return jsonify({"message": "Invalid mode."}), 400
            return jsonify({"message": f"{mode.capitalize()} started.", "mode": video_mode, "filename": video_filename}), 200
        except CameraBusyException:
            return jsonify({"message": "Camera is currently in use by another user."}), 503

@app.route('/video/stop', methods=['POST'])
def stop_video():
    global video_streamer, video_mode, video_filename
    with video_lock:
        if video_streamer is None:
            return jsonify({"message": "No video in progress."}), 400
        try:
            if video_mode == 'record':
                print("[DEBUG] Stopping video recording...")
                video_streamer.stop_recording()
            print("[DEBUG] Releasing video streamer...")
            video_streamer.release()
            print("[DEBUG] Video streamer released.")
        except Exception as e:
            print(f"[ERROR] Exception during video stop/release: {e}")
            return jsonify({"message": f"Error stopping video: {e}"}), 500
        
        # Check if recording completed successfully (for recording mode only)
        stopped_mode = video_mode
        stopped_filename = video_filename
        recording_success = True
        
        if stopped_mode == 'record' and video_streamer:
            recording_success = video_streamer.recording_completed_successfully()
            print(f"[DEBUG] Recording completed successfully: {recording_success}")
            
        video_streamer = None
        video_mode = None
        video_filename = None
    
    # Log any recording issues
    if stopped_mode == 'record' and not recording_success:
        print(f"[ERROR] Recording did not complete successfully: {stopped_filename}")
    
    return jsonify({
        "message": f"{stopped_mode.capitalize()} stopped.", 
        "mode": stopped_mode, 
        "filename": stopped_filename, 
        "success": recording_success if stopped_mode == 'record' else True
    }), 200


@app.route('/video/status', methods=['GET'])
def video_status():
    running = video_streamer is not None
    return jsonify({
        "running": running,
        "mode": video_mode,
        "filename": video_filename
    }), 200

@app.route('/video_feed')
def video_feed():
    global video_streamer
    def generate():
        streamer = video_streamer
        if streamer is None:
            yield (b'--frame\r\nContent-Type: text/plain\r\n\r\n'
                   b"No stream running.\r\n")
            return
        try:
            while True:
                frame = streamer.get_jpeg()
                if frame:
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    time.sleep(0.1)
        except Exception:
            pass
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video-file')
def video_file():
    file = request.args.get('file')
    print(f"[DEBUG] /video-file requested filename: {file}")
    if not file or not file.endswith('.mp4'):
        return jsonify({'error': 'Invalid file'}), 400
    video_path = os.path.join(DATA_DIR, file)
    print(f"[DEBUG] /video-file resolved video_path: {video_path}")
    if not os.path.isfile(video_path):
        return jsonify({'error': 'File not found'}), 404

    range_header = request.headers.get('Range', None)
    size = os.path.getsize(video_path)
    if not range_header:
        # No Range header, send the whole file
        return send_file(video_path, mimetype='video/mp4')

    # Parse Range header for exact byte range
    byte1, byte2 = 0, None
    m = re.search(r'bytes=(\d+)-(\d*)', range_header)
    if m:
        g = m.groups()
        byte1 = int(g[0])
        if g[1]:
            byte2 = int(g[1])
        else:
            byte2 = size - 1
    else:
        # Malformed Range header, ignore and send whole file
        return send_file(video_path, mimetype='video/mp4')

    # Clamp values to file size
    byte2 = min(byte2, size - 1)
    if byte1 > byte2:
        return Response(status=416)  # Requested Range Not Satisfiable

    length = byte2 - byte1 + 1
    with open(video_path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    rv = Response(data, 206, mimetype='video/mp4', direct_passthrough=True)
    rv.headers.add('Content-Range', f'bytes {byte1}-{byte2}/{size}')
    rv.headers.add('Accept-Ranges', 'bytes')
    rv.headers.add('Content-Length', str(length))
    return rv

@app.route('/sync/start', methods=['POST'])
def start_sensor_and_video():
    global sensor_thread, video_streamer, video_mode, video_filename
    # Debug: Log incoming request
    print("[DEBUG] /sync/start called")
    print(f"[DEBUG] Request JSON: {request.json}")
    # Start sensor loop
    sensor_response = None
    try:
        if not sensor.sensor_thread_event.is_set():
            print("[DEBUG] Sensor thread not running. Starting...")
            sensor.sensor_thread_running = True
            sensor.sensor_thread_event.set()
            sensor_thread = threading.Thread(target=sensor.read_sensor_loop, daemon=True)
            sensor_thread.start()
            sensor_response = {"message": "Sensor reading loop started."}
        else:
            print("[DEBUG] Sensor thread already running.")
            sensor_response = {"message": "Sensor reading loop already running."}
    except Exception as e:
        print(f"[ERROR] Exception starting sensor thread: {e}")
        sensor_response = {"error": str(e)}

    # Start video recording
    data = request.json or {}
    timestamp_str = time.strftime('%Y-%m-%d')
    filename = data.get('filename', f"{timestamp_str}.mp4")
    video_resp = None
    try:
        with video_lock:
            if video_streamer is not None:
                print(f"[DEBUG] Video already running in {video_mode} mode. Filename: {video_filename}")
                video_resp = {"message": f"Video already running in {video_mode} mode.", "mode": video_mode, "filename": video_filename}
            else:
                try:
                    print(f"[DEBUG] Starting video recording. Filename: {filename}")
                    video_streamer = VideoStreamer()
                    video_streamer.start_recording(filename)
                    video_mode = 'record'
                    video_filename = filename
                    video_resp = {"message": "Recording started.", "mode": video_mode, "filename": video_filename}
                except CameraBusyException:
                    print("[ERROR] Camera is currently in use by another user.")
                    video_resp = {"message": "Camera is currently in use by another user."}
                except Exception as ve:
                    print(f"[ERROR] Exception starting video recording: {ve}")
                    video_resp = {"error": str(ve)}
    except Exception as e:
        print(f"[ERROR] Exception in video lock block: {e}")
        video_resp = {"error": str(e)}

    print(f"[DEBUG] Sensor response: {sensor_response}")
    print(f"[DEBUG] Video response: {video_resp}")
    return jsonify({"sensor": sensor_response, "video": video_resp}), 200


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Optionally start the thread automatically, or require /sensor/start API call
    # sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    # sensor_thread.start()

    # Use host if expose to network
    #app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False)

    app.run(debug=True, port=8080, use_reloader=False)