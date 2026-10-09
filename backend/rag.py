import json
import logging
import math
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from backend.config import DATA_DIR

logger = logging.getLogger(__name__)

DOCS_DIR = DATA_DIR / "docs"
VECTOR_STORE_PATH = DATA_DIR / "vector_store.json"

# Ensure docs directory exists
DOCS_DIR.mkdir(parents=True, exist_ok=True)


class RAGDocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        text: str,
        filename: str,
        page_number: Optional[int] = None,
        section: Optional[str] = None,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.filename = filename
        self.page_number = page_number
        self.section = section

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "filename": self.filename,
            "page_number": self.page_number,
            "section": self.section,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RAGDocumentChunk":
        return cls(
            chunk_id=data["chunk_id"],
            text=data["text"],
            filename=data["filename"],
            page_number=data.get("page_number"),
            section=data.get("section"),
        )


class PurePythonTFIDF:
    """Fallback TF-IDF vectorizer using standard python math & numpy."""

    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.doc_vectors: List[np.ndarray] = []

    def tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 2]

    def fit_transform(self, corpus: List[str]) -> np.ndarray:
        tokenized_docs = [self.tokenize(doc) for doc in corpus]
        N = len(corpus)

        # Build vocabulary
        words = set(w for doc in tokenized_docs for w in doc)
        self.vocab = {w: idx for idx, w in enumerate(sorted(words))}

        # Calculate IDF
        df = Counter()
        for doc in tokenized_docs:
            for w in set(doc):
                df[w] += 1

        self.idf = {w: math.log((N + 1) / (df[w] + 1)) + 1.0 for w in words}

        # Build Vectors
        matrix = np.zeros((N, len(self.vocab)))
        for doc_idx, doc in enumerate(tokenized_docs):
            counts = Counter(doc)
            length = len(doc) or 1
            for word, count in counts.items():
                if word in self.vocab:
                    col_idx = self.vocab[word]
                    tf = count / length
                    matrix[doc_idx, col_idx] = tf * self.idf[word]

            # Normalize vector
            norm = np.linalg.norm(matrix[doc_idx])
            if norm > 0:
                matrix[doc_idx] /= norm

        self.doc_vectors = matrix
        return matrix

    def transform(self, query: str) -> np.ndarray:
        tokens = self.tokenize(query)
        vec = np.zeros((1, len(self.vocab)))
        counts = Counter(tokens)
        length = len(tokens) or 1

        for word, count in counts.items():
            if word in self.vocab:
                col_idx = self.vocab[word]
                tf = count / length
                vec[0, col_idx] = tf * self.idf[word]

        norm = np.linalg.norm(vec[0])
        if norm > 0:
            vec[0] /= norm
        return vec


