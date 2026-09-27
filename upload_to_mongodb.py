import json
from pymongo import MongoClient


# ----------------------------------------
# MONGODB CONNECTION
# ----------------------------------------

import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file and loads it into the environment

MONGODB_URI = os.getenv("MONGODB_URI")



# ----------------------------------------
# CONNECT TO MONGODB
# ----------------------------------------

print("Connecting to MongoDB...")

client = MongoClient(MONGODB_URI)

print("Connected successfully!")


# ----------------------------------------
# DATABASE AND COLLECTION
# ----------------------------------------

db = client["medical_chatbot"]

collection = db["medical_chunks"]


# ----------------------------------------
# LOAD JSON DATA
# ----------------------------------------

INPUT_FILE = "data/processed/who_chunks_with_embeddings.json"

print("\nLoading WHO chunks...")

with open(INPUT_FILE, "r", encoding="utf-8") as file:

    chunks = json.load(file)


print(f"Total chunks found: {len(chunks)}")


# ----------------------------------------
# UPLOAD DATA
# ----------------------------------------

print("\nUploading chunks to MongoDB...")

# Remove old data to avoid duplicates
collection.delete_many({})

# Insert all chunks
collection.insert_many(chunks)


print("\n--------------------------------")
print("UPLOAD SUCCESSFUL!")
print("--------------------------------")

print(f"Uploaded {len(chunks)} chunks")


# ----------------------------------------
# CLOSE CONNECTION
# ----------------------------------------

client.close()