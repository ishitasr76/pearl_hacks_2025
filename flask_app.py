import os
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from chatbot import BudgetBot


# Set the environment variable to your credentials file path
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = r"C:\Users\harsh\PearlHacks\pearl_hacks_2025\budgetbot-451019-10fa89cb499c.json"


# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db = SQLAlchemy(app)
budget_bot = BudgetBot()


# Models definition
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
   
    user = db.relationship('User', backref=db.backref('expenses', lazy=True))
    event = db.relationship('Event', backref=db.backref('expenses', lazy=True))


# Routes
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chatbot/message', methods=['POST'])
def handle_message():
    try:
        data = request.json
        user_id = data.get('user_id', 'default_user')
        message = data.get('message')


        # Convert string user_id to int if it's a number
        try:
            user_id = int(user_id)
        except ValueError:
            # For demo purposes, create a default user if user_id is not numeric
            default_user = User.query.filter_by(name='Default User').first()
            if not default_user:
                default_user = User(name='Default User', email='default@example.com')
                db.session.add(default_user)
                db.session.commit()
            user_id = default_user.id


        # Get user's expenses for context
        user_expenses = Expense.query.filter_by(paid_by=user_id).all()
        total_spent = sum(expense.amount for expense in user_expenses)


        # Process message through Dialogflow
        response = budget_bot.process_message(
            message,
            user_id=str(user_id),  # Convert back to string for Dialogflow
            context={
                'total_spent': total_spent,
                'recent_expenses': [
                    {
                        'description': expense.description,
                        'amount': expense.amount
                    } for expense in user_expenses[-5:]  # Last 5 expenses
                ]
            }
        )


        return jsonify({
            'response': response,
            'total_spent': total_spent
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'response': f'Sorry, I encountered an error: {str(e)}'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)