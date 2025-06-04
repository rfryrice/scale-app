from config import db

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

    def to_json(self):
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password,
        }
