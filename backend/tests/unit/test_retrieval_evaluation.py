"""Unit tests for RAG-Forge quantitative retrieval & reranking evaluation engine."""

import unittest
import math
from app.ai.evaluation.metrics import (
    recall_at_k,
    precision_at_k,
    mrr_at_k,
    hit_rate_at_k,
    dcg_at_k,
    idcg_at_k,
    ndcg_at_k,
    calculate_retrieval_metrics,
)
from app.ai.evaluation.benchmark_dataset import (
    BenchmarkDataset,
    BenchmarkItem,
    DocumentChunk,
    get_standard_rag_benchmark,
)
from app.ai.evaluation.evaluator import (
    RetrievalStrategy,
    DeterministicBM25Scorer,
    DeterministicDenseScorer,
    reciprocal_rank_fusion,
    RetrievalEvaluator,
)


class TestRetrievalMetrics(unittest.TestCase):
    """Verifies mathematical correctness of IR evaluation metrics."""

    def test_recall_at_k(self):
        relevant = {"doc1", "doc2", "doc3"}
        retrieved = ["doc1", "doc4", "doc2", "doc5"]

        # K=1: 1 hit out of 3 -> 1/3
        self.assertAlmostEqual(recall_at_k(retrieved, relevant, k=1), 1.0 / 3.0, places=4)
        # K=2: 1 hit out of 3 -> 1/3
        self.assertAlmostEqual(recall_at_k(retrieved, relevant, k=2), 1.0 / 3.0, places=4)
        # K=3: 2 hits out of 3 -> 2/3
        self.assertAlmostEqual(recall_at_k(retrieved, relevant, k=3), 2.0 / 3.0, places=4)
        # Empty inputs
        self.assertEqual(recall_at_k([], relevant, k=5), 0.0)
        self.assertEqual(recall_at_k(retrieved, set(), k=5), 0.0)

    def test_precision_at_k(self):
        relevant = {"doc1", "doc2"}
        retrieved = ["doc1", "doc3", "doc2", "doc4"]

        # K=1: 1/1 = 1.0
        self.assertEqual(precision_at_k(retrieved, relevant, k=1), 1.0)
        # K=2: 1/2 = 0.5
        self.assertEqual(precision_at_k(retrieved, relevant, k=2), 0.5)
        # K=4: 2/4 = 0.5
        self.assertEqual(precision_at_k(retrieved, relevant, k=4), 0.5)
        # K=0 or empty
        self.assertEqual(precision_at_k(retrieved, relevant, k=0), 0.0)

    def test_mrr_at_k(self):
        relevant = {"doc3"}
        retrieved = ["doc1", "doc2", "doc3", "doc4"]

        # doc3 is at rank 3 -> MRR = 1/3
        self.assertAlmostEqual(mrr_at_k(retrieved, relevant, k=5), 1.0 / 3.0, places=4)
        # If K=2, doc3 is outside top-K -> MRR = 0.0
        self.assertEqual(mrr_at_k(retrieved, relevant, k=2), 0.0)

    def test_hit_rate_at_k(self):
        relevant = {"doc2"}
        retrieved = ["doc1", "doc2", "doc3"]

        self.assertEqual(hit_rate_at_k(retrieved, relevant, k=1), 0.0)
        self.assertEqual(hit_rate_at_k(retrieved, relevant, k=2), 1.0)
        self.assertEqual(hit_rate_at_k(retrieved, relevant, k=3), 1.0)

    def test_dcg_and_idcg_calculation(self):
        ground_truth = {"d1": 3.0, "d2": 2.0, "d3": 1.0}
        
        # Perfect retrieval: ["d1", "d2", "d3"]
        # DCG@3 = (2^3 - 1)/log2(2) + (2^2 - 1)/log2(3) + (2^1 - 1)/log2(4)
        #       = 7/1.0 + 3/1.5849625 + 1/2.0
        #       = 7.0 + 1.892789 + 0.5 = 9.392789
        expected_dcg = (7.0 / 1.0) + (3.0 / math.log2(3)) + (1.0 / 2.0)
        actual_dcg = dcg_at_k(["d1", "d2", "d3"], ground_truth, k=3)
        actual_idcg = idcg_at_k(ground_truth, k=3)

        self.assertAlmostEqual(actual_dcg, expected_dcg, places=4)
        self.assertAlmostEqual(actual_idcg, expected_dcg, places=4)
        self.assertAlmostEqual(ndcg_at_k(["d1", "d2", "d3"], ground_truth, k=3), 1.0, places=4)

    def test_ndcg_at_k_imperfect_ranking(self):
        ground_truth = {"d1": 3.0, "d2": 2.0}
        # Inverted ranking: ["d2", "d1"]
        # DCG@2 = (2^2 - 1)/1 + (2^3 - 1)/log2(3) = 3 + 7/1.5849625 = 3 + 4.4165 = 7.4165
        # IDCG@2 = (2^3 - 1)/1 + (2^2 - 1)/log2(3) = 7 + 3/1.5849625 = 7 + 1.8928 = 8.8928
        # NDCG@2 = 7.4165 / 8.8928 ≈ 0.8339
        ndcg_val = ndcg_at_k(["d2", "d1"], ground_truth, k=2)
        self.assertTrue(0.80 < ndcg_val < 0.90)
        self.assertTrue(ndcg_val < 1.0)

    def test_calculate_retrieval_metrics_dict(self):
        ground_truth = {"d1": 3.0, "d2": 2.0, "d3": 0.0}
        retrieved = ["d1", "d3", "d2"]
        metrics = calculate_retrieval_metrics(retrieved, ground_truth, k_list=[1, 3])

        self.assertIn("recall@1", metrics)
        self.assertIn("precision@1", metrics)
        self.assertIn("mrr@1", metrics)
        self.assertIn("hit_rate@1", metrics)
        self.assertIn("ndcg@1", metrics)
        self.assertIn("ndcg@3", metrics)
        self.assertEqual(metrics["recall@1"], 0.5)
        self.assertEqual(metrics["precision@1"], 1.0)


