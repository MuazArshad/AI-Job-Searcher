import io
import fitz  # PyMuPDF
from docx import Document


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using PyMuPDF."""
    text_parts = []
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            text_parts.append(page.get_text("text"))
        doc.close()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}")
    return "\n".join(text_parts).strip()


def extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        doc = Document(io.BytesIO(file_bytes))
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n".join(paragraphs).strip()
    except Exception as e:
        raise ValueError(f"Failed to parse DOCX: {e}")


def parse_resume(filename: str, file_bytes: bytes) -> str:
    """Auto-detect file type and extract text."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower.endswith(".docx") or lower.endswith(".doc"):
        return extract_text_from_docx(file_bytes)
    else:
        # Try to decode as plain text
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except Exception:
            raise ValueError("Unsupported file format. Please upload a PDF or DOCX file.")
