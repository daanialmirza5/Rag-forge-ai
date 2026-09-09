"""Information Retrieval (IR) Evaluation Metrics for RAG Systems.

Includes standard, mathematically rigorous implementations of:
- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR@K)
- Hit Rate@K
- Discounted Cumulative Gain (DCG@K)
- Normalized Discounted Cumulative Gain (NDCG@K)
- Mean Average Precision (MAP@K)
"""

import math
from typing import Dict, List, Set, Union


def hit_rate_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Computes Hit Rate@K (1.0 if at least one relevant document is in top-K, 0.0 otherwise)."""
    if k <= 0 or not relevant_ids:
        return 0.0
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    return 1.0 if any(doc_id in rel_set for doc_id in top_k) else 0.0


def precision_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Computes Precision@K: (number of relevant items in top-K) / K."""
    if k <= 0:
        return 0.0
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for doc_id in top_k if doc_id in rel_set)
    return hits / float(k)


def recall_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Computes Recall@K: (number of relevant items in top-K) / (total relevant items)."""
    if k <= 0 or not relevant_ids:
        return 0.0
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    hits = sum(1 for doc_id in top_k if doc_id in rel_set)
    return hits / float(len(rel_set))


def mrr_at_k(retrieved_ids: List[str], relevant_ids: Union[Set[str], List[str]], k: int) -> float:
    """Computes Reciprocal Rank@K for a single query: 1 / rank of first relevant item, or 0.0."""
    if k <= 0 or not relevant_ids:
        return 0.0
    rel_set = set(relevant_ids)
    top_k = retrieved_ids[:k]
    for rank, doc_id in enumerate(top_k, start=1):
        if doc_id in rel_set:
            return 1.0 / float(rank)
    return 0.0


def dcg_at_k(retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int) -> float:
    """Computes Discounted Cumulative Gain (DCG@K) using standard logarithmic discount:

    DCG@K = sum_{i=1}^K (2^{rel_i} - 1) / log_2(i + 1)
    """
    if k <= 0 or not retrieved_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    dcg = 0.0
    for rank, doc_id in enumerate(top_k, start=1):
        rel = relevance_scores.get(doc_id, 0.0)
        if rel > 0.0:
            numerator = (2.0 ** rel) - 1.0
            denominator = math.log2(rank + 1.0)
            dcg += numerator / denominator
    return dcg


def idcg_at_k(relevance_scores: Dict[str, float], k: int) -> float:
    """Computes Ideal Discounted Cumulative Gain (IDCG@K) by ranking all ground truth scores descending."""
    if k <= 0 or not relevance_scores:
        return 0.0
    sorted_scores = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for rank, rel in enumerate(sorted_scores, start=1):
        if rel > 0.0:
            numerator = (2.0 ** rel) - 1.0
            denominator = math.log2(rank + 1.0)
            idcg += numerator / denominator
    return idcg


def ndcg_at_k(retrieved_ids: List[str], relevance_scores: Dict[str, float], k: int) -> float:
    """Computes Normalized Discounted Cumulative Gain (NDCG@K) = DCG@K / IDCG@K.

    Returns a value in [0.0, 1.0].
    """
    ideal_dcg = idcg_at_k(relevance_scores, k)
    if ideal_dcg <= 0.0:
        return 0.0
    actual_dcg = dcg_at_k(retrieved_ids, relevance_scores, k)
    return min(1.0, actual_dcg / ideal_dcg)


def calculate_retrieval_metrics(
    retrieved_ids: List[str],
    ground_truth: Dict[str, float],
    k_list: List[int] = None,
    relevance_threshold: float = 1.0,
) -> Dict[str, float]:
    """Calculates a comprehensive dictionary of retrieval metrics across various K cutoffs."""
    if k_list is None:
        k_list = [1, 3, 5, 10]

    # Binary relevant set for recall/precision/mrr
    relevant_ids = {doc_id for doc_id, score in ground_truth.items() if score >= relevance_threshold}

    metrics: Dict[str, float] = {}
    for k in k_list:
        metrics[f"recall@{k}"] = round(recall_at_k(retrieved_ids, relevant_ids, k), 4)
        metrics[f"precision@{k}"] = round(precision_at_k(retrieved_ids, relevant_ids, k), 4)
        metrics[f"mrr@{k}"] = round(mrr_at_k(retrieved_ids, relevant_ids, k), 4)
        metrics[f"hit_rate@{k}"] = round(hit_rate_at_k(retrieved_ids, relevant_ids, k), 4)
        metrics[f"ndcg@{k}"] = round(ndcg_at_k(retrieved_ids, ground_truth, k), 4)

    return metrics
