from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'  # Use PostgreSQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Routes
@app.route('/')
def home():
    return "Welcome to the Event Expense Splitter API!"

@app.route('/auth/signup', methods=['POST'])
def signup_user():
    data = request.json
    new_user = User(name=data['name'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/auth/login', methods=['POST'])
def login_user():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()
    if user and user.password == data['password']:  # Assuming password checking is done here
        return jsonify({'access_token': 'some-token'})  # Replace 'some-token' with real token logic
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/event/create', methods=['POST'])
def create_event():
    data = request.json
    new_event = Event(name=data['name'], created_by=data['user_id'])
    db.session.add(new_event)
    db.session.commit()
    return jsonify({'message': 'Event created successfully', 'event_id': new_event.id})

@app.route('/expense/add', methods=['POST'])
def add_expense():
    data = request.json
    new_expense = Expense(
        event_id=data['event_id'],
        description=data['description'],
        amount=data['amount'],
        paid_by=data['paid_by']
    )
    db.session.add(new_expense)
    db.session.commit()
    return jsonify({'message': 'Expense added successfully'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
