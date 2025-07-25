from flask import request, jsonify, Response
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
from thread_report import report_gpiochip0_users

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


@app.route("/list-csv", methods=["GET"])
def list_csv():
    # Ensure the data directory exists
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # List only .csv files
    csv_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.csv')]
    return jsonify({"files": csv_files})


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
    cal_status = calibrate_status()
    return jsonify({"running": sensor.sensor_thread_running,
                    "last_calibration":calibration_ratio}), 200

@app.route('/sensor/value', methods=['GET'])
def sensor_value():
    if not sensor.sensor_thread_event.is_set():
        return jsonify({"message": "Sensor is not running."}), 400
    value = sensor.get_sensor_value()
    if value is None:
        return jsonify({"message": "No sensor value available."}), 204
    return jsonify({"value": value}), 200

@app.route('/video/start', methods=['POST'])
def start_video():
    global video_streamer, video_mode, video_filename
    data = request.json or {}
    mode = data.get('mode')  # "livestream" or "record"
    timestamp_str = time.strftime('%Y-%m-%d')
    filename = data.get('filename', f"{timestamp_str}.avi")
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
        video_streamer = None
        stopped_mode = video_mode
        stopped_filename = video_filename
        video_mode = None
        video_filename = None
    return jsonify({"message": f"{stopped_mode.capitalize()} stopped.", "mode": stopped_mode, "filename": stopped_filename}), 200
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Optionally start the thread automatically, or require /sensor/start API call
    # sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    # sensor_thread.start()

    # Use host if expose to network
    #app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False)

    app.run(debug=True, port=8080, use_reloader=False)