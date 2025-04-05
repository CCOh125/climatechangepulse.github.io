import os
import json
import requests
import uuid
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get OpenRouter API Key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")

# Initialize Flask
app = Flask(__name__, static_url_path='', static_folder='.')
app.secret_key = os.urandom(24)  # For session management
CORS(app, resources={r"/*": {"origins": ["http://localhost:7100", "https://climatechangepulse.github.io"]}})

# Global variables
sessions = {}  # Store conversation history

def load_system_prompt():
    """Create system prompt with CSV file data"""
    system_prompt = """You are an assistant analyzing climate change data, focusing on the intersection of natural disasters and social media reactions.

Key information about the datasets:

1. Disasters Dataset:
   - Contains records of natural disasters worldwide
   - Includes information about disaster types, locations, dates, impacts
   - Major categories include floods, storms, earthquakes, droughts, etc.
   - Covers events from 2000-2020

2. Climate Change Twitter Dataset:
   - Contains tweets related to climate change
   - Includes sentiment analysis, topics, dates, and user information
   - Major topics include policy reactions, climate denial, activism
   - Significant spikes in tweet volume correspond to major climate events

Your task is to answer questions about climate change, focusing on:
1. How natural disasters impact public sentiment
2. Trends in climate discussions over time
3. Regional differences in climate discourse
4. Correlations between disaster types and social media reactions

Use specific examples when possible, but acknowledge when you don't have sufficient data.
"""
    return system_prompt

def get_session_id():
    """Get a session ID from the request or create a new one"""
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        session_id = str(uuid.uuid4())
    return session_id

def cleanup_old_sessions():
    """Remove sessions older than 1 hour to prevent memory leaks"""
    current_time = datetime.now()
    for session_id in list(sessions.keys()):
        if current_time - sessions[session_id]["last_access"] > timedelta(hours=1):
            del sessions[session_id]

@app.route('/')
def serve_index():
    return jsonify({'Response': 200, 'Message': 'Welcome to the Climate Change Pulse API!'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        # Cleanup old sessions
        cleanup_old_sessions()
        
        # Get or create session
        session_id = get_session_id()
        
        if session_id not in sessions:
            # Initialize new session
            system_prompt = load_system_prompt()
            
            sessions[session_id] = {
                "messages": [
                    {"role": "system", "content": system_prompt}
                ],
                "last_access": datetime.now()
            }
        else:
            # Update last access time
            sessions[session_id]["last_access"] = datetime.now()
        
        # Get user message
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        # Add user message to history
        sessions[session_id]["messages"].append({"role": "user", "content": user_message})
        
        # Get only the last 10 messages to avoid exceeding context limits
        messages_to_send = [sessions[session_id]["messages"][0]]  # Always include system prompt
        messages_to_send.extend(sessions[session_id]["messages"][-9:] if len(sessions[session_id]["messages"]) > 10 else sessions[session_id]["messages"][1:])
        
        # Call OpenRouter API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://climatechangepulse.github.io",
                "X-Title": "Climate Change Pulse",
            },
            data=json.dumps({
                "model": "google/gemini-2.5-pro-exp-03-25:free",  # High context window model
                "messages": messages_to_send,
                "temperature": 0.1,
                "max_tokens": 1000
            })
        )
        
        if response.status_code != 200:
            print(f"Error from OpenRouter: {response.text}")
            return jsonify({'error': f'API Error: {response.status_code}'}), 500
        
        result = response.json()
        assistant_message = result['choices'][0]['message']['content']
        
        # Add assistant response to history
        sessions[session_id]["messages"].append({"role": "assistant", "content": assistant_message})
        
        # Create response with session cookie
        resp = jsonify({
            'response': assistant_message,
            'conversation_id': session_id
        })
        
        # Set session cookie
        resp.set_cookie('session_id', session_id, max_age=3600, httponly=True, samesite='Lax')
        
        return resp
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 