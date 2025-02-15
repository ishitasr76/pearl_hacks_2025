from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'  # Use PostgreSQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models9
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False)
    creator_name = db.Column(db.String(100), nullable=False)
    total_people = db.Column(db.Integer, nullable=False)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    paid_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

# @app.route('/auth/signup', methods=['POST'])
# def signup_user():
#     data = request.form  # Use request.form instead of request.json for form submission

#     if not data or 'email' not in data or 'password' not in data or 'name' not in data:
#         return jsonify({'message': 'Missing required fields'}), 400
    
#     # Check if the email already exists
#     existing_user = User.query.filter_by(email=data['email']).first()
#     if existing_user:
#         return jsonify({'message': 'Email already exists'}), 400

#     # Create new user and save to DB
#     new_user = User(name=data['name'], email=data['email'])
#     db.session.add(new_user)
#     db.session.commit()
#     return jsonify({'message': 'User created successfully'}), 201

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

    # Check if required fields are present in the request
    if not data or 'event_name' not in data or 'creator_name' not in data or 'total_people' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    # Check if an event with the same name already exists
    existing_event = Event.query.filter_by(event_name=data['event_name']).first()

    if existing_event:
        return jsonify({'message': 'A trip with this event name already exists. Please choose a different name.'}), 409

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

@app.route('/trip', methods=['GET'])
def trip_form():
    trip_name = request.args.get('trip_name')  # Retrieve the trip name from query parameters
    if trip_name:
        # Try to get the trip details from the database
        trip = Event.query.filter_by(event_name=trip_name).first()
        
        if trip:
            return f'You are accessing the trip with name: {trip.event_name} and the creater is:{trip.creator_name}'
        else:
            return f'Trip with the name "{trip_name}" not found.'
    else:
        return 'No trip name provided!'



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
