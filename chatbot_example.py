import os
from openai import OpenAI
from dotenv import load_dotenv

# Load the environment variables from .env
load_dotenv()

# Initialize OpenAI
client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Create a chatcompletion response
chat_completion = client.chat.completions.create(
    model="gpt-4o",
    messages = [
        {'role': 'user', 'content': 'Who won the United States 2024 presidential election?'}
    ]
)

print(chat_completion.choices[0].message.content)

# import os
# import google.generativeai as genai
# from dotenv import load_dotenv

# # Load API key from .env file
# load_dotenv()
# API_KEY = os.getenv("GEMINI_API_KEY")

# if not API_KEY:
#     raise ValueError("GEMINI_API_KEY not found in .env file")

# # Configure the API
# genai.configure(api_key=API_KEY)

# # Initialize the Gemini model
# model = genai.GenerativeModel("gemini-pro")

# def chat_with_gemini():
#     """A simple chatbot function that interacts with the Gemini model."""
#     print("Chatbot initialized! Type 'exit' to quit.")

#     while True:
#         user_input = input("You: ")
#         if user_input.lower() == "exit":
#             print("Goodbye!")
#             break
        
#         try:
#             response = model.generate_content(user_input)
#             print("Gemini:", response.text)
#         except Exception as e:
#             print("Error:", e)

# def main():
#     """Main function to start the chatbot."""
#     chat_with_gemini()

# if __name__ == "__main__":
#     main()
