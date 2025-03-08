"""
chatbot_server.py communicates with climatechangepulse.org, giving responses to user queries.
"""

import os
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

if not API_KEY:
    raise ValueError("OPENAI_API_LEY not found in .env file")

# Configure the API
client = OpenAI(api_key = os.environ.get('OPENAI_API_KEY'))

# Initialize Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

@app.route('/')
def home():
    return jsonify({'Response': 200, 'Message': 'Welcome to the climatechangepulse.org server!'})

@app.route('/dog')
def cat():
    return jsonify({'dog': 'My favorite dog is the Great Dane.'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        # The user's message
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        chat_completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                  'role': 'user',
                  'content': user_message  
                }
            ]
        )
        
        return jsonify({'response': chat_completion.choices[0].message.content})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Create static folder and copy index.html there
    # os.makedirs('static', exist_ok=True)
    # import shutil
    # shutil.copy('index.html', 'static/index.html')
    
    # Run the Flask app
    app.run(debug=True) 