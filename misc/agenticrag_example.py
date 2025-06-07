import sqlite3
import requests
from dotenv import load_dotenv
import os
import json
import re
import pandas as pd

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")

# Initialize in-memory SQLite database
conn = sqlite3.connect(':memory:')
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

# Load data from CSV files into SQLite
disasters_df = pd.read_csv('../data/disasters_FINAL.csv')
tweets_df = pd.read_csv('../data/finalized_tweets.csv')

# Insert data into SQLite tables
disasters_df.to_sql('disasters', conn, if_exists='append', index=False)
tweets_df.to_sql('tweets', conn, if_exists='append', index=False)

# Print sample of each dataset
print("Disasters dataset sample:")
print(pd.read_sql_query("SELECT * FROM disasters LIMIT 5", conn))
print("\nTweets dataset sample:")
print(pd.read_sql_query("SELECT * FROM tweets LIMIT 5", conn))

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
            "max_tokens": 1000
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
    print("Raw API response:", repr(content))  # Debug print
    return json.loads(content)['sql_query']

def answer_with_table(user_query, sql_expression, dataset_name):
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
        return "No data found"
    except Exception as e:
        return f"QUERY_INCORRECT: {str(e)}"

if __name__ == '__main__':
    user_input = input('What is your question? ')
    
    # First determine which dataset to use
    dataset_name = determine_dataset(user_input)
    if not dataset_name:
        print("Could not determine which dataset to use. Please rephrase your question.")
        exit()
        
    print(f"Using {dataset_name} dataset")
    
    max_retries = 3
    retry_count = 0
    previous_error = None
    
    while retry_count < max_retries:
        sql_expr = get_sql_expression(user_input, dataset_name, retry_count, max_retries, previous_error)
        print(f"\nGenerated SQL query:\n{sql_expr}\n")
        
        try:
            # Execute query and get results
            answer = answer_with_table(user_input, sql_expr, dataset_name)
            
            # Check if the answer indicates a problem with the query
            if answer.startswith("QUERY_INCORRECT:"):
                print(f"Query needs revision (attempt {retry_count + 1}/{max_retries}):")
                print(f"Reason: {answer[16:]}\n")
                previous_error = answer
                retry_count += 1
            else:
                print("Query executed successfully!")
                print(f"""--------------------\n\n{answer}\n\n--------------------""")
                break
                
        except Exception as e:
            print(f"Error executing query (attempt {retry_count + 1}/{max_retries}):")
            print(f"Error: {e}")
            print(f"Query: {sql_expr}\n")
            previous_error = str(e)
            retry_count += 1
            
    if retry_count >= max_retries:
        print("\nFailed to generate a valid query after maximum retries.")
        print("Please try rephrasing your question.")
