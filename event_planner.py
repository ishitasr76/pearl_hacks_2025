from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)


CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'  # Use PostgreSQL in production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Many-to-Many Association Table (No Model Class Needed)
user_event = db.Table('user_event',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

# User Model
class User(db.Model):
    __tablename__ = 'user'  # Explicit table name to avoid confusion
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)  # Store hashed password

    # Many-to-Many Relationship with Event
    # events = db.relationship('Event', secondary=user_event, backref=db.backref('participants', lazy='dynamic'))

# Event Model
class Event(db.Model):
    __tablename__ = 'event'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False, unique=True)
    creator_name = db.Column(db.String(100), nullable=False)
    total_people = db.Column(db.Integer, nullable=False)

    # Many-to-many relationship with the User class
    participants = db.relationship('User', secondary=user_event, backref=db.backref('events', lazy='dynamic'))

    # Optional: Function to add a user to the event
    def add_participant(self, user):
        if user not in self.participants:
            self.participants.append(user)
            db.session.commit()

    # Optional: Function to remove a user from the event
    def remove_participant(self, user):
        if user in self.participants:
            self.participants.remove(user)
            db.session.commit()

    # Optionally add a method to handle logic for counting participants
    def update_total_people(self):
        self.total_people = len(self.participants)
        db.session.commit()



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

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True)

    # Validate request data
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing email or password'}), 400

    user = User.query.filter_by(email=data['email']).first()

    # Check if user exists and password is correct
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    return jsonify({'message': 'Login successful', 'access_token': 'fake-token'}), 200


@app.route('/auth/signup', methods=['POST'])
def signup():
    data = request.get_json(force=True)

    # Check for missing fields
    if not data or 'name' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'message': 'Email already in use'}), 409

    # Hash the password before storing
    hashed_password = generate_password_hash(data['password'])

    # Create new user
    new_user = User(name=data['name'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Account created successfully'}), 201


@app.route('/event/create', methods=['POST'])
def create_event():
    data = request.json

    # Check if required fields are present in the request
    if not data or 'event_name' not in data or 'creator_name' not in data or 'total_people' not in data or 'attendees' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    # Check if an event with the same name already exists
    existing_event = Event.query.filter_by(event_name=data['event_name']).first()
    if existing_event:
        return jsonify({'message': 'An event with this name already exists. Please choose a different name.'}), 409

    # Create a new event with provided data
    new_event = Event(
        event_name=data['event_name'],
        creator_name=data['creator_name'],
        total_people=data['total_people']
    )

    # Process the attendees and create or find users based on email
    attendees = []
    for attendee_data in data['attendees']:
        # Try to find the user by email
        user = User.query.filter_by(email=attendee_data['email']).first()
        if not user:
            # If the user doesn't exist, create a new one
            user = User(name=attendee_data['name'], email=attendee_data['email'])
            db.session.add(user)
            db.session.commit()  # Commit to get the user ID

        # Add the user to the attendees list
        attendees.append(user)

    # Associate the attendees with the event (many-to-many relationship)
    new_event.participants.extend(attendees)  # Use the `participants` relationship to add attendees

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
            # Render the 'current_trip.html' template and pass the trip object to it
            return render_template('current_trip.html', trip=trip)
        else:
            return f'Trip with the name "{trip_name}" not found.'
    else:
        return 'No trip name provided!'
    



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
