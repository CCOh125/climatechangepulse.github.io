"""
create_vectorstore.py

This script creates a vector store from the disaster and twitter data and saves it to disk.
"""

import os
from dotenv import load_dotenv
import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings
from langchain.schema import Document

# Load environment variables
load_dotenv()

def load_data():
    disasters_df = pd.read_csv('data/disasters.csv')
    twitter_df = pd.read_csv('data/twitterSection.csv')
    return disasters_df, twitter_df

def prepare_documents(disasters_df, twitter_df):
    disaster_docs = []
    for _, row in disasters_df.iterrows():
        content = f"Disaster Type: {row['Disaster Type']}\n" \
                  f"Subtype: {row.get('Disaster Subtype', 'Unknown')}\n" \
                  f"Country: {row['Country']}\n" \
                  f"Location: {row['Location']}\n" \
                  f"Date: {row['start_date']} to {row['end_date']}\n" \
                  f"Deaths: {row.get('Total Deaths', 'Unknown')}\n" \
                  f"Affected: {row.get('No Affected', 'Unknown')}\n" \
                  f"Coordinates: {row.get('Latitude', 'Unknown')}, {row.get('Longitude', 'Unknown')}"
        
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
        content = f"Tweet from {row.get('created_at', 'Unknown date')}\n" \
                  f"Topic: {row.get('topic', 'Unknown')}\n" \
                  f"Sentiment: {row.get('sentiment', 'Unknown')}\n" \
                  f"Location: {row.get('lat', 'Unknown')}, {row.get('lng', 'Unknown')}"
        
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

def create_knowledge_base(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    chunked_documents = text_splitter.split_documents(documents)
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(
        documents=chunked_documents,
        embedding=embeddings
    )
    return vectorstore

def main():
    print("Loading data...")
    disasters_df, twitter_df = load_data()
    
    print("Preparing documents...")
    documents = prepare_documents(disasters_df, twitter_df)
    
    print("Creating knowledge base...")
    vectorstore = create_knowledge_base(documents)
    
    print("Saving vectorstore to disk...")
    # Create vectorstore directory if it doesn't exist
    os.makedirs('vectorstore', exist_ok=True)
    
    # Save the vectorstore
    vectorstore.save_local('vectorstore')
    print("Vectorstore saved successfully to 'vectorstore' directory!")

if __name__ == "__main__":
    main()


