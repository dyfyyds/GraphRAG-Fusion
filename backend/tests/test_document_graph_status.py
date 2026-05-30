import pytest

from app.services.document_service import decide_document_status_after_graph


def test_graph_failure_keeps_chunks_and_marks_document_graph_failed():
    doc = type("Doc", (), {"status": "building_graph", "chunk_count": 3, "error_message": None})()

    decide_document_status_after_graph(
        doc,
        {"success": False, "message": "LLM 返回内容不是有效 JSON", "entity_count": 0, "relation_count": 0},
    )

    assert doc.status == "graph_failed"
    assert doc.chunk_count == 3
    assert "LLM 返回内容不是有效 JSON" in doc.error_message


def test_graph_success_marks_document_completed():
    doc = type("Doc", (), {"status": "building_graph", "chunk_count": 2, "error_message": "old"})()

    decide_document_status_after_graph(
        doc,
        {"success": True, "message": "图谱构建完成", "entity_count": 1, "relation_count": 1},
    )

    assert doc.status == "completed"
    assert doc.error_message is None
