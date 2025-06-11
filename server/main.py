from flask import request, jsonify, Response
from config import app, db
from models import Contact, User
from video_streamer import VideoStreamer, CameraBusyException
from sensor import (
    calibrate_start, calibrate_weight_read, calibrate_set_known_weight,
    calibrate_status, read_sensor_loop, set_hx
)
from hx711_gpiod import HX711
import csv
import os
import time
import threading
from thread_report import report_gpiochip0_users

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# -- Recording controller --
recording_lock = threading.Lock()
recording_streamer = None
recording_filename = None
video_streamer_instance = None

# -- Sensor thread --
sensor_thread = None
sensor_thread_running = False

# --- Instantiate HX711 and inject into sensor module ---
DOUT_PIN = 21
PD_SCK_PIN = 20
GPIO_CHIP = '/dev/gpiochip0'
hx = HX711(dout_pin=DOUT_PIN, pd_sck_pin=PD_SCK_PIN, chip=GPIO_CHIP)
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
    global sensor_thread, sensor_thread_running
    if sensor_thread_running:
        return jsonify({"message": "Sensor reading loop already running."}), 400
    sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    sensor_thread.start()
    sensor_thread_running = True
    return jsonify({"message": "Sensor reading loop started."}), 200

@app.route('/sensor/status', methods=['GET'])
def sensor_status():
    return jsonify({"running": sensor_thread_running}), 200

# Stream Routes
@app.route('/video_feed')
def video_feed():
    global video_streamer_instance
    def generate():
        try:
            streamer = VideoStreamer()
            video_streamer_instance = streamer
        except CameraBusyException:
            # Instead of streaming, yield a single error frame
            yield (b'--frame\r\nContent-Type: text/plain\r\n\r\n'
                   b'Camera is currently in use by another user.\r\n')
            return

        try:
            while True:
                frame = streamer.get_jpeg()
                if frame:
                    yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                else:
                    time.sleep(0.1)
        finally:
            streamer.release()
            if video_streamer_instance == streamer:
                video_streamer_instance = None
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_streamer, recording_filename, video_streamer_instance
    with recording_lock:
        if video_streamer_instance is not None:
            video_streamer_instance.release()
            video_streamer_instance = None
            time.sleep(0.1)

        if recording_streamer is not None:
            return jsonify({"message": "Recording already in progress"}), 400
        filename = request.json.get('filename', 'output.avi')
        recording_streamer = VideoStreamer()
        recording_streamer.start_recording(filename)
        recording_filename = filename
    return jsonify({"message": "Recording started", "filename": filename})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording_streamer, recording_filename
    with recording_lock:
        if recording_streamer is None:
            return jsonify({"message": "No recording in progress"}), 400
        recording_streamer.stop_recording()
        recording_streamer.release()
        recording_streamer = None
        filename = recording_filename
        recording_filename = None
    return jsonify({"message": "Recording stopped", "filename": filename})

@app.route("/api/users", methods=["GET"])
def users():
    return jsonify(
        {
            "users": [
                "user1",
                "user2",
                "user3"
            ]
        }
    )

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Optionally start the thread automatically, or require /sensor/start API call
    # sensor_thread = threading.Thread(target=read_sensor_loop, daemon=True)
    # sensor_thread.start()

    # Use host if expose to network
    #app.run(debug=True, port=8080, host="0.0.0.0", use_reloader=False)

    app.run(debug=True, port=8080, use_reloader=False)