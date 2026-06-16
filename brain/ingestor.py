import os
import tempfile
from pathlib import Path


class Ingestor:
    SUPPORTED = {
        ".txt": "texto",
        ".md": "markdown",
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".html": "html",
        ".css": "css",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".csv": "csv",
        ".xml": "xml",
        ".pdf": "pdf",
        ".docx": "word",
        ".png": "image",
        ".jpg": "image",
        ".jpeg": "image",
        ".gif": "image",
    }

    def __init__(self, vector_store=None):
        if vector_store is None:
            from brain.vector_store import VectorStore
            vector_store = VectorStore()
        self.store = vector_store

    def ingest_file(self, file_path):
        path = Path(file_path)
        if not path.exists():
            return f"Arquivo não encontrado: {file_path}"
        ext = path.suffix.lower()
        if ext not in self.SUPPORTED:
            return f"Extensão não suportada: {ext}"

        text = self._extract_text(file_path, ext)
        if not text:
            return f"Não foi possível extrair texto de {file_path}"

        chunks = self._chunk_text(text)
        count = 0
        for chunk in chunks:
            doc_id = f"{path.stem}_{hash(chunk) % 10**8:08x}"
            self.store.add_text(
                chunk,
                metadata={
                    "source": str(path),
                    "type": self.SUPPORTED[ext],
                    "filename": path.name,
                },
                doc_id=doc_id
            )
            count += 1
        return f"{path.name}: {count} chunks indexados"

    def ingest_directory(self, directory, recursive=True):
        path = Path(directory)
        if not path.is_dir():
            return f"Diretório não encontrado: {directory}"
        results = []
        pattern = "**/*" if recursive else "*"
        for f in sorted(path.glob(pattern)):
            if f.suffix.lower() in self.SUPPORTED and f.is_file():
                result = self.ingest_file(str(f))
                results.append(result)
        return results

    def ingest_text(self, text, source="manual"):
        chunks = self._chunk_text(text)
        count = 0
        for chunk in chunks:
            doc_id = f"{source}_{hash(chunk) % 10**8:08x}"
            self.store.add_text(
                chunk,
                metadata={"source": source, "type": "text"},
                doc_id=doc_id
            )
            count += 1
        return f"{count} chunks indexados de entrada manual"

    def _extract_text(self, file_path, ext):
        try:
            if ext == ".pdf":
                return self._extract_pdf(file_path)
            elif ext == ".docx":
                return self._extract_docx(file_path)
            elif ext in (".png", ".jpg", ".jpeg", ".gif"):
                return self._extract_image(file_path)
            else:
                with open(file_path, "r", errors="ignore") as f:
                    return f.read()
        except Exception as e:
            return f"[ERRO] {e}"

    def _extract_pdf(self, file_path):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(file_path)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            if text.strip():
                return text
        except ImportError:
            pass
        try:
            from pdf2image import convert_from_path
            import pytesseract
            images = convert_from_path(file_path)
            return "\n".join(pytesseract.image_to_string(img, lang="por") for img in images)
        except ImportError:
            return ""

    def _extract_docx(self, file_path):
        try:
            from docx import Document
            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            return f"[ERRO] {e}"

    def _extract_image(self, file_path):
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img, lang="por")
            return text.strip()
        except ImportError:
            return ""

    def _chunk_text(self, text, chunk_size=500, overlap=50):
        if not text:
            return []
        words = text.split()
        if len(words) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk = " ".join(words[start:end])
            if chunk.strip():
                chunks.append(chunk)
            start += chunk_size - overlap
        return chunks
