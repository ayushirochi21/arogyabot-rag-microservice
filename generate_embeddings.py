import json
import os
from sentence_transformers import SentenceTransformer


# -----------------------------------------
# FILE PATHS
# -----------------------------------------

INPUT_FILE = "data/processed/who_chunks.json"

OUTPUT_FILE = "data/processed/who_chunks_with_embeddings.json"


# -----------------------------------------
# LOAD EMBEDDING MODEL
# -----------------------------------------

print("Loading embedding model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("Model loaded successfully!")


# -----------------------------------------
# LOAD CHUNKS
# -----------------------------------------

print("\nLoading WHO chunks...")

with open(INPUT_FILE, "r", encoding="utf-8") as file:
    chunks = json.load(file)

print(f"Total chunks found: {len(chunks)}")


# -----------------------------------------
# GENERATE EMBEDDINGS
# -----------------------------------------

print("\nGenerating embeddings...")

BATCH_SIZE = 32

all_chunks = []

for start in range(0, len(chunks), BATCH_SIZE):

    batch = chunks[start:start + BATCH_SIZE]

    texts = [chunk["text"] for chunk in batch]

    embeddings = model.encode(
        texts,
        show_progress_bar=False
    )

    # Add embedding to each chunk
    for chunk, embedding in zip(batch, embeddings):

        chunk["embedding"] = embedding.tolist()

        all_chunks.append(chunk)

    print(
        f"Processed {min(start + BATCH_SIZE, len(chunks))}"
        f" / {len(chunks)} chunks"
    )


# -----------------------------------------
# SAVE RESULTS
# -----------------------------------------

print("\nSaving embeddings...")

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        all_chunks,
        file,
        ensure_ascii=False,
        indent=2
    )


print("\n--------------------------------")
print("EMBEDDINGS GENERATED SUCCESSFULLY!")
print("--------------------------------")

print(f"Total chunks: {len(all_chunks)}")
print(f"Saved to: {OUTPUT_FILE}")