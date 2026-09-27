import os
import re
import json
import pdfplumber


# --------------------------------------------------
# 1. FOLDERS
# --------------------------------------------------

PDF_FOLDER = "data/who_pdfs"
OUTPUT_FOLDER = "data/processed"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


# --------------------------------------------------
# 2. CLEAN TEXT
# --------------------------------------------------

def clean_text(text):
    """
    Cleans extracted PDF text.
    """

    # Join words that were split across a line break with a hyphen
    # e.g. "diabe-\ntes" -> "diabetes"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n\n", text)

    # Remove spaces at beginning/end of lines
    text = "\n".join(line.strip() for line in text.splitlines())

    # Remove empty lines
    lines = [line for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)

    return text.strip()

# --------------------------------------------------
## --------------------------------------------------
# 2b. REMOVE WEBPAGE / PRINT BOILERPLATE
# --------------------------------------------------

def remove_boilerplate(text):
    """
    Removes common browser-print junk that sneaks into WHO PDFs
    when a webpage was printed to PDF instead of using an official
    PDF export (nav menus, timestamps, language switchers, footer
    URLs, and page numbers).
    """

    noise_exact_lines = {
        "donate", "©", "home", "newsroom", "emergencies",
        "data", "about who", "menu", "search",
    }

    timestamp_pattern = re.compile(
        r"^\d{1,2}/\d{1,2}/\d{2,4},?\s*\d{1,2}:\d{2}\s*[AP]M"
    )
    reading_time_pattern = re.compile(
        r"reading time:\s*\d+\s*min", re.IGNORECASE
    )
    language_switcher_pattern = re.compile(
        r"(العربية|中文|Français|Русский|Español)"
    )
    footer_url_pattern = re.compile(
        r"^https?://\S+(\s+\d+/\d+)?$"
    )
    page_number_pattern = re.compile(
        r"^\d+/\d+$"
    )

    cleaned_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            continue
        if lower in noise_exact_lines:
            continue
        if timestamp_pattern.match(stripped):
            continue
        if reading_time_pattern.search(stripped):
            continue
        if language_switcher_pattern.search(stripped):
            continue
        if footer_url_pattern.match(stripped):
            continue
        if page_number_pattern.match(stripped):
            continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()
# --------------------------------------------------
# 3. EXTRACT TEXT FROM ONE PDF (page by page, keeping line structure)
# --------------------------------------------------

def extract_pages(pdf_path):
    """
    Reads a PDF using pdfplumber and returns a list of page texts.
    pdfplumber preserves word spacing far more reliably than pypdf,
    which fixes issues like "nor mal" instead of "normal".
    """

    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:

        print(f"\nReading: {os.path.basename(pdf_path)}")
        print(f"Number of pages: {len(pdf.pages)}")

        for page_number, page in enumerate(pdf.pages, start=1):

            try:
                text = page.extract_text()

                if text:
                    pages_text.append(text)

                print(f"  Processed page {page_number}")

            except Exception as e:
                print(f"  Could not read page {page_number}: {e}")

    return pages_text


# --------------------------------------------------
# 4. DETECT SECTION HEADINGS
# --------------------------------------------------

SENTENCE_STARTER_WORDS = {
    "it", "this", "that", "these", "those", "there", "he", "she",
    "they", "we", "you", "i", "his", "her", "their", "its", "and",
    "but", "or", "so", "however", "therefore", "also", "these are",
}


def is_probable_heading(line, next_line):
    """
    Heuristic check: does this line look like a section heading
    (e.g. "Key facts", "Symptoms", "Prevention") rather than a
    normal sentence, or a mid-sentence line break?
    """

    if not line:
        return False

    word_count = len(line.split())
    first_word = line.split()[0].lower().strip(".,;:") if line.split() else ""

    # Reject anything starting with a pronoun/conjunction —
    # real headings are noun phrases, never sentence fragments
    if first_word in SENTENCE_STARTER_WORDS:
        return False

    # ALL CAPS short lines are almost always headings
    if line.isupper() and 1 <= word_count <= 6:
        return True

    # Short, title-like line, not ending in punctuation,
    # immediately followed by a longer paragraph line
    if (
        word_count <= 6
        and len(line) < 45
        and not line.endswith((".", ",", ";", ":"))
        and line[0].isupper()
        and next_line
        and len(next_line) > 60
    ):
        return True

    return False