class TestRetrievalEvaluator(unittest.TestCase):
    """Tests the benchmark dataset, BM25, Dense, RRF, and evaluator execution."""

    def setUp(self):
        self.benchmark = get_standard_rag_benchmark()
        self.evaluator = RetrievalEvaluator(self.benchmark)

    def test_benchmark_structure(self):
        self.assertGreaterEqual(len(self.benchmark.documents), 20)
        self.assertGreaterEqual(len(self.benchmark.items), 6)
        doc = self.benchmark.get_document_by_id("DOC-DIST-01")
        self.assertIsNotNone(doc)
        self.assertEqual(doc.domain, "distributed_systems")

    def test_bm25_scorer(self):
        scorer = DeterministicBM25Scorer(self.benchmark.documents)
        results = scorer.score("Raft consensus leader election", top_k=3)
        self.assertTrue(len(results) > 0)
        top_doc_ids = [doc_id for doc_id, _ in results]
        self.assertTrue("DOC-DIST-01" in top_doc_ids or "DOC-DIST-02" in top_doc_ids)

    def test_rrf_fusion(self):
        dense_ranking = ["DOC-DIST-01", "DOC-DIST-02", "DOC-DIST-03"]
        sparse_ranking = ["DOC-DIST-02", "DOC-DIST-01", "DOC-DIST-04"]
        fused = reciprocal_rank_fusion(dense_ranking, sparse_ranking, top_k=4)

        fused_ids = [doc_id for doc_id, _ in fused]
        # DOC-DIST-01 and DOC-DIST-02 should be top 2
        self.assertIn(fused_ids[0], ["DOC-DIST-01", "DOC-DIST-02"])
        self.assertIn(fused_ids[1], ["DOC-DIST-01", "DOC-DIST-02"])

    def test_evaluator_all_strategies(self):
        result = self.evaluator.evaluate_all(k_list=[1, 3, 5])
        
        self.assertEqual(result.num_queries, len(self.benchmark.items))
        self.assertIn("dense_only", result.strategy_results)
        self.assertIn("sparse_bm25", result.strategy_results)
        self.assertIn("hybrid_rrf", result.strategy_results)
        self.assertIn("hybrid_reranked", result.strategy_results)

        # Check macro-averaged metrics exist
        for strat in ["dense_only", "sparse_bm25", "hybrid_rrf", "hybrid_reranked"]:
            metrics = result.strategy_results[strat]
            self.assertIn("ndcg@3", metrics)
            self.assertIn("recall@3", metrics)
            self.assertIn("mrr@3", metrics)
            self.assertGreater(metrics["ndcg@3"], 0.0)

        # Details length = num_queries * 4 strategies
        self.assertEqual(len(result.details), len(self.benchmark.items) * 4)


if __name__ == "__main__":
    unittest.main()
