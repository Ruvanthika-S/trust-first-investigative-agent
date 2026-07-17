import unittest

from agent import build_evidence_summary, score_source_credibility


class AgentFeatureTests(unittest.TestCase):
    def test_score_source_credibility_for_government_url(self):
        source = {"title": "CDC report", "url": "https://www.cdc.gov/health"}
        result = score_source_credibility(source)
        self.assertEqual(result["label"], "high")
        self.assertGreaterEqual(result["score"], 3)

    def test_build_evidence_summary_counts_support_and_contradiction(self):
        trace = [
            {"step": "decompose", "detail": "Split into: ['one', 'two']"},
            {"step": "search", "detail": "Searched: 'one'", "sources": [{"title": "A", "url": "https://example.com/a"}]},
            {"step": "evaluate", "detail": "SUPPORT: the evidence matches.", "source_url": "https://example.com/a"},
            {"step": "search", "detail": "Searched: 'two'", "sources": [{"title": "B", "url": "https://example.org/b"}]},
            {"step": "evaluate", "detail": "CONTRADICT: the evidence conflicts.", "source_url": "https://example.org/b"},
        ]
        summary = build_evidence_summary(trace)
        self.assertEqual(summary["claim_count"], 2)
        self.assertEqual(summary["evidence_by_claim"][0]["support"], 1)
        self.assertEqual(summary["evidence_by_claim"][1]["contradict"], 1)


if __name__ == "__main__":
    unittest.main()
