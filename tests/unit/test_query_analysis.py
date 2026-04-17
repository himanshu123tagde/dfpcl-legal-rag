from __future__ import annotations

import unittest
from app.retrieval.query_analysis import analyze_query


class QueryAnalysisTests(unittest.TestCase):
    def test_query_analysis_needs_hyde_triggering(self):
        """
        Verify that the heuristic gating logic correctly flags queries that
        need HyDE vs those that don't.
        """
        cases = [
            # Conceptual / Analytical - Should trigger HyDE
            ("What are our liabilities if a vendor delivers software late?", True),
            ("Explain the legal implications of the force majeure clause in this agreement.", True),
            ("How constitutes a material breach under New York law?", True),
            ("Summarize the rights and obligations of the parties regarding IP ownership.", True),
            ("What happens if the sub-contractor fails to provide the required insurance certificates?", True),
            
            # Navigational / Direct - Should skip HyDE
            ("Find the MSA for Acme Corp", False),
            ("Show me the latest judgment from the Bombay High Court", False),
            ("Get the NDA for Project X", False),
            ("lookup contract doc_id:123", False),
            
            # Short queries - Should skip HyDE
            ("MSA status", False),
            ("confidentiality clause", False),
            ("termination notice", False),
            
            # Borderline but conceptual (due to keyword)
            ("Describe the termination process", True),
        ]
        
        for question, expected_hyde in cases:
            with self.subTest(question=question):
                analysis = analyze_query(question)
                self.assertEqual(analysis.needs_hyde, expected_hyde, f"Failed for query: {question}")

    def test_query_analysis_field_extraction(self):
        """
        Verify that metadata extraction still works alongside HyDE detection.
        """
        question = "judgment jurisdiction: Mumbai regarding breach of contract"
        analysis = analyze_query(question)
        
        self.assertEqual(analysis.jurisdiction, "Mumbai")
        self.assertEqual(analysis.doc_type, "judgment")
        self.assertFalse(analysis.needs_hyde)  # 'regarding breach of contract' doesn't trigger length or phrase
        self.assertEqual(analysis.keyword, "regarding") # Chosen from tokens by length


if __name__ == "__main__":
    unittest.main()
