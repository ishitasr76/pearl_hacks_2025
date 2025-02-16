from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

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
    
    event_id = data['event_id']
    name = data['name']
    
    # Get the event and check if it exists
    event = Event.query.get(event_id)
    if not event:
        return jsonify({'message': 'Event not found'}), 404
    
    # Check if the person adding the expense is a participant in the event
    is_participant = False
    for participant in event.participants:
        if participant.name == name:
            is_participant = True
            break
    
    if not is_participant:
        return jsonify({'message': 'Only event participants can add expenses'}), 403
    
    # If validation passes, create the expense
    expense = Expense(
        name=data['name'],
        description=data['description'],
        amount=float(data['amount']),
        date=data['date'],
        event_id=data['event_id']
    )
    
    db.session.add(expense)
    db.session.commit()
    
    return jsonify({'message': 'Expense added successfully'}), 201


@app.route('/expenses', methods=['GET'])
def get_expenses():
    event_id = request.args.get('event_id')
    if not event_id:
        return jsonify({'message': 'Missing event_id'}), 400

    event = Event.query.get(event_id)
    if not event:
        return jsonify({'message': 'Event not found'}), 404

    expenses = Expense.query.filter_by(event_id=event_id).all()
    
    # Get all participants
    participants = {user.name: 0 for user in event.participants}
    
    # Initialize balance tracking - this tracks how much each person has actually paid
    paid_amounts = {name: 0 for name in participants}
    
    # Calculate the total expense and update who paid what
    total_expense = 0
    for expense in expenses:
        total_expense += expense.amount
        # Add the expense amount to what this person has paid
        if expense.name in paid_amounts:
            paid_amounts[expense.name] += expense.amount
    
    # Calculate each person's fair share
    num_participants = len(participants)
    if num_participants == 0:
        return jsonify({'message': 'No participants in the event'}), 400
    
    share_per_person = total_expense / num_participants
    
    # Calculate final debt (negative means they owe money, positive means they're owed money)
    debt = {}
    for person in participants:
        # What they paid minus what they should have paid
        debt[person] = round(paid_amounts.get(person, 0) - share_per_person, 2)
    
    # Calculate who owes who
    settlements = []
    debtors = [(person, amount) for person, amount in debt.items() if amount < 0]
    creditors = [(person, amount) for person, amount in debt.items() if amount > 0]
    
    # Sort by absolute amount (largest debt/credit first)
    debtors.sort(key=lambda x: x[1])  # Already negative, so this puts largest debt first
    creditors.sort(key=lambda x: x[1], reverse=True)  # Largest credit first
    
    # Match debtors with creditors
    debtor_idx = 0
    creditor_idx = 0
    
    while debtor_idx < len(debtors) and creditor_idx < len(creditors):
        debtor, debt_amount = debtors[debtor_idx]
        creditor, credit_amount = creditors[creditor_idx]
        
        # The amount to transfer is the minimum of the debt and credit
        transfer_amount = min(abs(debt_amount), credit_amount)
        
        if transfer_amount > 0:
            settlements.append({
                "from": debtor,
                "to": creditor,
                "amount": round(transfer_amount, 2)
            })
        
        # Update remaining amounts
        debtors[debtor_idx] = (debtor, debt_amount + transfer_amount)
        creditors[creditor_idx] = (creditor, credit_amount - transfer_amount)
        
        # Move to next person if their debt/credit has been fully handled
        if abs(debtors[debtor_idx][1]) < 0.01:  # Using 0.01 to handle floating point errors
            debtor_idx += 1
        if abs(creditors[creditor_idx][1]) < 0.01:
            creditor_idx += 1
    
    expenses_list = [{
        'name': expense.name,
        'description': expense.description,
        'amount': expense.amount,
        'date': expense.date
    } for expense in expenses]
    
    return jsonify({
        'expenses': expenses_list, 
        'debt': debt,
        'settlements': settlements,
        'total_people': num_participants,
        'total_expense': total_expense,
        'share_per_person': round(share_per_person, 2)
    })



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

if __name__ == '__main__':
    app.run(debug=True)