import pandas as pd
import requests
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY not found in environment variables")

# Load datasets
'''CHANGE FILE PATH TO MATCH YOUR LOCAL FILE PATH'''
disasters_df = pd.read_csv('../data/disasters_FINAL.csv')
tweets_df = pd.read_csv('../data/finalized_tweets.csv')

# Print sample of each dataset
print("Disasters dataset sample:")
print(disasters_df.head())
print("\nTweets dataset sample:")
print(tweets_df.head())

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
    print(f'Response: {response_json}')
    
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
                'You are an AI that determines which dataset to use based on a query. '
                'Return a JSON object with key "dataset" and value either "disasters" or "tweets". '
                'Use "disasters" for queries about natural disasters, deaths, economic damage, etc. '
                'Use "tweets" for queries about social media, sentiment, aggressiveness, etc. '
                'Here are the columns in each dataset:\n'
                f'Disasters: {", ".join(disasters_df.columns)}\n'
                f'Tweets: {", ".join(tweets_df.columns)}'
            )
        },
        {
            'role': 'user',
            'content': query
        }
    ]
    
    response = make_openrouter_request(messages)
    
    # Extract JSON from markdown code block if present
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
    if json_match:
        response = json_match.group(1)
    else:
        # If no markdown block, try to find JSON in the response
        json_match = re.search(r'(\{.*\})', response, re.DOTALL)
        if json_match:
            response = json_match.group(1)
    
    try:
        dataset = json.loads(response)["dataset"]
        return dataset
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error determining dataset: {e}")
        print(f"Raw response: {response}")
        return None

def get_pandas_expression(query, dataset_name, retry_count=0, max_retries=3, previous_error=None):
    # Select the appropriate dataframe
    df = disasters_df if dataset_name == "disasters" else tweets_df
    
    # Add error context to the system prompt if this is a retry
    system_content = (
        'You are an intelligent AI assistant that is tasked with returning JSON objects, where the key '
        'is "pandas_expression" and the value is the user query converted into a pandas expression. '
        'Ensure the value in the JSON object is of raw string type. Do not include anything else in your response. '
        'The pandas expression should be a valid Python string that can be evaluated with eval(). '
        'DO NOT include any string prefixes like r" or f". '
        'Here are examples of valid responses:\n'
        '{"pandas_expression": "df[df[\'Year\'] == 2020]"}\n'
        '{"pandas_expression": "df[df[\'Total Deaths\'] == df[\'Total Deaths\'].max()]"}\n'
        'Here are examples of INVALID responses:\n'
        '{"pandas_expression": r"df[df[\'Year\'] == 2020]"}\n'
        '{"pandas_expression": f"df[df[\'Year\'] == 2020]"}\n'
        'Never assume that the data is of a certain type. If the user asks for the date, ensure that its of type datetime.'
        'If the user asks for a number, ensure that its of type int or float.'
    )
    
    if previous_error:
        system_content += f'\n\nPrevious attempt failed with error: {previous_error}\n'
        system_content += 'Please fix the expression to address this error. For datetime operations, first convert the column to datetime using pd.to_datetime().'
    
    messages = [
        {
            'role': 'system',
            'content': system_content
        },
        {
            'role': 'user',
            'content': (
                f'Here is a dataset: {df.head().to_string()}. '
                f'Here is the user query: {query}. '
                'Write a pandas expression that properly evaluates the user query.'
            )
        }
    ]
    
    response = make_openrouter_request(messages)
    print(f'''\n\n Response for get_pandas_expression: \n\n\n{response}''')
    return response

def validate_pandas_expression(expr, dataset_name):
    """Test if a pandas expression is valid by trying to evaluate it."""
    try:
        # Create a safe environment for eval with the appropriate dataframe
        df = disasters_df if dataset_name == "disasters" else tweets_df
        safe_dict = {'df': df, 'pd': pd}
        eval(expr, safe_dict)
        return True, None
    except Exception as e:
        error_msg = str(e)
        print(f"Expression validation failed: {error_msg}")
        return False, error_msg

def answer_with_table(user_query, pandas_expression, dataset_name):
    # Select the appropriate dataframe
    df = disasters_df if dataset_name == "disasters" else tweets_df
    
    # Evaluate the pandas expression safely
    print(f'Calling eval with pandas expression: {pandas_expression}')
    try:
        # The expression should be something like: df[df['Flavor'] == 'Vanilla']
        result_table = eval(pandas_expression, {'df': df, 'pd': pd})
    except Exception as e:
        return f"Error evaluating pandas expression: {e}"

    # Convert the result to a string (limit rows for brevity)
    # table_str = result_table.head(10).to_string()
    # print(f'Table: {table_str}')

    # Now ask the LLM to answer the user's question using the table
    messages = [
        {
            'role': 'system',
            'content': (
                'You are a data analyst. The table provided to you is the direct result of a pandas query that '
                'answers the user\'s question. Your task is to interpret this filtered data and explain briefly what it '
                'tells us about the user\'s question. If the table is empty, explain what that means in the context '
                'of the question. Provide only the concise answer to the question, no other text.'
            )
        },
        {
            'role': 'user',
            'content': (
                f"User's question: {user_query}\n"
                f"Here is the filtered data that answers this question:\n{result_table}"
            )
        }
    ]
    
    return make_openrouter_request(messages)

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
        pandas_expr_json = get_pandas_expression(user_input, dataset_name, retry_count, max_retries, previous_error)
        
        # Strip markdown code block syntax using regex
        pandas_expr_json = re.sub(r'```json\n|\n```', '', pandas_expr_json)
        
        try:
            pandas_expr = json.loads(pandas_expr_json)["pandas_expression"]
            # Remove any string prefixes if they exist
            pandas_expr = re.sub(r'^[rf]?"|"$', '', pandas_expr)
            
            # Validate the expression
            is_valid, error = validate_pandas_expression(pandas_expr, dataset_name)
            if is_valid:
                print(f"Generated pandas expression: {pandas_expr}")
                answer = answer_with_table(user_input, pandas_expr, dataset_name)
                print(f"""--------------------\n\nLLM's answer: {answer}\n\n --------------------""")
                break
            else:
                print(f"Invalid pandas expression, retrying... (attempt {retry_count + 1}/{max_retries})")
                previous_error = error
                retry_count += 1
                
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing pandas expression: {e}")
            print(f"Raw expression: {pandas_expr_json}")
            previous_error = str(e)
            retry_count += 1
            
    if retry_count >= max_retries:
        print("Failed to generate a valid pandas expression after maximum retries.")
