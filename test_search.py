import json
import textwrap
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer


import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file and loads it into the environment

MONGODB_URI = os.getenv("MONGODB_URI")


DB_NAME = "medical_chatbot"
COLLECTION_NAME = "medical_chunks"
INDEX_NAME = "medical_vector_index"


print("Connecting to MongoDB...")
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
print("Connected successfully!")

print("\nLoading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("Model loaded successfully!")

query = input("\nAsk a health question: ")

print("\nEmbedding your query...")
query_embedding = model.encode(query).tolist()

print("Searching MongoDB Atlas Vector Search...")

results = collection.aggregate([
    {
        "$vectorSearch": {
            "index": INDEX_NAME,
            "path": "embedding",
            "queryVector": query_embedding,
            "numCandidates": 100,
            "limit": 5
        }
    },
    {
        "$project": {
            "_id": 0,
            "text": 1,
            "document": 1,
            "source": 1,
            "topic": 1,
            "section": 1,
            "chunk_number": 1,
            "score": {"$meta": "vectorSearchScore"}
        }
    }
])

print("\n" + "=" * 60)
print("TOP MATCHES")
print("=" * 60)

for i, doc in enumerate(results, 1):
    print(f"\n[{i}] {doc.get('topic', 'N/A').title()} — {doc.get('section', 'N/A')}")
    print(f"    Document: {doc.get('document', 'N/A')}  |  Score: {doc['score']:.4f}")
    print("-" * 60)

    wrapped = textwrap.fill(
        doc["text"],
        width=70,
        initial_indent="    ",
        subsequent_indent="    "
    )
    print(wrapped)
    print()

client.close()
print("Done!")