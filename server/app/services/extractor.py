"""Content Text Extraction & Image Processing Service.

Extracts text from TXT, DOCX, PDF, and inspects PNG/JPG images.
Gracefully handles parsing failures and edge cases.
"""

import io
from typing import Dict, Any, Optional
from pypdf import PdfReader
from docx import Document as DocxDocument
from PIL import Image


class ExtractionService:
    """Extracts text and normalizes document / image content."""

    def extract(self, input_type: str, content: bytes, filename: Optional[str] = None) -> Dict[str, Any]:
        """Extracts text and structural metadata based on input type."""
        if input_type == "TEXT":
            return self._extract_text(content)
        elif input_type == "PDF":
            return self._extract_pdf(content)
        elif input_type == "DOCX":
            return self._extract_docx(content)
        elif input_type in ["IMAGE_PNG", "IMAGE_JPG"]:
            return self._extract_image(content, input_type)
        else:
            raise ValueError(f"Unsupported extraction input type: {input_type}")

    def _extract_text(self, content: bytes) -> Dict[str, Any]:
        """Decodes raw text with fallback encodings."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="replace")

        text = text.strip()
        words = text.split()
        return {
            "text": text,
            "page_count": 1,
            "char_count": len(text),
            "word_count": len(words),
            "metadata": {"encoding": "utf-8"},
        }

    def _extract_pdf(self, content: bytes) -> Dict[str, Any]:
        """Extracts text page by page from PDF using pypdf."""
        try:
            reader = PdfReader(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Corrupt or malformed PDF file: {str(e)}")

        page_texts = []
        for i, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    page_texts.append(page_text.strip())
            except Exception:
                page_texts.append(f"[Page {i+1} unextractable text]")

        full_text = "\n\n".join(page_texts).strip()
        words = full_text.split()
        return {
            "text": full_text,
            "page_count": len(reader.pages),
            "char_count": len(full_text),
            "word_count": len(words),
            "metadata": {
                "num_pages": len(reader.pages),
                "is_encrypted": reader.is_encrypted,
            },
        }

    def _extract_docx(self, content: bytes) -> Dict[str, Any]:
        """Extracts paragraphs and table cells from DOCX using python-docx."""
        try:
            doc = DocxDocument(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Corrupt or malformed DOCX file: {str(e)}")

        text_parts = []
        # Paragraphs
        for p in doc.paragraphs:
            if p.text.strip():
                text_parts.append(p.text.strip())

        # Tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    text_parts.append(" | ".join(row_cells))

        full_text = "\n\n".join(text_parts).strip()
        words = full_text.split()
        return {
            "text": full_text,
            "page_count": 1,  # DOCX doesn't have fixed pagination without word rendering
            "char_count": len(full_text),
            "word_count": len(words),
            "metadata": {
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
            },
        }

    def _extract_image(self, content: bytes, input_type: str) -> Dict[str, Any]:
        """Verifies and inspects image dimensions, color space, and metadata."""
        try:
            image = Image.open(io.BytesIO(content))
            image.verify()  # Validates file integrity
            # Re-open for metadata reading since verify() closes image
            image = Image.open(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Corrupt or unreadable image file: {str(e)}")

        width, height = image.size
        mode = image.mode
        format_name = image.format or ("PNG" if input_type == "IMAGE_PNG" else "JPEG")

        # Descriptive text representation for AI / prompt context
        text = f"[{format_name} Image: {width}x{height} pixels, Mode {mode}]"

        return {
            "text": text,
            "page_count": 1,
            "char_count": len(text),
            "word_count": 0,
            "metadata": {
                "width": width,
                "height": height,
                "mode": mode,
                "format": format_name,
                "aspect_ratio": round(width / max(height, 1), 2),
            },
        }


# Singleton instance
extraction_service = ExtractionService()
