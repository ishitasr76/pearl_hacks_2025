import os
from dotenv import load_dotenv
import google.generativeai as genai


# Load environment variables from .env file
load_dotenv()


class BudgetBot:
    def __init__(self):
        # Retrieve the Google API key from environment variables
        google_api_key = os.getenv('GOOGLE_API_KEY')


        if not google_api_key:
            raise ValueError("Missing GOOGLE_API_KEY in environment variables.")


        # Configure the Gemini Generative AI API using the API key
        genai.configure(api_key=google_api_key)
       
        # Initialize the Gemini Generative Model (Gemini AI)
        self.model = genai.GenerativeModel('gemini-pro')  # Replace 'gemini-pro' with the actual model ID you are using
        self.chat = self.model.start_chat(history=[])


    def process_message(self, text, user_id, context=None):
        """Process a message through Gemini AI and enhance it with custom logic."""
        # Send the user's message to Gemini AI for processing
        response = self.chat.send_message(text, stream=True)
        message = ""
        for chunk in response:
            if chunk.text:
                message += chunk.text
       
        # Enhanced response based on intent
        intent = self._detect_intent(text)


        if intent == "check_spending":
            return self._enhance_spending_response(message, context)
        elif intent == "get_budget_advice":
            return self._provide_budget_advice(message, context)
       
        # return message  # Return the response from Gemini AI
        return f"Received your message: {text}, Context: {context}, User ID: {user_id}"

    def _detect_intent(self, text):
        """Detect intent from the input message."""
        if "spending" in text.lower():
            return "check_spending"
        elif "budget" in text.lower():
            return "get_budget_advice"
        return "unknown"


    def _enhance_spending_response(self, response, context):
        """Enhance spending-related responses with specific details."""
        if not context or 'total_spent' not in context:
            return response
       
        total_spent = context['total_spent']
        recent_expenses = context.get('recent_expenses', [])
       
        # Add more personalized context to the response
        enhanced_response = f"{response}\n\nYou've spent ${total_spent:.2f} in total.\n"
       
        if recent_expenses:
            enhanced_response += "\nRecent expenses:\n"
            for expense in recent_expenses:
                enhanced_response += f"- {expense['description']}: ${expense['amount']:.2f}\n"
               
        return enhanced_response


    def _provide_budget_advice(self, response, context):
        """Provide personalized budgeting advice based on spending patterns."""
        if not context or 'total_spent' not in context:
            return response
       
        total_spent = context['total_spent']
       
        advice = f"{response}\n\n"
       
        if total_spent > 5000:
            advice += "It looks like your spending is relatively high. Consider:\n"
            advice += "- Setting up a monthly budget\n"
            advice += "- Tracking expenses by category\n"
            advice += "- Identifying non-essential expenses\n"
        elif total_spent > 2000:
            advice += "Your spending seems moderate. Tips to consider:\n"
            advice += "- Look for areas to reduce regular expenses\n"
            advice += "- Set aside some money for savings\n"
        else:
            advice += "Your spending appears to be well-controlled. To maintain this:\n"
            advice += "- Continue tracking your expenses\n"
            advice += "- Consider setting up an emergency fund\n"
           
        return advice


    def analyze_spending(self, user_id, timeframe='month'):
        """Analyze user spending patterns over a given timeframe."""
        # Placeholder for actual database analysis, modify to fit your DB structure
        analysis = {
            'timeframe': timeframe,
            'total_spent': 0,
            'categories': {},
            'recommendations': []
        }
       
        # Example analysis logic (modify as needed)
        if timeframe == 'month':
            # Example: Assume the user spent $3500 this month
            analysis['total_spent'] = 3500
            analysis['categories'] = {
                "food": 1200,
                "transport": 800,
                "entertainment": 500,
                "miscellaneous": 1000
            }
            analysis['recommendations'] = ["Consider cutting down on entertainment expenses", "Look into cheaper transport options"]
       
        return analysis
