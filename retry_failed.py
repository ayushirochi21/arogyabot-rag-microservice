import csv
import time
import requests

# -----------------------------------------
# CONFIG
# -----------------------------------------

API_URL = "http://127.0.0.1:5000/chat"
ORIGINAL_CSV = "evaluation_results_20260911_123230.csv"  
OUTPUT_FILE = "evaluation_results_FINAL.csv"

DELAY_BETWEEN_QUESTIONS = 15  
MAX_RETRIES_PER_QUESTION = 3
RETRY_WAIT = 25                

FAILED_QUESTIONS = [
    ("diabetes", "How can diabetes be prevented?"),
    ("stroke", "What are the warning signs of a stroke?"),
    ("asthma", "What triggers asthma attacks?"),
    ("chikungunya", "What are the symptoms of chikungunya?"),
    ("dengue", "What are the symptoms of dengue fever?"),
    ("dengue", "How can dengue be prevented?"),
    ("hypertension", "What causes high blood pressure?"),
    ("tuberculosis", "How is TB treated?"),
    ("typhoid", "How can typhoid be prevented?"),
    ("off-topic", "Who created you?"),
    ("off-topic", "Tell me a joke."),
]


def ask_question(question):
    """Sends one question, retrying on 429 errors."""

    for attempt in range(1, MAX_RETRIES_PER_QUESTION + 1):

        start_time = time.time()

        try:
            response = requests.post(API_URL, json={"question": question}, timeout=60)
            elapsed = round(time.time() - start_time, 2)

            if response.status_code == 200:
                data = response.json()
                return {
                    "answer": data.get("answer", ""),
                    "sources": data.get("sources", []),
                    "elapsed": elapsed,
                }

            body = response.text
            if "429" in body or "quota" in body.lower():
                print(f"    Attempt {attempt}: quota error, waiting {RETRY_WAIT}s before retry...")
                time.sleep(RETRY_WAIT)
                continue
            else:
                return {"answer": f"ERROR: HTTP {response.status_code} - {body[:200]}", "sources": [], "elapsed": elapsed}

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            return {"answer": f"ERROR: {e}", "sources": [], "elapsed": elapsed}

    return {"answer": "ERROR: still quota-limited after retries", "sources": [], "elapsed": 0}


def main():

    # Load original results
    with open(ORIGINAL_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # Retry each failed question
    for category, question in FAILED_QUESTIONS:
        print(f"Retrying: ({category}) {question}")

        result = ask_question(question)

        for row in rows:
            if row["question"] == question:
                row["answer"] = result["answer"]
                sources = result["sources"]
                row["top_relevance_score"] = sources[0]["score"] if sources else ""
                row["num_sources_used"] = len(sources)
                row["sources_summary"] = "; ".join(
                    f"{s['topic']} ({s['section']}) [{s['score']}]" for s in sources
                )
                row["response_time_sec"] = result["elapsed"]
                break

        print(f"    -> {result['elapsed']}s\n")
        time.sleep(DELAY_BETWEEN_QUESTIONS)

    # Save merged final CSV
    fieldnames = list(rows[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Merged results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()