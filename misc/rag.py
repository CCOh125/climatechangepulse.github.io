import os
import pandas as pd
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

# Load environment variables for API keys
load_dotenv()

# Check if API key exists
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in your environment")

# Load datasets
def load_data():
    disasters_df = pd.read_csv('data/disasters.csv')
    twitter_df = pd.read_csv('data/twitterSection.csv')
    return disasters_df, twitter_df

# Convert dataframes to documents for processing
def prepare_documents(disasters_df, twitter_df):
    disaster_docs = []
    for _, row in disasters_df.iterrows():
        # Create a string representation of each disaster
        content = f"Disaster Type: {row['Disaster Type']}\n" \
                  f"Subtype: {row.get('Disaster Subtype', 'Unknown')}\n" \
                  f"Country: {row['Country']}\n" \
                  f"Location: {row['Location']}\n" \
                  f"Date: {row['start_date']} to {row['end_date']}\n" \
                  f"Deaths: {row.get('Total Deaths', 'Unknown')}\n" \
                  f"Affected: {row.get('No Affected', 'Unknown')}\n" \
                  f"Coordinates: {row.get('Latitude', 'Unknown')}, {row.get('Longitude', 'Unknown')}"
        
        # Create a document with metadata
        doc = Document(
            page_content=content,
            metadata={
                "source": "disasters",
                "disaster_type": row['Disaster Type'],
                "country": row['Country'],
                "start_date": row['start_date'],
                "end_date": row['end_date']
            }
        )
        disaster_docs.append(doc)
    
    twitter_docs = []
    for _, row in twitter_df.iterrows():
        # Create a string representation of each tweet
        content = f"Tweet from {row.get('created_at', 'Unknown date')}\n" \
                  f"Topic: {row.get('topic', 'Unknown')}\n" \
                  f"Sentiment: {row.get('sentiment', 'Unknown')}\n" \
                  f"Location: {row.get('lat', 'Unknown')}, {row.get('lng', 'Unknown')}"
        
        # Create a document with metadata
        doc = Document(
            page_content=content,
            metadata={
                "source": "twitter",
                "created_at": row.get('created_at', ''),
                "topic": row.get('topic', ''),
                "sentiment": row.get('sentiment', '')
            }
        )
        twitter_docs.append(doc)
    
    return disaster_docs + twitter_docs

# Create a knowledge base
def create_knowledge_base(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # Split documents into chunks
    chunked_documents = text_splitter.split_documents(documents)
    
    # Create vector store using FAISS instead of Chroma
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(
        documents=chunked_documents,
        embedding=embeddings
    )
    return vectorstore

# Set up RAG for querying
def setup_rag(vectorstore):
    # Define a custom prompt template
    template = """You are an assistant that helps analyze disaster and climate-related social media data.
    Use only the providedcontext to answer the question.
    Do not provide an answer if no relevant information is found.

    Context:
    {context}

    Question: {question}
    
    Answer:"""
    
    QA_PROMPT = PromptTemplate(
        template=template,
        input_variables=["context", "question"]
    )
    
    # Set up the retrieval chain
    llm = ChatOpenAI(temperature=0)
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": QA_PROMPT}
    )
    
    return qa_chain

def main():
    disasters_df, twitter_df = load_data()
    #print(f"Loaded {len(disasters_df)} disaster records and {len(twitter_df)} tweets")
    
    documents = prepare_documents(disasters_df, twitter_df)
    #print(f"Prepared {len(documents)} documents for processing")
    
    vectorstore = create_knowledge_base(documents)
    qa_chain = setup_rag(vectorstore)
    
    print("You can now query disaster and Twitter data.")
    print("Example queries:")
    print("- What were the most common disasters in 2015?")
    print("- How did people on Twitter respond to floods?")
    print("- Compare hurricane damage between 2010 and 2020")
    
    while True:
        query = input("\nEnter your question (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
            
        print("\nProcessing your question...")
        result = qa_chain({"query": query})
        
        print("\nAnswer:")
        print(result["result"])
        
        print("\nSources:")
        for i, doc in enumerate(result["source_documents"][:3]):
            print(f"Source {i+1}: {doc.metadata.get('source', 'Unknown')} - {doc.metadata}")

if __name__ == "__main__":
    main()