class RAGEngine:
    """RAG Document Ingestion, Embedding, and Retrieval System."""

    def __init__(self, docs_dir: Path = DOCS_DIR):
        self.docs_dir = docs_dir
        self.chunks: List[RAGDocumentChunk] = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self.load_or_index_documents()

    def parse_txt(self, file_path: Path) -> List[RAGDocumentChunk]:
        """Parse TXT file into chunks."""
        chunks = []
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            filename = file_path.name
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

            for idx, para in enumerate(paragraphs):
                if len(para) < 20:
                    continue
                chunk_id = f"{filename}_p{idx+1}"
                chunks.append(
                    RAGDocumentChunk(
                        chunk_id=chunk_id,
                        text=para,
                        filename=filename,
                        page_number=1,
                        section=f"Paragraph {idx+1}",
                    )
                )
        except Exception as e:
            logger.error(f"Error parsing TXT {file_path}: {e}")
        return chunks

    def parse_pdf(self, file_path: Path) -> List[RAGDocumentChunk]:
        """Parse PDF file into page-preserved chunks using pypdf."""
        chunks = []
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            filename = file_path.name

            for page_idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text or len(text.strip()) < 20:
                    continue
                page_num = page_idx + 1
                paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= 20]
                if not paras:
                    paras = [text.strip()]

                for sub_idx, para in enumerate(paras):
                    chunk_id = f"{filename}_pg{page_num}_s{sub_idx+1}"
                    chunks.append(
                        RAGDocumentChunk(
                            chunk_id=chunk_id,
                            text=para,
                            filename=filename,
                            page_number=page_num,
                            section=f"Page {page_num}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {e}")
        return chunks

    def parse_docx(self, file_path: Path) -> List[RAGDocumentChunk]:
        """Parse DOCX file into paragraph chunks using python-docx."""
        chunks = []
        try:
            import docx
            doc = docx.Document(str(file_path))
            filename = file_path.name
            paras = [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) >= 20]

            for idx, para in enumerate(paras):
                chunk_id = f"{filename}_p{idx+1}"
                chunks.append(
                    RAGDocumentChunk(
                        chunk_id=chunk_id,
                        text=para,
                        filename=filename,
                        page_number=1,
                        section=f"Paragraph {idx+1}",
                    )
                )
        except Exception as e:
            logger.error(f"Error parsing DOCX {file_path}: {e}")
        return chunks

    def parse_csv(self, file_path: Path) -> List[RAGDocumentChunk]:
        """Parse CSV document into row/section chunks."""
        chunks = []
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            filename = file_path.name

            for idx, row in df.iterrows():
                row_str = ", ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                if len(row_str) >= 15:
                    chunk_id = f"{filename}_row{idx+1}"
                    chunks.append(
                        RAGDocumentChunk(
                            chunk_id=chunk_id,
                            text=row_str,
                            filename=filename,
                            page_number=1,
                            section=f"Row {idx+1}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error parsing CSV document {file_path}: {e}")
        return chunks

    def ingest_all_documents(self) -> List[RAGDocumentChunk]:
        """Crawls docs directory and ingests all supported files."""
        all_chunks: List[RAGDocumentChunk] = []

        if not self.docs_dir.exists():
            return all_chunks

        for file_path in self.docs_dir.glob("*.*"):
            ext = file_path.suffix.lower()
            if ext == ".txt":
                all_chunks.extend(self.parse_txt(file_path))
            elif ext == ".pdf":
                all_chunks.extend(self.parse_pdf(file_path))
            elif ext in [".docx", ".doc"]:
                all_chunks.extend(self.parse_docx(file_path))
            elif ext == ".csv":
                all_chunks.extend(self.parse_csv(file_path))

        self.chunks = all_chunks
        self.build_vector_index()
        self.save_vector_store()
        return self.chunks

    def build_vector_index(self):
        """Builds TF-IDF Vectorizer Matrix over ingested chunks."""
        if not self.chunks:
            self.vectorizer = None
            self.tfidf_matrix = None
            return

        corpus = [c.text for c in self.chunks]
        if SKLEARN_AVAILABLE:
            try:
                self.vectorizer = TfidfVectorizer(
                    ngram_range=(1, 2),
                    stop_words="english",
                    max_features=5000,
                    sublinear_tf=True,
                )
                self.tfidf_matrix = self.vectorizer.fit_transform(corpus)
                return
            except Exception as e:
                logger.warning(f"Sklearn vectorizer failed: {e}. Falling back to PurePythonTFIDF.")

        # Fallback to Pure Python TFIDF
        self.vectorizer = PurePythonTFIDF()
        self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def save_vector_store(self):
        """Persists chunk store metadata to disk."""
        try:
            data = [c.to_dict() for c in self.chunks]
            with open(VECTOR_STORE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")

    def load_or_index_documents(self):
        """Loads vector store or re-indexes documents if missing."""
        if VECTOR_STORE_PATH.exists():
            try:
                with open(VECTOR_STORE_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chunks = [RAGDocumentChunk.from_dict(d) for d in data]
                if self.chunks:
                    self.build_vector_index()
                    return
            except Exception as e:
                logger.warning(f"Error loading vector store: {e}. Re-indexing documents.")

        self.ingest_all_documents()

    def search(self, query: str, top_k: int = 3) -> Dict[str, Any]:
        """Retrieves top_k most relevant chunks for query."""
        if not query or not query.strip():
            return {"status": "error", "message": "Query cannot be empty.", "results": [], "count": 0}

        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            self.ingest_all_documents()

        if not self.chunks or self.vectorizer is None or self.tfidf_matrix is None:
            return {
                "status": "no_results",
                "message": "No academic documents have been ingested yet into the RAG vector store.",
                "results": [],
                "count": 0,
            }

        try:
            query_vec = self.vectorizer.transform([query] if SKLEARN_AVAILABLE and hasattr(self.vectorizer, 'fit_transform') and not isinstance(self.vectorizer, PurePythonTFIDF) else query)
            
            if SKLEARN_AVAILABLE and hasattr(query_vec, 'toarray'):
                similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            else:
                sim_matrix = np.dot(self.vectorizer.doc_vectors, query_vec.T).flatten()
                similarities = sim_matrix

            top_indices = np.argsort(similarities)[::-1]

            results = []
            MIN_SIMILARITY_THRESHOLD = 0.08
            for idx in top_indices:
                score = float(similarities[idx])
                if score < MIN_SIMILARITY_THRESHOLD:
                    continue

                chunk = self.chunks[idx]
                results.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "filename": chunk.filename,
                        "page_number": chunk.page_number,
                        "section": chunk.section,
                        "similarity_score": round(score, 4),
                        "source_citation": f"[{chunk.filename}, Page {chunk.page_number or 1}]",
                    }
                )

                if len(results) >= top_k:
                    break

            if not results:
                return {
                    "status": "no_results",
                    "message": f"No relevant information found in college documents for query '{query}'.",
                    "results": [],
                    "count": 0,
                }

            return {
                "status": "success",
                "message": f"Retrieved {len(results)} relevant document passage(s).",
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return {"status": "error", "message": f"RAG Search Execution Error: {str(e)}", "results": [], "count": 0}


# Singleton RAG instance
_rag_instance: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGEngine()
    return _rag_instance
