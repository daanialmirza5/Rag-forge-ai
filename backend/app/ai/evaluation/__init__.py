"""RAG-Forge Quantitative Retrieval & Reranking Evaluation Engine.

Provides mathematically rigorous IR metrics (NDCG@K, Recall@K, Precision@K, MRR@K, MAP@K),
benchmark evaluation datasets, and comparative retrievers analysis (Dense vs Sparse vs Hybrid RRF vs Reranked).
"""

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
    BenchmarkItem,
    BenchmarkDataset,
    get_standard_rag_benchmark,
)
from app.ai.evaluation.evaluator import (
    RetrievalStrategy,
    EvaluationResult,
    RetrievalEvaluator,
)

__all__ = [
    "recall_at_k",
    "precision_at_k",
    "mrr_at_k",
    "hit_rate_at_k",
    "dcg_at_k",
    "idcg_at_k",
    "ndcg_at_k",
    "calculate_retrieval_metrics",
    "BenchmarkItem",
    "BenchmarkDataset",
    "get_standard_rag_benchmark",
    "RetrievalStrategy",
    "EvaluationResult",
    "RetrievalEvaluator",
]
