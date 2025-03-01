import os
import google.generativeai as genai
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY is not set")

# Read the CSV file
df = pd.read_csv('data/disasters.csv')

# Count disasters by type
disaster_counts = df['Disaster Type'].value_counts()

# Configure Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-pro')

prompt = f"""Based on the following disaster data from 2007-2009:

{disaster_counts.to_string()}

Count the number of disaster for each type """

response = model.generate_content(prompt)
print(response.text)

# Ask teacher how to commit changes to the repository