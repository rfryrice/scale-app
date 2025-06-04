from flask import request, jsonify
from config import app, db
from models import Contact

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
    
    new_contact = Contact(username=username, password=password)
    try:
        db.session.add(new_contact)
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