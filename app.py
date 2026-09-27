import os
from flask import Flask, request, jsonify
from flask_cors import CORS
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

MIN_RELEVANCE_SCORE = 0.5  # tune based on testing


# -----------------------------------------
# INITIALIZE APP
# -----------------------------------------

app = Flask(__name__)
CORS(app)  # allows requests from your React frontend later


# -----------------------------------------
# LOAD EVERYTHING ONCE AT STARTUP
# -----------------------------------------

print("Connecting to MongoDB...")
client = MongoClient(MONGODB_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
print("Connected to MongoDB!")

print("Loading embedding model...")
embedder = SentenceTransformer("all-MiniLM-L6-v2")
print("Embedding model loaded!")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel(GEMINI_MODEL)
print(f"Gemini model ready: {GEMINI_MODEL}")


# -----------------------------------------
# RETRIEVAL
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
# PROMPT BUILDING
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

If the user's question is not related to public health, symptoms,
diseases, prevention, or medical information (for example: personal
questions, casual conversation, or unrelated topics), politely explain
that you can only help with public-health-related questions, and do not
attempt to force an answer using the unrelated information below.

Do not attempt to diagnose the user's specific condition. Only provide
general information about possible causes, prevention, and general
guidance to seek care.

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
# ROUTES
# -----------------------------------------
@app.route("/", methods=["GET"])
def home():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Medical Chatbot Demo</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; background: #f5f5f5; }
        h1 { color: #1F4E78; }
        textarea { width: 100%; height: 60px; font-size: 16px; padding: 10px; box-sizing: border-box; }
        button { margin-top: 10px; padding: 10px 24px; font-size: 16px; background: #1F4E78; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #163a56; }
        #answer { margin-top: 20px; padding: 15px; background: white; border-radius: 8px; white-space: pre-wrap; min-height: 40px; }
        #sources { margin-top: 15px; font-size: 13px; color: #555; }
        .loading { color: #888; font-style: italic; }
    </style>
</head>
<body>
    <h1>AI-Based Public Health Chatbot</h1>
    <p>Ask a health question (based on WHO / ICMR / NCDC verified sources):</p>
    <textarea id="question" placeholder="e.g. What are the symptoms of diabetes?"></textarea><br>
    <button onclick="askQuestion()">Ask</button>

    <div id="answer"></div>
    <div id="sources"></div>

    <script>
        async function askQuestion() {
            const question = document.getElementById('question').value;
            const answerDiv = document.getElementById('answer');
            const sourcesDiv = document.getElementById('sources');

            if (!question.trim()) return;

            answerDiv.innerHTML = '<span class="loading">Thinking...</span>';
            sourcesDiv.innerHTML = '';

            try {
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: question })
                });
                const data = await response.json();

                answerDiv.innerText = data.answer || data.error || 'No response';

                if (data.sources && data.sources.length > 0) {
                    let sourcesHtml = '<strong>Sources used:</strong><ul>';
                    data.sources.forEach(s => {
                        sourcesHtml += `<li>${s.topic} (${s.section}) — score ${s.score}</li>`;
                    });
                    sourcesHtml += '</ul>';
                    sourcesDiv.innerHTML = sourcesHtml;
                }
            } catch (err) {
                answerDiv.innerText = 'Error connecting to server: ' + err;
            }
        }
    </script>
</body>
</html>
"""

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "RAG microservice is running"})


@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field in request body"}), 400

    question = data["question"].strip()

    if not question:
        return jsonify({"error": "Question cannot be empty"}), 400

    try:
        chunks = retrieve_chunks(question, top_k=5)

        if not chunks or chunks[0]["score"] < MIN_RELEVANCE_SCORE:
            return jsonify({
                "answer": "I'm a public health information assistant, so I can only help with questions about diseases, symptoms, prevention, and treatment based on verified sources like WHO, ICMR, and NCDC. Could you rephrase your question as a health-related query? For personal medical concerns, please consult a qualified healthcare professional.",
                "sources": []
            })

        prompt = build_prompt(question, chunks)
        response = gemini_model.generate_content(prompt)

        sources = [
            {
                "topic": chunk.get("topic", "N/A"),
                "section": chunk.get("section", "N/A"),
                "document": chunk.get("document", "N/A"),
                "score": round(chunk["score"], 3)
            }
            for chunk in chunks
        ]

        return jsonify({
            "answer": response.text,
            "sources": sources
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------------------------
# RUN SERVER
# -----------------------------------------

if __name__ == "__main__":
    app.run(debug=True, port=5000)