import fitz
import json
from pathlib import Path


def extract_text_with_metadata(pdf_path: Path):
    """
    Return a list of dictionaries containing extracted text and metadata for each page in the PDF.
    [
      {"page": 1, "text": "Shimano Manual...", "source": "file.pdf"},
      {"page": 2, "text": "Safety info...", "source": "file.pdf"}
    ]
    """
    doc = fitz.open(pdf_path)
    filename = Path(pdf_path).name

    extracted_pages = []

    for page_num, page in enumerate(doc.pages(), start=1):
        if clean_text := page.get_text().strip():
            extracted_pages.append(
                {
                    "source": filename,
                    "page_number": page_num,
                    "text": clean_text,
                    "char_count": len(clean_text),
                }
            )

    return extracted_pages


if __name__ == "__main__":
    manuals_path = Path(__file__).parent.parent / "manuals"
    pdf_file = manuals_path / "2025-2026_Compatibility_v035_en.pdf"
    output_path = Path("debug_output.json")

    try:
        data = extract_text_with_metadata(pdf_file)

        print(f"✅ Found pages: {len(data)}")
        print("--- Sample of the first page ---")
        print(json.dumps(data[0], indent=2, ensure_ascii=False))

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"💾 Saved to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        print("Check if the file exists and the path is correct.")
