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

def get_pandas_expression(query, dataset_name, retry_count=0, max_retries=3, previous_error=None):
    # Select the appropriate dataframe
    df = disasters_df if dataset_name == "disasters" else tweets_df
    
    # Get column info for better context
    column_info = []
    for col in df.columns:
        sample = df[col].iloc[0] if not df.empty else None
        dtype = str(df[col].dtype)
        column_info.append(f"{col} ({dtype}): {sample}")
    
    # Add error context to the system prompt if this is a retry
    system_content = (
        'You are an AI that generates pandas expressions. Follow these rules strictly:\n'
        '1. Return ONLY a complete pandas expression as a string\n'
        '2. Do not include any JSON formatting, markdown, or other text\n'
        '3. The expression must be a valid Python string that can be evaluated with eval()\n'
        '4. For datetime operations, use pd.to_datetime() first\n'
        '5. For numeric operations, ensure columns are converted to numeric using pd.to_numeric()\n'
        '6. Always use double quotes for column names\n'
        '7. Keep expressions simple and focused on one task\n\n'
        'Example valid responses:\n'
        'df[df["Year"] == 2020]\n'
        'df[df["Total Deaths"] == df["Total Deaths"].max()]\n'
        'df.assign(date=pd.to_datetime(df["date"]))[df["date"].dt.year == 2019]\n\n'
        'Example invalid responses:\n'
        '{"pandas_expression": "df[df[\'Year\'] == 2020]"}\n'
        'df[df[\'Year\'] == 2020]\n'
        'return df[df["Year"] == 2020]'
    )
    
    if previous_error:
        system_content += f'\n\nPrevious attempt failed with error: {previous_error}'
    
    messages = [
        {
            'role': 'system',
            'content': system_content
        },
        {
            'role': 'user',
            'content': (
                f'Dataset: {dataset_name}\n'
                f'Columns and sample values:\n' + '\n'.join(column_info) + '\n\n'
                f'Query: {query}\n'
                'Generate a pandas expression to answer this query.'
            )
        }
    ]
    
    response = make_openrouter_request(messages)
    
    # Clean up the response to get just the pandas expression
    response = response.strip()
    
    # Remove any markdown code blocks if present
    response = re.sub(r'```.*?\n|\n```', '', response)
    
    # Remove any JSON formatting if present
    response = re.sub(r'^{"pandas_expression":\s*"|"}$', '', response)
    
    # Remove any string prefixes
    response = re.sub(r'^[rf]?"|"$', '', response)
    
    # Remove any Python keywords that might have been included
    response = re.sub(r'^(return|def|print)\s+', '', response)
    
    # Basic validation of the expression
    if not response.startswith('df'):
        raise ValueError("Expression must start with 'df'")
    
    if ';' in response:
        raise ValueError("Expression contains multiple statements")
    
    return response

def validate_pandas_expression(expr, dataset_name):
    """Test if a pandas expression is valid by trying to evaluate it."""
    try:
        # Create a safe environment for eval with the appropriate dataframe
        df = disasters_df if dataset_name == "disasters" else tweets_df
        safe_dict = {'df': df, 'pd': pd}
        
        # First try to evaluate the expression
        result = eval(expr, safe_dict)
        
        # Additional validation
        if not isinstance(result, pd.DataFrame):
            return False, "Expression must return a DataFrame"
            
        if result.empty:
            return False, "Expression returned an empty DataFrame"
            
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
