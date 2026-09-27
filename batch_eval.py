import csv
import time
import datetime
import requests

# -----------------------------------------
# CONFIG
# -----------------------------------------

API_URL = "http://127.0.0.1:5000/chat"
OUTPUT_FILE = f"evaluation_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# -----------------------------------------
# TEST QUESTION SET (15 questions total)
# 12 on-topic covering all disease topics + 3 off-topic
# -----------------------------------------

TEST_QUESTIONS = [
    ("diabetes", "What are the symptoms of diabetes?"),
    ("diabetes", "How can diabetes be prevented?"),
    ("stroke", "What are the warning signs of a stroke?"),
    ("asthma", "What triggers asthma attacks?"),
    ("chikungunya", "What are the symptoms of chikungunya?"),
    ("dengue", "What are the symptoms of dengue fever?"),
    ("dengue", "How can dengue be prevented?"),
    ("hypertension", "What causes high blood pressure?"),
    ("malaria", "How is malaria transmitted?"),
    ("seasonal influenza", "What are the symptoms of seasonal flu?"),
    ("tuberculosis", "How is TB treated?"),
    ("typhoid", "How can typhoid be prevented?"),
    ("off-topic", "What is your favorite color?"),
    ("off-topic", "Who created you?"),
    ("off-topic", "Tell me a joke."),
]


# -----------------------------------------
# RUN THE EVALUATION
# -----------------------------------------

def run_evaluation():

    results = []

    print(f"Running {len(TEST_QUESTIONS)} test questions against {API_URL}...\n")

    for i, (category, question) in enumerate(TEST_QUESTIONS, 1):

        print(f"[{i}/{len(TEST_QUESTIONS)}] ({category}) {question}")

        start_time = time.time()

        try:
            response = requests.post(
                API_URL,
                json={"question": question},
                timeout=60
            )
            elapsed = round(time.time() - start_time, 2)

            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                sources = data.get("sources", [])

                top_score = sources[0]["score"] if sources else ""
                num_sources = len(sources)
                sources_summary = "; ".join(
                    f"{s['topic']} ({s['section']}) [{s['score']}]" for s in sources
                )

            else:
                answer = f"ERROR: HTTP {response.status_code} - {response.text[:200]}"
                top_score = ""
                num_sources = 0
                sources_summary = ""

        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            answer = f"ERROR: {e}"
            top_score = ""
            num_sources = 0
            sources_summary = ""

        results.append({
            "id": i,
            "category": category,
            "question": question,
            "answer": answer,
            "top_relevance_score": top_score,
            "num_sources_used": num_sources,
            "sources_summary": sources_summary,
            "response_time_sec": elapsed,
            "manually_correct (fill in Y/N)": "",
            "manually_grounded (fill in Y/N)": "",
            "hallucination_observed (fill in Y/N)": "",
            "notes": "",
        })

        print(f"    -> {elapsed}s | top score: {top_score}\n")
        time.sleep(5)  # stay under the per-minute rate limit

    # -----------------------------------------
    # WRITE TO CSV (timestamped, never overwrites)
    # -----------------------------------------

    fieldnames = list(results[0].keys())

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("--------------------------------")
    print("EVALUATION COMPLETE")
    print("--------------------------------")
    print(f"Results saved to: {OUTPUT_FILE}")
    print(f"Total questions: {len(results)}")

    times = [r["response_time_sec"] for r in results if isinstance(r["response_time_sec"], (int, float))]
    if times:
        print(f"Average response time: {round(sum(times) / len(times), 2)}s")


if __name__ == "__main__":
    run_evaluation()