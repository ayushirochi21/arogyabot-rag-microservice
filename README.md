# Public Health RAG Chatbot

A source-grounded Retrieval-Augmented Generation (RAG) framework using a Python (Flask) microservice, MongoDB Atlas Vector Search, and Google Gemini API to deliver reliable, verifiable public health guidance.

---

## Prerequisites

- **Python**: Version 3.10+ installed
- **Node.js**: Version 18+ (if running the MERN application layer)
- **MongoDB Atlas**: An active MongoDB Atlas account
- **Google AI Studio**: An active Google account to generate a Gemini API Key

---

## 1. Setting Up MongoDB Atlas Cluster & Vector Search Index

1. **Create a Cluster:**
   - Sign in to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas).
   - Click **Create** to deploy a new cluster (a free `M0` cluster works for testing).

2. **Obtain Connection String:**
   - In your cluster dashboard, click **Connect**.
   - Choose **Drivers** (Node.js or Python).
   - Copy the provided connection string. Replace `<password>` with your database user password.

3. **Create the Vector Search Index:**
   - In Atlas, navigate to **Atlas Search / Vector Search** in the sidebar.
   - Click **Create Search Index**.
   - Select **JSON Editor** under **Atlas Vector Search** and click **Next**.
   - Select your target database and collection (e.g., `health_db.vector_store`).
   - Use the following index definition:

```json
{
  "fields": [
    {
      "numDimensions": 384,
      "path": "embedding",
      "similarity": "cosine",
      "type": "vector"
    }
  ]
}

```

* Name the index **`medical_vector_index`** and click **Create Vector Index**.

---

## 2. Obtaining a Google Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/?utm_source=gemini).
2. Sign in with your Google account.
3. Click **Get API key** and then **Create API key**.
4. Copy the generated API key string for your environment configuration.

---

## 3. Environment Configuration

Create a `.env` file in the root directory of the project (or inside your Python microservice folder) with the following environment variables:

```env
MONGO_URI="your_mongodb_atlas_connection_string"
GEMINI_API_KEY="your_gemini_api_key"
DB_NAME="health_db"
COLLECTION_NAME="vector_store"
VECTOR_INDEX_NAME="medical_vector_index"

```

---

## 4. Setup & Running in Terminal

### Step 1: Clone the Repository

```bash
git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
cd your-repo-name

```

### Step 2: Set Up Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows (Command Prompt):
venv\Scripts\activate.bat
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

```

### Step 3: Install Required Python Dependencies

```bash
pip install --upgrade pip
pip install flask flask-cors pymongo google-generativeai sentence-transformers pdfplumber

```

### Step 4: Run the Ingestion Pipeline (Offline Data Processing)

Run the ingestion script to process source PDFs, generate section-aware embeddings, and store them in MongoDB Atlas:

```bash
python ingest.py

```

### Step 5: Start the Flask Microservice

Launch the API microservice to serve the RAG pipeline endpoints:

```bash
python app.py

```

The service will typically start at `http://127.0.0.1:5000`.

---

## Verification & API Testing

To verify the setup, send a test POST request to the `/chat` endpoint using `curl`:

```bash
curl -X POST [http://127.0.0.1:5000/chat](http://127.0.0.1:5000/chat) \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the key symptoms of dengue?"}'

```

```

```
