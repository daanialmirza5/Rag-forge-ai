"""Comparative Retrieval & Reranking Evaluation Harness.

Simulates and evaluates:
1. Dense Retrieval (Semantic vector similarity)
2. Sparse Retrieval (BM25 Okapi lexical scoring)
3. Hybrid Retrieval (Reciprocal Rank Fusion - RRF)
4. Hybrid + Cross-Encoder Reranker

Computes macro-averaged NDCG@K, Recall@K, Precision@K, and MRR@K across benchmarks.
"""

import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Set, Tuple

from app.ai.evaluation.benchmark_dataset import BenchmarkDataset, BenchmarkItem, DocumentChunk
from app.ai.evaluation.metrics import calculate_retrieval_metrics, ndcg_at_k, recall_at_k, mrr_at_k


class RetrievalStrategy(str, Enum):
    DENSE_ONLY = "dense_only"
    SPARSE_BM25 = "sparse_bm25"
    HYBRID_RRF = "hybrid_rrf"
    HYBRID_RERANKED = "hybrid_reranked"


def _tokenize(text: str) -> List[str]:
    return [token for token in re.split(r"[^a-zA-Z0-9_]+", text.lower()) if token]


class DeterministicBM25Scorer:
    """Zero-dependency reference implementation of Okapi BM25 scoring."""

    def __init__(self, documents: List[DocumentChunk], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.num_docs = len(documents)
        self.doc_tokens: Dict[str, List[str]] = {
            doc.id: _tokenize(f"{doc.content} {' '.join(doc.metadata.values())}")
            for doc in documents
        }
        self.doc_lengths: Dict[str, int] = {
            doc_id: len(tokens) for doc_id, tokens in self.doc_tokens.items()
        }
        self.avg_doc_len = (
            sum(self.doc_lengths.values()) / float(self.num_docs) if self.num_docs > 0 else 1.0
        )
        self.doc_freq: Dict[str, int] = {}
        for tokens in self.doc_tokens.values():
            for unique_token in set(tokens):
                self.doc_freq[unique_token] = self.doc_freq.get(unique_token, 0) + 1

    def score(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        query_tokens = _tokenize(query)
        if not query_tokens or self.num_docs == 0:
            return []

        scores: Dict[str, float] = {}
        for doc_id, tokens in self.doc_tokens.items():
            doc_len = self.doc_lengths[doc_id]
            doc_score = 0.0
            term_counts: Dict[str, int] = {}
            for t in tokens:
                term_counts[t] = term_counts.get(t, 0) + 1

            for q_token in query_tokens:
                if q_token in term_counts:
                    tf = term_counts[q_token]
                    df = self.doc_freq.get(q_token, 0)
                    idf = math.log(1.0 + (self.num_docs - df + 0.5) / (df + 0.5))
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                    doc_score += idf * (numerator / denominator)

            scores[doc_id] = doc_score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


class DeterministicDenseScorer:
    """Semantic vector representation simulator using sublinear TF-IDF and n-gram overlap."""

    def __init__(self, documents: List[DocumentChunk]):
        self.documents = documents
        self.doc_tokens = {
            doc.id: set(_tokenize(f"{doc.content} {doc.domain}")) for doc in documents
        }

    def score(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        query_tokens = set(_tokenize(query))
        scores: Dict[str, float] = {}
        for doc_id, doc_toks in self.doc_tokens.items():
            if not query_tokens or not doc_toks:
                scores[doc_id] = 0.0
                continue
            intersection = query_tokens.intersection(doc_toks)
            jaccard = len(intersection) / float(len(query_tokens.union(doc_toks)))
            scores[doc_id] = jaccard

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def reciprocal_rank_fusion(
    dense_ranking: List[str], sparse_ranking: List[str], rrf_k: int = 60, top_k: int = 10
) -> List[Tuple[str, float]]:
    """Reciprocal Rank Fusion (RRF) combining dense and sparse ranking lists."""
    scores: Dict[str, float] = {}
    for rank, doc_id in enumerate(dense_ranking):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)
    for rank, doc_id in enumerate(sparse_ranking):
        scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (rrf_k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]


def cross_encoder_rerank(
    query: str, candidate_doc_ids: List[str], documents_map: Dict[str, DocumentChunk], top_k: int = 10
) -> List[Tuple[str, float]]:
    """Simulates cross-encoder second-stage reranker scoring query-candidate chunk interactions."""
    q_tokens = _tokenize(query)
    q_set = set(q_tokens)

    reranked: List[Tuple[str, float]] = []
    for doc_id in candidate_doc_ids:
        doc = documents_map.get(doc_id)
        if not doc:
            continue
        doc_toks = _tokenize(doc.content)
        overlap = sum(1 for t in doc_toks if t in q_set)
        
        # Position and exact phrase match bonus
        exact_match_bonus = 1.5 if any(re.search(r"\b" + re.escape(t) + r"\b", doc.content, re.I) for t in q_tokens if len(t) > 4) else 0.0
        score = (overlap / (len(doc_toks) + 1.0)) * 10.0 + exact_match_bonus
        reranked.append((doc_id, score))

    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked[:top_k]


@dataclass
class QueryEvaluationDetail:
    query_id: str
    query: str
    strategy: RetrievalStrategy
    retrieved_ids: List[str]
    metrics: Dict[str, float]


@dataclass
class EvaluationResult:
    dataset_name: str
    num_queries: int
    strategy_results: Dict[str, Dict[str, float]]  # strategy -> metric_name -> avg_score
    details: List[QueryEvaluationDetail] = field(default_factory=list)
    execution_time_ms: float = 0.0


class RetrievalEvaluator:
    """Evaluates and benchmarks multiple RAG retrieval architectures against ground truth."""

    def __init__(self, dataset: BenchmarkDataset):
        self.dataset = dataset
        self.bm25_scorer = DeterministicBM25Scorer(dataset.documents)
        self.dense_scorer = DeterministicDenseScorer(dataset.documents)
        self.docs_map = {doc.id: doc for doc in dataset.documents}

    def run_strategy(
        self, item: BenchmarkItem, strategy: RetrievalStrategy, top_k: int = 10
    ) -> List[str]:
        if strategy == RetrievalStrategy.SPARSE_BM25:
            scored = self.bm25_scorer.score(item.query, top_k=top_k)
            return [doc_id for doc_id, _ in scored]

        elif strategy == RetrievalStrategy.DENSE_ONLY:
            scored = self.dense_scorer.score(item.query, top_k=top_k)
            return [doc_id for doc_id, _ in scored]

        elif strategy == RetrievalStrategy.HYBRID_RRF:
            dense_top = [doc_id for doc_id, _ in self.dense_scorer.score(item.query, top_k=20)]
            sparse_top = [doc_id for doc_id, _ in self.bm25_scorer.score(item.query, top_k=20)]
            fused = reciprocal_rank_fusion(dense_top, sparse_top, top_k=top_k)
            return [doc_id for doc_id, _ in fused]

        elif strategy == RetrievalStrategy.HYBRID_RERANKED:
            dense_top = [doc_id for doc_id, _ in self.dense_scorer.score(item.query, top_k=20)]
            sparse_top = [doc_id for doc_id, _ in self.bm25_scorer.score(item.query, top_k=20)]
            fused_candidates = [doc_id for doc_id, _ in reciprocal_rank_fusion(dense_top, sparse_top, top_k=20)]
            reranked = cross_encoder_rerank(item.query, fused_candidates, self.docs_map, top_k=top_k)
            return [doc_id for doc_id, _ in reranked]

        return []

    def evaluate_all(self, k_list: List[int] = None) -> EvaluationResult:
        """Evaluates all 4 retrieval strategies across the benchmark dataset."""
        if k_list is None:
            k_list = [1, 3, 5, 10]

        start_time = time.perf_counter()
        strategies = [
            RetrievalStrategy.DENSE_ONLY,
            RetrievalStrategy.SPARSE_BM25,
            RetrievalStrategy.HYBRID_RRF,
            RetrievalStrategy.HYBRID_RERANKED,
        ]

        strategy_metrics_accum: Dict[str, Dict[str, List[float]]] = {
            strat.value: {} for strat in strategies
        }
        details: List[QueryEvaluationDetail] = []

        for item in self.dataset.items:
            for strat in strategies:
                retrieved_ids = self.run_strategy(item, strat, top_k=max(k_list))
                metrics = calculate_retrieval_metrics(retrieved_ids, item.ground_truth_relevance, k_list=k_list)

                details.append(
                    QueryEvaluationDetail(
                        query_id=item.query_id,
                        query=item.query,
                        strategy=strat,
                        retrieved_ids=retrieved_ids,
                        metrics=metrics,
                    )
                )

                for m_name, m_val in metrics.items():
                    if m_name not in strategy_metrics_accum[strat.value]:
                        strategy_metrics_accum[strat.value][m_name] = []
                    strategy_metrics_accum[strat.value][m_name].append(m_val)

        # Macro average across queries
        strategy_results: Dict[str, Dict[str, float]] = {}
        for strat_name, metric_dict in strategy_metrics_accum.items():
            strategy_results[strat_name] = {
                m_name: round(sum(vals) / len(vals), 4) if vals else 0.0
                for m_name, vals in metric_dict.items()
            }

        elapsed = (time.perf_counter() - start_time) * 1000.0

        return EvaluationResult(
            dataset_name=self.dataset.name,
            num_queries=len(self.dataset.items),
            strategy_results=strategy_results,
            details=details,
            execution_time_ms=round(elapsed, 2),
        )
