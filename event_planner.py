from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_app import BudgetBot

app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Many-to-Many Association Table (No Model Class Needed)
user_event = db.Table('user_event',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

# User Model
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=True)

# Event Model
class Event(db.Model):
    __tablename__ = 'event'
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(100), nullable=False, unique=True)
    creator_name = db.Column(db.String(100), nullable=False)
    total_people = db.Column(db.Integer, nullable=False)
    participants = db.relationship('User', secondary=user_event, backref=db.backref('events', lazy='dynamic'))

    def add_participant(self, user):
        if user not in self.participants:
            self.participants.append(user)
            db.session.commit()

    def remove_participant(self, user):
        if user in self.participants:
            self.participants.remove(user)
            db.session.commit()

    def update_total_people(self):
        self.total_people = len(self.participants)
        db.session.commit()

# Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(100), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('event.id'), nullable=False)


# Drop and recreate all tables in the database (only for development)
with app.app_context():
    db.drop_all()  # Drops all existing tables
    db.create_all()  # Creates the tables according to the updated models


# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/<html_page>')
def render_page(html_page):
    try:
        return render_template(html_page)
    except:
        return "Page not found", 404

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json(force=True)
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing email or password'}), 400

    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    return jsonify({'message': 'Login successful', 'access_token': 'fake-token'}), 200

@app.route('/auth/signup', methods=['POST'])
def signup():
    data = request.get_json(force=True)
    if not data or 'name' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'message': 'Email already in use'}), 409

    hashed_password = generate_password_hash(data['password'])
    new_user = User(name=data['name'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'Account created successfully'}), 201

@app.route('/event/create', methods=['POST'])
def create_event():
    data = request.json
    if not data or 'event_name' not in data or 'creator_name' not in data or 'total_people' not in data or 'attendees' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    existing_event = Event.query.filter_by(event_name=data['event_name']).first()
    if existing_event:
        return jsonify({'message': 'An event with this name already exists. Please choose a different name.'}), 409

    new_event = Event(
        event_name=data['event_name'],
        creator_name=data['creator_name'],
        total_people=data['total_people']
    )

    attendees = []
    for attendee_data in data['attendees']:
        user = User.query.filter_by(email=attendee_data['email']).first()
        if not user:
            user = User(name=attendee_data['name'], email=attendee_data['email'])
            db.session.add(user)
            db.session.commit()

        attendees.append(user)

    new_event.participants.extend(attendees)
    db.session.add(new_event)
    db.session.commit()

    return jsonify({'message': 'Event created successfully', 'event_id': new_event.id}), 201

@app.route('/expenses/add', methods=['POST'])
def add_expense():
    data = request.json
    if 'event_id' not in data:
        return jsonify({'message': 'Missing event_id'}), 400

    expense = Expense(
        name=data['name'],
        description=data['description'],
        amount=data['amount'],
        date=data['date'],
        event_id=data['event_id']  # Assign the expense to a trip
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({'message': 'Expense added successfully'}), 201


@app.route('/expenses', methods=['GET'])
def get_expenses():
    event_id = request.args.get('event_id')
    if not event_id:
        return jsonify({'message': 'Missing event_id'}), 400

    expenses = Expense.query.filter_by(event_id=event_id).all()
    expenses_list = []
    balances = {}

    for expense in expenses:
        expenses_list.append({
            'name': expense.name,
            'description': expense.description,
            'amount': expense.amount,
            'date': expense.date
        })

        # Update balances dictionary
        if expense.name in balances:
            balances[expense.name] += expense.amount
        else:
            balances[expense.name] = expense.amount

    return jsonify({'expenses': expenses_list, 'balances': balances})



@app.route('/trip', methods=['GET'])
def trip_form():
    trip_name = request.args.get('trip_name')
    if trip_name:
        trip = Event.query.filter_by(event_name=trip_name).first()
        if trip:
            return render_template('current_trip.html', trip=trip)
        else:
            return f'Trip with the name "{trip_name}" not found.'
    else:
        return 'No trip name provided!'

@app.route('/chat/message', methods=['POST'])
def chat():
    budget_bot = BudgetBot()
    """Route to handle chat interactions."""
    data = request.get_json()

    if not data or 'user_id' not in data or 'text' not in data:
        return jsonify({'error': 'Invalid input, please provide user_id and text.'}), 400

    user_id = data['user_id']
    text = data['text']
    context = data.get('context', None)  # Optional context for the bot

    # Process the message through BudgetBot
    response = budget_bot.process_message(text, user_id, context)

    return jsonify({'response': response}), 200

if __name__ == '__main__':
    app.run(debug=True)
