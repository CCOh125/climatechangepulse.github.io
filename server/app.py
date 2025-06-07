import os
import json
import requests
import uuid
import pandas as pd
import sqlite3
import re
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
CORS(app, resources={r"/*": {"origins": ["https://climatechangepulse.org"]}})

# Global variables
sessions = {}  # Store conversation history
conn = None  # SQLite connection

# Initialize database when module is loaded
def init_app():
    """Initialize the database when the app starts"""
    global conn
    if conn is None:
        initialize_database()

def initialize_database():
    """Initialize in-memory SQLite database with CSV data"""
    global conn
    
    try:
        print("Initializing in-memory SQLite database...")
        
        # Initialize in-memory SQLite database
        conn = sqlite3.connect(':memory:', check_same_thread=False)
        cursor = conn.cursor()

        # Create tables with exact column names from CSV
        cursor.execute('''
            CREATE TABLE disasters (
                "Disaster Type" TEXT,
                "Disaster Subtype" TEXT,
                "Disaster Group" TEXT,
                "Disaster Subgroup" TEXT,
                "Event Name" TEXT,
                "Origin" TEXT,
                "Country" TEXT,
                "Location" TEXT,
                "Latitude" REAL,
                "Longitude" REAL,
                "start_date" TEXT,
                "end_date" TEXT,
                "Total Deaths" REAL,
                "No Affected" REAL,
                "Reconstruction Costs ('000 US$)" REAL,
                "Total Damages ('000 US$)" REAL,
                "CPI" REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE tweets (
                "created_at" TEXT,
                "id" INTEGER,
                "lng" REAL,
                "lat" REAL,
                "topic" TEXT,
                "sentiment" REAL,
                "stance" TEXT,
                "gender" TEXT,
                "temperature_avg" REAL,
                "aggressiveness" TEXT
            )
        ''')

        try:
            # Load data from CSV files into SQLite
            disasters_df = pd.read_csv('data/disasters_FINAL.csv')
            tweets_df = pd.read_csv('data/finalized_tweets.csv')

            # Insert data into SQLite tables
            disasters_df.to_sql('disasters', conn, if_exists='append', index=False)
            tweets_df.to_sql('tweets', conn, if_exists='append', index=False)

            print(f"Loaded {len(disasters_df)} disaster records and {len(tweets_df)} tweet records into database")
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Error loading CSV data: {str(e)}")
            print("Continuing with empty database tables...")
            
        # Commit the changes
        conn.commit()
        
    except Exception as e:
        print(f"Critical error initializing database: {str(e)}")
        conn = None
        raise

def make_openrouter_request(messages):
    """Make a request to OpenRouter API"""
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://climatechangepulse.github.io",
            "X-Title": "Climate Change Pulse",
        },
        data=json.dumps({
            "model": "meta-llama/llama-4-scout:free",
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 4000
        })
    )
    
    response_json = response.json()
    
    if response.status_code != 200:
        error_msg = response_json.get('error', {}).get('message', 'Unknown error')
        error_code = response_json.get('error', {}).get('code', response.status_code)
        raise Exception(f"OpenRouter API Error (Code {error_code}): {error_msg}")
    
    if 'error' in response_json:
        error_msg = response_json['error'].get('message', 'Unknown error')
        error_code = response_json['error'].get('code', 'Unknown code')
        raise Exception(f"OpenRouter API Error (Code {error_code}): {error_msg}")
    
    if 'choices' not in response_json:
        raise Exception(f"Unexpected API response format: {response_json}")
    
    return response_json['choices'][0]['message']['content']

def determine_dataset(query):
    """Determine which dataset is relevant for the query."""
    messages = [
        {
            'role': 'system',
            'content': (
                'Return only "disasters" or "tweets" based on the query. '
                'Use "disasters" for queries about natural disasters, deaths, economic damage. '
                'Use "tweets" for queries about social media, sentiment, aggressiveness.'
            )
        },
        {
            'role': 'user',
            'content': query
        }
    ]
    
    response = make_openrouter_request(messages)
    
    # Clean up response to get just the dataset name
    response = response.strip().lower()
    if response in ['disasters', 'tweets']:
        return response
    return None

