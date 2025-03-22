import os
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load environment variables
load_dotenv()

# Initialize Flask
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:8000"}})

# Global variables for RAG components
vectorstore = None
qa_chain = None

def setup_rag(vectorstore):
    template = """You are an assistant that helps analyze disaster and climate-related social media data.
    Use only the provided context to answer the question.
    Do not provide an answer if no relevant information is found.

    Context:
    {context}

    Question: {question}
    
    Answer:"""
    
    QA_PROMPT = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    llm = ChatOpenAI(temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": QA_PROMPT}
    )
    
    return qa_chain

def initialize_rag():
    global vectorstore, qa_chain
    
    # Check if vectorstore directory exists
    if not os.path.exists('vectorstore'):
        raise ValueError("Vectorstore not found. Please run create_vectorstore.py first.")
    
    print("Loading vectorstore from disk...")
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.load_local('vectorstore', embeddings)
    
    print("Setting up RAG chain...")
    qa_chain = setup_rag(vectorstore)

@app.route('/')
def home():
    return jsonify({'Response': 200, 'Message': 'Welcome to the Climate Change Pulse RAG API!'})

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message')
        
        if not user_message:
            return jsonify({'error': 'No message provided'}), 400
        
        if not qa_chain:
            return jsonify({'error': 'RAG system not initialized'}), 500
        
        # Process the query using RAG
        result = qa_chain({"query": user_message})
        
        # Prepare sources for response
        sources = []
        for doc in result["source_documents"][:3]:
            sources.append({
                "source": doc.metadata.get('source', 'Unknown'),
                "metadata": doc.metadata
            })
        
        return jsonify({
            'response': result["result"],
            'sources': sources
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    # Initialize RAG system
    print("Initializing RAG system...")
    initialize_rag()
    print("RAG system initialized successfully!")
    
    # Run the Flask app
    app.run(debug=True) 