import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
df = pd.read_csv('/misc/data/icecream.csv')

def get_pandas_expression(query):
    client = OpenAI(api_key=API_KEY)
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are an intelligent AI assistant that is tasked with returning JSON objects, where the key '
                    'is "pandas_expression" and the value is the user query converted into a pandas expression. '
                    'Ensure the value in the JSON object is of raw string type. Do not include anything else in your response.'
                )
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
    )
    return chat_completion.choices[0].message.content

def answer_with_table(user_query, pandas_expression):
    # Evaluate the pandas expression safely
    try:
        # The expression should be something like: df[df['Flavor'] == 'Vanilla']
        result_table = eval(pandas_expression, {'df': df, 'pd': pd})
    except Exception as e:
        return f"Error evaluating pandas expression: {e}"

    # Convert the result to a string (limit rows for brevity)
    table_str = result_table.head(10).to_string()

    # Now ask the LLM to answer the user's question using the table
    client = OpenAI(api_key=API_KEY)
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                'role': 'system',
                'content': (
                    'You are a data analyst. Use the provided table to answer the user\'s question. '
                    'If the table is empty or does not answer the question, say so.'
                )
            },
            {
                'role': 'user',
                'content': (
                    f"User's question: {user_query}\n"
                    f"Relevant table:\n{table_str}"
                )
            }
        ]
    )
    return chat_completion.choices[0].message.content

if __name__ == '__main__':
    user_input = input('What is your question? ')
    pandas_expr_json = get_pandas_expression(user_input)
    # Extract the pandas expression from the JSON string
    import json
    pandas_expr = json.loads(pandas_expr_json)["pandas_expression"]
    print(f"Generated pandas expression: {pandas_expr}")
    answer = answer_with_table(user_input, pandas_expr)
    print("LLM's answer:", answer)