def split_into_sections(full_text):
    """
    Splits the cleaned document text into a list of
    (section_name, section_text) tuples using heading detection.
    Anything before the first detected heading is labeled "Introduction".
    """

    lines = full_text.splitlines()
    sections = []

    current_section = "Introduction"
    current_lines = []

    for i, line in enumerate(lines):
        next_line = lines[i + 1] if i + 1 < len(lines) else ""

        if is_probable_heading(line, next_line):
            # Save whatever we've collected so far
            if current_lines:
                sections.append((current_section, "\n".join(current_lines).strip()))

            current_section = line.strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_section, "\n".join(current_lines).strip()))

    # Drop empty sections
    return [(name, text) for name, text in sections if text.strip()]


# --------------------------------------------------
# 5. SPLIT SECTION TEXT INTO CHUNKS
# --------------------------------------------------

def create_chunks(text, chunk_size=1000, overlap=200):
    """
    Splits text into chunks.

    chunk_size = approximate number of characters
    overlap = repeated characters between chunks
    """

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap

    return chunks


# --------------------------------------------------
# 6. PROCESS ALL PDFs
# --------------------------------------------------

def process_all_pdfs():

    pdf_files = [
        file for file in os.listdir(PDF_FOLDER)
        if file.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print("No PDF files found!")
        return

    print(f"\nFound {len(pdf_files)} PDF files.")

    all_chunks = []
    global_chunk_id = 1

    for pdf_file in pdf_files:

        pdf_path = os.path.join(PDF_FOLDER, pdf_file)
        topic = os.path.splitext(pdf_file)[0].replace("_", " ").replace("-", " ").strip()

        # ------------------------------------------
        # Extract + Clean
        # ------------------------------------------

        pages = extract_pages(pdf_path)
        raw_text = "\n".join(pages)
        cleaned_text = clean_text(raw_text)
        cleaned_text = remove_boilerplate(cleaned_text)

        # Save cleaned text for inspection
        text_filename = os.path.splitext(pdf_file)[0] + ".txt"
        text_path = os.path.join(OUTPUT_FOLDER, text_filename)

        with open(text_path, "w", encoding="utf-8") as file:
            file.write(cleaned_text)

        print(f"Cleaned text saved: {text_path}")

        # ------------------------------------------
        # Split into sections, then chunk each section
        # ------------------------------------------

        sections = split_into_sections(cleaned_text)
        print(f"Detected {len(sections)} sections.")

        MIN_CHUNK_LENGTH = 40  # characters — filters out titles/junk fragments

        chunk_number = 0

        for section_name, section_text in sections:

            section_chunks = create_chunks(section_text, chunk_size=2000, overlap=200)

            for chunk in section_chunks:

                if len(chunk) < MIN_CHUNK_LENGTH:
                    continue  # skip tiny, uninformative chunks

                chunk_number += 1

                chunk_data = {
                    "chunk_id": global_chunk_id,
                    "document": pdf_file,
                    "source": "WHO",
                    "topic": topic,
                    "section": section_name,
                    "chunk_number": chunk_number,
                    "text": chunk,
                }

                all_chunks.append(chunk_data)
                global_chunk_id += 1

        print(f"Created {chunk_number} chunks.")
    # --------------------------------------------------
    # 7. SAVE ALL CHUNKS
    # --------------------------------------------------

    output_json = os.path.join(OUTPUT_FOLDER, "who_chunks.json")

    with open(output_json, "w", encoding="utf-8") as file:
        json.dump(all_chunks, file, ensure_ascii=False, indent=2)

    print("\n----------------------------------")
    print("PROCESSING COMPLETE")
    print("----------------------------------")

    print(f"PDFs processed: {len(pdf_files)}")
    print(f"Total chunks: {len(all_chunks)}")
    print(f"Output file: {output_json}")


# --------------------------------------------------
# 8. RUN PROGRAM
# --------------------------------------------------

if __name__ == "__main__":
    process_all_pdfs()