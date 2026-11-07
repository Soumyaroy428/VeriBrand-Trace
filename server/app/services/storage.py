"""Secure File Storage & Signature Validation Service.

Enforces:
1. File signature (magic bytes) validation — never trust extensions alone.
2. File size enforcement (max 10MB per document/image).
3. Path traversal attack prevention.
4. Cryptographic SHA-256 content hashing for immutability.
5. Workspace-isolated storage paths.
"""

import os
import re
import hashlib
from typing import Tuple, Dict, Any, Optional
from pathlib import Path

# Base upload directory relative to server root
BASE_STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit

# Magic byte signatures
SIGNATURES = {
    "PDF": b"%PDF-",
    "PNG": b"\x89PNG\r\n\x1a\n",
    "JPG": b"\xff\xd8\xff",
    "DOCX": b"PK\x03\x04",
}


def sanitize_filename(filename: str) -> str:
    """Strips path traversal sequences and special characters from filename."""
    # Remove directory separators and null bytes
    clean = os.path.basename(filename).replace("\x00", "")
    # Allow alphanumeric, dots, underscores, dashes
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", clean)
    if not clean:
        clean = "uploaded_file"
    return clean


def detect_file_type(content: bytes, filename: str) -> Tuple[str, str]:
    """Detects and validates input type using magic bytes and MIME mapping.

    Returns:
        (input_type, mime_type) e.g. ("PDF", "application/pdf")

    Raises:
        ValueError if file signature does not match expected format or is unsupported.
    """
    if len(content) == 0:
        raise ValueError("Uploaded file is empty (0 bytes)")

    ext = os.path.splitext(filename.lower())[1]

    # 1. PDF Check
    if content.startswith(SIGNATURES["PDF"]):
        return "PDF", "application/pdf"
    elif ext == ".pdf":
        raise ValueError("Invalid PDF: File signature mismatch (%PDF- header missing)")

    # 2. PNG Check
    if content.startswith(SIGNATURES["PNG"]):
        return "IMAGE_PNG", "image/png"
    elif ext == ".png":
        raise ValueError("Invalid PNG: File signature mismatch (PNG magic bytes missing)")

    # 3. JPEG Check
    if content.startswith(SIGNATURES["JPG"]):
        return "IMAGE_JPG", "image/jpeg"
    elif ext in [".jpg", ".jpeg"]:
        raise ValueError("Invalid JPEG: File signature mismatch (SOI marker missing)")

    # 4. DOCX Check (Zip archive with [Content_Types].xml or standard PK header)
    if content.startswith(SIGNATURES["DOCX"]):
        # Verify it's a docx and not just any zip if filename has docx
        if ext == ".docx":
            return "DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif ext == ".zip":
            raise ValueError("ZIP archives must have a .docx extension for document audits")
        return "DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif ext == ".docx":
        raise ValueError("Invalid DOCX: File signature mismatch (PK zip header missing)")

    # 5. Plain Text Check
    if ext in [".txt", ".md", ".json", ".csv", ".text"] or not ext:
        try:
            content.decode("utf-8")
            return "TEXT", "text/plain"
        except UnicodeDecodeError:
            try:
                content.decode("latin-1")
                return "TEXT", "text/plain"
            except Exception:
                raise ValueError("Binary file format not supported or invalid text encoding")

    raise ValueError(f"Unsupported file format: {ext or 'unknown'}. Supported formats: TXT, DOCX, PDF, PNG, JPG")


class StorageService:
    """Manages secure file persistence with workspace boundaries."""

    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or BASE_STORAGE_DIR
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def validate_file(
        self,
        filename: str,
        content: bytes,
        max_size: int = MAX_FILE_SIZE_BYTES,
    ) -> Tuple[str, str]:
        """Validates file size and binary signature."""
        if len(content) > max_size:
            max_mb = max_size / (1024 * 1024)
            raise ValueError(f"File size exceeds maximum allowable limit of {max_mb:.1f} MB")

        return detect_file_type(content, filename)

    def save_file(
        self,
        workspace_id: str,
        filename: str,
        content: bytes,
    ) -> Dict[str, Any]:
        """Validates, hashes, and stores file immutably.

        Returns metadata dictionary including storage_key and content_hash.
        """
        input_type, mime_type = self.validate_file(filename, content)
        content_hash = hashlib.sha256(content).hexdigest()
        clean_name = sanitize_filename(filename)

        # Build workspace-isolated path
        workspace_dir = self.root_dir / workspace_id
        workspace_dir.mkdir(parents=True, exist_ok=True)

        storage_key = f"{workspace_id}/{content_hash[:16]}_{clean_name}"
        target_path = self.root_dir / storage_key

        # Write file immutably (if already exists, content is identical because of content_hash)
        if not target_path.exists():
            target_path.write_bytes(content)

        return {
            "storage_key": storage_key,
            "content_hash": content_hash,
            "file_size": len(content),
            "input_type": input_type,
            "mime_type": mime_type,
            "filename": clean_name,
        }

    def get_file_bytes(self, storage_key: str) -> bytes:
        """Retrieves raw file bytes ensuring path stays inside root_dir."""
        target_path = (self.root_dir / storage_key).resolve()
        if not str(target_path).startswith(str(self.root_dir.resolve())):
            raise ValueError("Path traversal attempt detected")
        if not target_path.exists():
            raise FileNotFoundError(f"Stored file not found for key: {storage_key}")
        return target_path.read_bytes()


# Singleton instance
storage_service = StorageService()

