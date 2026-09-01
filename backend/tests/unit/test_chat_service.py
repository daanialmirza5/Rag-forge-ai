from app.services.chat_service import _extract_cited_indices


def test_extracts_unique_indices_in_first_occurrence_order():
    text = "Revenue grew [2] due to expansion [1]. Costs also rose [2]."
    assert _extract_cited_indices(text, num_chunks=3) == [2, 1]


def test_ignores_markers_out_of_range():
    text = "This cites [1] and an invalid [99] marker, and [0] too."
    assert _extract_cited_indices(text, num_chunks=2) == [1]


def test_no_markers_returns_empty_list():
    assert _extract_cited_indices("No citations here.", num_chunks=5) == []


def test_no_chunks_means_nothing_is_in_range():
    assert _extract_cited_indices("Cites [1] anyway.", num_chunks=0) == []
