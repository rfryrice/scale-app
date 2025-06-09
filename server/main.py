from flask import request, jsonify, Response
from config import app, db
from models import Contact, User
from video_streamer import VideoStreamer, CameraBusyException
import csv
import os
import time
import threading

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

# -- Recording controller --
recording_lock = threading.Lock()
recording_streamer = None
recording_filename = None

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



# ROUTES TO MAKE:
# /data
# /line

# Sensor Routes
@app.route('/video_feed')
def video_feed():
    def generate():
        try:
            streamer = VideoStreamer()
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
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording_streamer, recording_filename
    with recording_lock:
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

    app.run(debug=True, port=8080)