import uuid

from app.ai.retrieval.bm25_index import _tokenize, _WorkspaceBM25Cache
from app.ai.retrieval.hybrid_retriever import RetrievedChunk, _reciprocal_rank_fusion


def test_tokenize_lowercases_and_splits_on_punctuation():
    assert _tokenize("Hello, World! Foo-Bar_123") == ["hello", "world", "foo", "bar", "123"]


def test_tokenize_simple_sentence():
    assert _tokenize("The Quick Brown Fox.") == ["the", "quick", "brown", "fox"]


def test_rrf_prefers_items_ranked_highly_in_both_lists():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    dense_ranking = [a, b, c]
    sparse_ranking = [a, c, b]

    fused = _reciprocal_rank_fusion(dense_ranking, sparse_ranking)

    assert fused[0].chunk_id == a  # rank 0 in both lists
    assert {r.chunk_id for r in fused} == {a, b, c}
    assert all(isinstance(r, RetrievedChunk) for r in fused)


def test_rrf_includes_items_present_in_only_one_ranking():
    a, b = uuid.uuid4(), uuid.uuid4()
    fused = _reciprocal_rank_fusion([a], [b])
    assert {r.chunk_id for r in fused} == {a, b}


def test_rrf_scores_are_sorted_descending():
    ids = [uuid.uuid4() for _ in range(5)]
    fused = _reciprocal_rank_fusion(ids, list(reversed(ids)))
    scores = [r.fused_score for r in fused]
    assert scores == sorted(scores, reverse=True)


def test_bm25_cache_hits_on_matching_version_and_misses_on_change():
    cache = _WorkspaceBM25Cache()
    workspace_id = uuid.uuid4()
    chunk_ids = [uuid.uuid4(), uuid.uuid4()]

    assert cache.get(workspace_id, version=1) is None

    cache.put(workspace_id, version=1, bm25=None, chunk_ids=chunk_ids)
    hit = cache.get(workspace_id, version=1)
    assert hit is not None
    assert hit[1] == chunk_ids

    # A version bump (from a Redis INCR on ingestion) must miss, even though
    # nothing about the workspace_id key itself changed.
    assert cache.get(workspace_id, version=2) is None


def test_bm25_cache_evicts_least_recently_used():
    cache = _WorkspaceBM25Cache(maxsize=2)
    ws1, ws2, ws3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    cache.put(ws1, version=1, bm25=None, chunk_ids=[])
    cache.put(ws2, version=1, bm25=None, chunk_ids=[])
    cache.put(ws3, version=1, bm25=None, chunk_ids=[])  # evicts ws1 (LRU)

    assert cache.get(ws1, version=1) is None
    assert cache.get(ws2, version=1) is not None
    assert cache.get(ws3, version=1) is not None
