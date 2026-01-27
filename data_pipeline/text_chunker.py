import json
import re
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

from data_pipeline.text_extractor import extract_text_with_metadata


def clean_shimano_text(text: str) -> str:
    """
    Removes standard Shimano footers that repeat on each page and breaks search.
    """
    text = re.sub(r"Ver\.\s*\d+\.\d+.*SHIMANO INC\.", "", text)
    text = re.sub(
        r"Specifications are subject to change without prior notice\.", "", text
    )
    text = re.sub(r" +", " ", text).strip()
    return text


def extract_model_names(text: str) -> list[str]:
    """
    Heuristic for extracting Shimano model names (e.g., RD-R9250, CS-M8100).
    Looks for a pattern: 2-3 capital letters + dash + digits/letters
    """
    # Regex: starting word, 2-3 letters (RD, FC, CS...), dash, then digits/letters
    pattern = r"\b[A-Z]{2,3}-[A-Z0-9]+(?:-[A-Z0-9]+)?\b"
    models = re.findall(pattern, text)
    return sorted(set(models))


def process_data(raw_pages, output_file: Path, chunk_size: int, chunk_overlap: int):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["Model No.", "\n\n", "\n", ". ", " ", ""],
        keep_separator=True,
    )

    processed_chunks = []

    for page in raw_pages:
        for i, chunk_text in enumerate(
            text_splitter.split_text(clean_shimano_text(page["text"]))
        ):
            chunk_doc = {
                "chunk_id": f"{page['source']}_p{page['page_number']}_{i}",
                "text": chunk_text,
                "metadata": {
                    "source": page["source"],
                    "page_number": page["page_number"],
                    "chunk_index": i,
                    "char_count": len(chunk_text),
                    "related_models": extract_model_names(chunk_text),
                },
            }
            processed_chunks.append(chunk_doc)

    print(f"✅ Created {len(processed_chunks)} chunks.")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed_chunks, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved to {output_file}")


if __name__ == "__main__":
    manuals_path = Path(__file__).parent.parent / "manuals"
    pdf_file = manuals_path / "2025-2026_Compatibility_v035_en.pdf"
    output_file = Path("ready_for_es.json")
    chunk_size = 800
    chunk_overlap = 150

    extracted_pages = extract_text_with_metadata(pdf_file)
    process_data(extracted_pages, output_file, chunk_size, chunk_overlap)