def get_sql_expression(query, dataset_name, retry_count=0, max_retries=3, previous_error=None):
    """Generate SQL query for the given question and dataset"""
    schema_info = {
        'disasters': '''Available columns in the disasters table:
- "Disaster Type" (TEXT)
- "Disaster Subtype" (TEXT)
- "Disaster Group" (TEXT)
- "Disaster Subgroup" (TEXT)
- "Event Name" (TEXT)
- "Origin" (TEXT)
- "Country" (TEXT)
- "Location" (TEXT)
- "Latitude" (REAL)
- "Longitude" (REAL)
- "start_date" (TEXT)
- "end_date" (TEXT)
- "Total Deaths" (REAL)
- "No Affected" (REAL)
- "Reconstruction Costs ('000 US$)" (REAL)
- "Total Damages ('000 US$)" (REAL)
- "CPI" (REAL)''',
        'tweets': '''Available columns in the tweets table:
- "created_at" (TEXT) - Format: YYYY-MM-DD HH:MM:SS+00:00
- "id" (INTEGER)
- "lng" (REAL)
- "lat" (REAL)
- "topic" (TEXT)
- "sentiment" (REAL)
- "stance" (TEXT)
- "gender" (TEXT) - Values: "male", "female"
- "temperature_avg" (REAL)
- "aggressiveness" (TEXT) - Values: "aggressive", "not aggressive"'''
    }

    # Build system message with emphasis on proper quoting and error handling
    system_content = f'''You must return ONLY a JSON object with a single key "sql_query" containing the SQL query. Do not include any other text, explanations, or markdown.

{schema_info[dataset_name]}

CRITICAL RULES:
1. ALL column names with spaces or special characters MUST be enclosed in double quotes
2. Column names shown above are the EXACT names - use them exactly as shown including quotes
3. For text columns with specific values (like "aggressiveness"), use CASE statements to convert them to numbers if needed

Example correct queries:
- SELECT "Event Name", "Total Deaths" FROM disasters ORDER BY "Total Deaths" DESC LIMIT 1
- SELECT "gender", AVG(CASE WHEN "aggressiveness" = 'aggressive' THEN 1 ELSE 0 END) as avg_aggressiveness FROM tweets GROUP BY "gender"'''

    # Add previous error information if this is a retry
    if previous_error and retry_count > 0:
        system_content += f'''

PREVIOUS ERROR (attempt {retry_count}): {previous_error}
Please fix the SQL query based on this error. Pay special attention to column name quoting and syntax.'''

    messages = [
        {
            'role': 'system',
            'content': system_content
        },
        {
            'role': 'user',
            'content': query
        }
    ]
    
    content = make_openrouter_request(messages)
    print(f"Raw API response for SQL generation: {repr(content)}")  # Debug print
    return json.loads(content)['sql_query']

def answer_with_table(user_query, sql_expression, dataset_name):
    """Execute SQL query and generate natural language answer"""
    try:
        # Execute the SQL query and get the actual results
        result_table = pd.read_sql_query(sql_expression, conn)
        
        # If we got results, ask LLM to explain them
        if not result_table.empty:
            messages = [
                {
                    'role': 'system',
                    'content': '''Answer the question based on the data shown. 
                    
IMPORTANT: Do not mention limitations about "only one data point" or similar phrases when the query is specifically designed to return filtered results (like finding the top/highest/most/least of something). The data shown is the intended result of the query, not a limitation of the dataset.

Focus on directly answering the question with the information provided.
If there is no data, you can assume the query failed to return any results, so you should say there was no data found.'''
                },
                {
                    'role': 'user',
                    'content': (
                        f"Question: {user_query}\n"
                        f"Data:\n{result_table.to_string(index=False)}"
                    )
                }
            ]
            return make_openrouter_request(messages)
        return "No data found matching your query."
    except Exception as e:
        return f"QUERY_INCORRECT: {str(e)}"

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
        # Ensure database is initialized
        global conn
        if conn is None:
            print("Database not initialized, initializing now...")
            initialize_database()
            if conn is None:
                return jsonify({'error': 'Database initialization failed'}), 500
        
        # Cleanup old sessions
        cleanup_old_sessions()
        
        # Get or create session
        session_id = get_session_id()
        
        # Get user message
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        if session_id not in sessions:
            # Initialize new session
            sessions[session_id] = {
                "messages": [],
                "last_access": datetime.now()
            }
        else:
            # Update last access time
            sessions[session_id]["last_access"] = datetime.now()
        
        # Add user message to history
        sessions[session_id]["messages"].append({"role": "user", "content": user_message})
        
        print(f"Processing query: {user_message}")
        
        # Determine which dataset to use
        dataset_name = determine_dataset(user_message)
        if not dataset_name:
            response_text = "I couldn't determine whether your question is about disasters or social media data. Please rephrase your question to be more specific about natural disasters (earthquakes, floods, etc.) or social media sentiment/reactions."
            sessions[session_id]["messages"].append({"role": "assistant", "content": response_text})
            
            resp = jsonify({
                'response': response_text,
                'conversation_id': session_id,
                'context_type': 'unknown'
            })
            resp.set_cookie('session_id', session_id, max_age=3600, httponly=True, samesite='Lax')
            return resp
            
        print(f"Using {dataset_name} dataset")
        
        # Generate and execute SQL query with retries
        max_retries = 3
        retry_count = 0
        previous_error = None
        assistant_message = None
        
        while retry_count < max_retries:
            try:
                sql_expr = get_sql_expression(user_message, dataset_name, retry_count, max_retries, previous_error)
                print(f"Generated SQL query: {sql_expr}")
                
                # Execute query and get results
                answer = answer_with_table(user_message, sql_expr, dataset_name)
                
                # Check if the answer indicates a problem with the query
                if answer.startswith("QUERY_INCORRECT:"):
                    print(f"Query needs revision (attempt {retry_count + 1}/{max_retries}): {answer[16:]}")
                    previous_error = answer
                    retry_count += 1
                else:
                    print("Query executed successfully!")
                    assistant_message = answer
                    break
                    
            except Exception as e:
                print(f"Error executing query (attempt {retry_count + 1}/{max_retries}): {e}")
                previous_error = str(e)
                retry_count += 1
                
        if assistant_message is None:
            assistant_message = "I encountered difficulties analyzing your question. Please try rephrasing it or asking a different question about the climate change data."
        
        # Add assistant response to history
        sessions[session_id]["messages"].append({"role": "assistant", "content": assistant_message})
        
        # Create response with session cookie
        resp = jsonify({
            'response': assistant_message,
            'conversation_id': session_id,
            'context_type': dataset_name
        })
        
        # Set session cookie
        resp.set_cookie('session_id', session_id, max_age=3600, httponly=True, samesite='Lax')
        
        return resp
    
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Initialize database when module loads
init_app()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))) 