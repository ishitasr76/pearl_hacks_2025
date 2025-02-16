import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import date
from werkzeug.security import generate_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, JWTManager
import os

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'  # Use PostgreSQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["JWT_SECRET_KEY"] = "your_secret_key"
jwt = JWTManager(app)

db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    expenses = db.relationship('Expense', backref='payer', lazy=True)
    
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    creator_name = db.Column(db.String(100), nullable=False)
    total_people = db.Column(db.Integer, nullable=False)
    expenses = db.relationship('Expense', backref='event', lazy=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)

# Drop and recreate all tables in the database (only for development)
with app.app_context():
    db.drop_all()  # Drops all existing tables
    db.create_all()  # Creates the tables according to the updated models

# Routes
@app.route('/')
def home():
    return render_template('index.html')  # Default homepage

@app.route('/<html_page>')
def render_page(html_page):
    try:
        return render_template(html_page)  # Dynamically render requested page
    except:
        return "Page not found", 404  # Handle missing templates gracefully

@app.route('/auth/signup', methods=['POST'])
def signup_user():
    data = request.form  # Use request.form instead of request.json for form submission

    if not data or 'email' not in data or 'password' not in data or 'name' not in data:
        return jsonify({'message': 'Missing required fields'}), 400
    
    # Check if the email already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'message': 'Email already exists'}), 400

    # Create new user and save to DB
    hashed_password = generate_password_hash(data['password'], method='pbkdf2:sha256')
    new_user = User(name=data['name'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/auth/login', methods=['POST'])
def login_user():
    data = request.json
    user = User.query.filter_by(email=data['email']).first()

    if user and check_password_hash(user.password, data['password']):
        access_token = create_access_token(identity=user.id)
        return jsonify({'access_token': access_token})
    
    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/event/create', methods=['POST'])
def create_event():
    data = request.json

    # Check if required fields are present in the request
    if not data or 'event_name' not in data or 'creator_name' not in data or 'total_people' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    # Create a new event with provided data
    new_event = Event(
        event_name=data['event_name'],
        creator_name=data['creator_name'],
        total_people=data['total_people']
    )

    # Add the new event to the database and commit
    db.session.add(new_event)
    db.session.commit()

    # Return a success message with the event ID
    return jsonify({'message': 'Event created successfully', 'event_id': new_event.id}), 201

@app.route('/expense/add', methods=['POST'])
@jwt_required()
def add_expense():
    user_id = get_jwt_identity()  # Get logged-in user
    data = request.json

    new_expense = Expense(
        event_id=data['event_id'],
        description=data['description'],
        amount=data['amount'],
        paid_by=user_id,  # Securely use the logged-in user ID
        date=date.today()
    )

    db.session.add(new_expense)
    db.session.commit()
    export_to_csv()

    return jsonify({'message': 'Expense added successfully'})

def export_to_csv():
    expenses = Expense.query.all()
    if not expenses:  # Check if no expenses exist
        return

    expenses_data = [{
        'id': expense.id,
        'event_id': expense.event_id,
        'description': expense.description,
        'amount': expense.amount,
        'paid_by': expense.paid_by,
        'date': expense.date.strftime('%Y-%m-%d')
    } for expense in expenses]

    df = pd.DataFrame(expenses_data)
    df.to_csv('expenses.csv', index=False)


@app.route('/export_csv', methods=['GET'])
def export_csv():
    # Ensure that the CSV file is available
    if not os.path.exists('expenses.csv'):
        return jsonify({'message': 'No data to export'}), 404
    
    # Send the file to the user
    return send_file('expenses.csv', as_attachment=True)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
