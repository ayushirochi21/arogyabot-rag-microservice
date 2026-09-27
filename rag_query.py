import os
from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import google.generativeai as genai


# -----------------------------------------
# CONFIG
# -----------------------------------------
import os
from dotenv import load_dotenv

load_dotenv()  # reads the .env file and loads it into the environment

MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

DB_NAME = "medical_chatbot"
COLLECTION_NAME = "medical_chunks"
INDEX_NAME = "medical_vector_index"

GEMINI_MODEL = "gemini-3.1-flash-lite"


# -----------------------------------------
# CONNECT TO MONGODB
# -----------------------------------------

print("Connecting to MongoDB...")

client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

print("Connected successfully!")


# -----------------------------------------
# LOAD EMBEDDING MODEL
# -----------------------------------------

print("\nLoading embedding model...")

embedder = SentenceTransformer("all-MiniLM-L6-v2")

print("Embedding model loaded!")


# -----------------------------------------
# CONFIGURE GEMINI
# -----------------------------------------

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(GEMINI_MODEL)

print(f"Gemini model ready: {GEMINI_MODEL}")


# -----------------------------------------
# RETRIEVE RELEVANT CHUNKS
# -----------------------------------------

def retrieve_chunks(query, top_k=5):

    query_embedding = embedder.encode(query).tolist()

    results = collection.aggregate([
        {
            "$vectorSearch": {
                "index": INDEX_NAME,
                "path": "embedding",
                "queryVector": query_embedding,
                "numCandidates": 100,
                "limit": top_k
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "document": 1,
                "topic": 1,
                "section": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ])

    return list(results)


# -----------------------------------------
# BUILD THE GROUNDED PROMPT
# -----------------------------------------

def build_prompt(question, chunks):

    context_blocks = []

    for i, chunk in enumerate(chunks, 1):
        context_blocks.append(
            f"[Source {i}: {chunk.get('topic', 'N/A').title()} — "
            f"{chunk.get('section', 'N/A')}]\n{chunk['text']}"
        )

    context_text = "\n\n".join(context_blocks)

    prompt = f"""You are a public health information assistant. Answer the
user's question using ONLY the verified information provided below.
Do not use any outside knowledge. If the provided information does not
fully answer the question, say so honestly instead of guessing.

Always end your answer with a reminder to consult a qualified healthcare
professional for personal medical advice — you are an information tool,
not a diagnostic tool.

VERIFIED INFORMATION:
{context_text}

USER QUESTION:
{question}

Answer clearly and concisely, in plain language a non-expert can understand."""

    return prompt


# -----------------------------------------
# MAIN LOOP
# -----------------------------------------

def main():

    question = input("\nAsk a health question: ")

    print("\nRetrieving relevant information...")
    chunks = retrieve_chunks(question, top_k=5)

    if not chunks:
        print("No relevant information found in the knowledge base.")
        return

    print(f"Found {len(chunks)} relevant chunks.")

    prompt = build_prompt(question, chunks)

    print("\nAsking Gemini...")
    response = gemini_model.generate_content(prompt)

    print("\n" + "=" * 60)
    print("ANSWER")
    print("=" * 60)
    print(response.text)

    print("\n" + "-" * 60)
    print("SOURCES USED")
    print("-" * 60)
    for chunk in chunks:
        print(f"- {chunk.get('topic', 'N/A').title()} ({chunk.get('section', 'N/A')}) "
              f"[{chunk.get('document', 'N/A')}] — score {chunk['score']:.3f}")

    client.close()


if __name__ == "__main__":
    main()