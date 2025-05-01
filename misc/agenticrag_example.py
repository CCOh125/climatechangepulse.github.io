import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
import os
'''
Design an Agentic RAG system which acheives the following behavior:

User sends in query

Query is used to construct a pandas expression

pandas expression is used to query the pandas dataset

Return the table to the LLM

LLM spits out response.
'''
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
df = pd.read_csv('data/icecream.csv')

def get_pandas_expression(query):
    client = OpenAI(api_key=API_KEY)
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages = [
            {'role': 'system', 'content': 'You are an intelligent AI assistant that is tasked with returning JSON objects, where the key'
            'is the "pandas_expression" and the value is the user query converted into a pandas expression. Ensure the value in the JSON object is'
            'of raw string type. Do not include anything else in your response.',
                'role': 'user', 'content': f'Here is a dataset: {df}. Here is the user query: {query}. Write a pandas expression that properlys evaluates the user query.'}
        ]
    )
    return chat_completion.choices[0].message.content


if __name__ == '__main__':
    user_input = input('What is your question?')
    ans = get_pandas_expression(user_input)
    print(ans)