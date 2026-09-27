import csv
import time
import datetime
import requests

API_URL = "http://127.0.0.1:5000/chat"
OUTPUT_FILE = f"evaluation_results_round2_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

DELAY_BETWEEN_QUESTIONS = 5  # seconds — safe under 15 RPM limit

TEST_QUESTIONS = [
    ("cardiovascular disease", "What are the symptoms of a heart attack?"),
    ("cardiovascular disease", "How can cardiovascular disease be prevented?"),
    ("COPD", "What are the symptoms of COPD?"),
    ("COPD", "What causes chronic obstructive pulmonary disease?"),
    ("leprosy", "What are the early signs of leprosy?"),
    ("leprosy", "Is leprosy curable?"),
    ("cholera", "What causes cholera?"),
    ("cholera", "How is cholera treated?"),
    ("Japanese encephalitis", "What are the symptoms of Japanese encephalitis?"),
    ("Japanese encephalitis", "How is Japanese encephalitis prevented?"),
    ("Kala-azar", "What are the symptoms of Kala-azar?"),
    ("Kala-azar", "How is visceral leishmaniasis transmitted?"),
    ("lymphatic filariasis", "What causes lymphatic filariasis?"),
    ("lymphatic filariasis", "How can lymphatic filariasis be prevented?"),
    ("HIV/AIDS", "How is HIV transmitted?"),
    ("HIV/AIDS", "What are the early symptoms of HIV infection?"),
    ("hepatitis", "What are the symptoms of viral hepatitis?"),
    ("hepatitis", "How can hepatitis B be prevented?"),
    ("mental health", "What are common signs of depression?"),
    ("mental health", "When should someone seek help for depression?"),
    ("personal-symptom", "I have had a fever and joint pain for 3 days, what could this be?"),
    ("personal-symptom", "I am feeling very thirsty and tired lately, should I be worried?"),
]


def run_evaluation():
    results = []
    print(f"Running {len(TEST_QUESTIONS)} test questions against {API_URL}...\n")

    for i, (category, question) in enumerate(TEST_QUESTIONS, 1):
        print(f"[{i}/{len(TEST_QUESTIONS)}] ({category}) {question}")
        start_time = time.time()

        try:
            response = requests.post(API_URL, json={"question": question}, timeout=60)
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
        time.sleep(DELAY_BETWEEN_QUESTIONS)

    fieldnames = list(results[0].keys())
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print("--------------------------------")
    print("EVALUATION COMPLETE")
    print("--------------------------------")
    print(f"Results saved to: {OUTPUT_FILE}")

    times = [r["response_time_sec"] for r in results if isinstance(r["response_time_sec"], (int, float))]
    if times:
        print(f"Average response time: {round(sum(times) / len(times), 2)}s")


if __name__ == "__main__":
    run_evaluation()