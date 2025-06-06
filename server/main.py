from flask import request, jsonify
from config import app, db
from models import Contact, User
import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')


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



    data = []
    # Assume the CSV file is in the server directory and has columns: 'x', 'y'
    with open("data/timestamped_data_js.csv", newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Convert x and y to numbers if needed
            data.append({
                'x': row['Timestamp'],
                'y': float(row['Value'])
            })

            
    return jsonify({"data": data})



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