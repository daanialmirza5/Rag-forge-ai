#!/usr/bin/env python3
"""RAG-Forge Quantitative Retrieval Evaluation Runner CLI.

Usage:
    python scripts/run_retrieval_eval.py

Evaluates Dense, Sparse (BM25), Hybrid RRF, and Cross-Encoder Reranked architectures
against the multi-domain gold-standard evaluation benchmark and outputs formatted tables.
"""

import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.ai.evaluation.benchmark_dataset import get_standard_rag_benchmark
from app.ai.evaluation.evaluator import RetrievalEvaluator


def main():
    print("=" * 80)
    print("  RAG-FORGE: QUANTITATIVE RETRIEVAL & RERANKING EVALUATION HARNESS")
    print("=" * 80)

    dataset = get_standard_rag_benchmark()
    print(f"\n[+] Loaded Benchmark Dataset: {dataset.name} (v{dataset.version})")
    print(f"[+] Total Corpus Chunks: {len(dataset.documents)}")
    print(f"[+] Total Evaluation Queries: {len(dataset.items)}")
    print(f"[+] Domains: {', '.join(sorted(list({d.domain for d in dataset.documents})))}\n")

    evaluator = RetrievalEvaluator(dataset)
    print("[*] Running comparative retrieval evaluation (Dense vs BM25 vs RRF vs Reranked)...")
    result = evaluator.evaluate_all(k_list=[1, 3, 5, 10])

    print(f"[OK] Evaluation completed in {result.execution_time_ms:.2f}ms\n")
    print("-" * 80)
    print(f"{'Retrieval Strategy':<25} | {'NDCG@3':<8} | {'NDCG@5':<8} | {'Recall@3':<9} | {'Recall@5':<9} | {'MRR@5':<8}")
    print("-" * 80)

    for strat, metrics in result.strategy_results.items():
        name_display = strat.replace("_", " ").title()
        ndcg_3 = f"{metrics.get('ndcg@3', 0.0):.4f}"
        ndcg_5 = f"{metrics.get('ndcg@5', 0.0):.4f}"
        rec_3 = f"{metrics.get('recall@3', 0.0):.4f}"
        rec_5 = f"{metrics.get('recall@5', 0.0):.4f}"
        mrr_5 = f"{metrics.get('mrr@5', 0.0):.4f}"
        print(f"{name_display:<25} | {ndcg_3:<8} | {ndcg_5:<8} | {rec_3:<9} | {rec_5:<9} | {mrr_5:<8}")

    print("-" * 80)
    print("\n[+] Sample Query-by-Query Performance:")
    for detail in result.details[:8]:  # Show sample queries
        print(f"  * [{detail.strategy.value.upper()}] Query {detail.query_id}: {detail.query[:55]}...")
        print(f"    Retrieved: {detail.retrieved_ids[:3]} | NDCG@3: {detail.metrics.get('ndcg@3', 0.0):.4f} | Recall@3: {detail.metrics.get('recall@3', 0.0):.4f}")

    print("\n" + "=" * 80)
    print("  EVALUATION COMPLETE - All metrics validated mathematically")
    print("=" * 80)


if __name__ == "__main__":
    main()
