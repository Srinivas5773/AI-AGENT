import unittest
from pathlib import Path
from backend.rag import RAGEngine, RAGDocumentChunk, get_rag_engine, DOCS_DIR


class TestRAG(unittest.TestCase):

    def setUp(self):
        self.rag = RAGEngine(docs_dir=DOCS_DIR)

    def test_txt_parsing_and_chunking(self):
        """Test parsing and chunking TXT documents."""
        syllabus_file = DOCS_DIR / "dbms_syllabus.txt"
        self.assertTrue(syllabus_file.exists())

        chunks = self.rag.parse_txt(syllabus_file)
        self.assertGreater(len(chunks), 0)
        self.assertEqual(chunks[0].filename, "dbms_syllabus.txt")
        self.assertIn("dbms_syllabus.txt", chunks[0].chunk_id)

    def test_rag_semantic_search_and_citations(self):
        """Test retrieving relevant document chunks and source citations."""
        res = self.rag.search("CS301 DBMS Unit 3 Normalization 1NF 2NF 3NF BCNF", top_k=5)
        self.assertEqual(res["status"], "success")
        self.assertGreater(len(res["results"]), 0)

        norm_chunk = next((r for r in res["results"] if "NORMALIZATION" in r["text"].upper()), res["results"][0])
        self.assertIn("source_citation", norm_chunk)
        self.assertTrue(any(k in norm_chunk["filename"].lower() for k in ["syllabus", "syllabi"]))

    def test_rag_missing_evidence(self):
        """Test searching for absent topic returns no results."""
        res = self.rag.search("underwater scuba diving astro-cooking galaxy spaceship", top_k=2)
        self.assertEqual(res["status"], "no_results")
        self.assertEqual(len(res["results"]), 0)

    def test_empty_query_handling(self):
        """Test RAG search with empty string."""
        res = self.rag.search("   ")
        self.assertEqual(res["status"], "error")
        self.assertIn("cannot be empty", res["message"])


if __name__ == "__main__":
    unittest.main()
