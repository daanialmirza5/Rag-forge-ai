"""Structural check that the retrieval graph is wired the way
`app/ai/graph/rag_graph.py` documents. Running it end-to-end needs a live
DB + AI providers — see `docs/PROGRESS.md` for what's exercised live."""

from app.ai.graph.rag_graph import retrieval_graph


def test_graph_has_expected_nodes_in_order():
    node_names = list(retrieval_graph.get_graph().nodes.keys())
    assert node_names == ["__start__", "rewrite_query", "hybrid_retrieve", "rerank", "__end__"]


def test_graph_edges_form_a_single_linear_path():
    graph = retrieval_graph.get_graph()
    edges = {(e.source, e.target) for e in graph.edges}
    assert edges == {
        ("__start__", "rewrite_query"),
        ("rewrite_query", "hybrid_retrieve"),
        ("hybrid_retrieve", "rerank"),
        ("rerank", "__end__"),
    }
