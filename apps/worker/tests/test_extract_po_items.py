import pytest
from celery_worker.tasks import extract_po_items as extract_po_items_module


def test_split_document_into_chunks_respects_character_limit() -> None:
    document_text = "\n".join(["A" * 4000, "B" * 4000, "C" * 4000])

    chunks = extract_po_items_module._split_document_into_chunks(document_text, chunk_chars=10000)

    assert len(chunks) == 2
    assert all(len(chunk) <= 10000 for chunk in chunks)


def test_combine_purchase_order_items_deduplicates_items() -> None:
    chunk_results = [
        [
            {
                "name": "Item 1",
                "unit_cost": 10.0,
                "qty_count": 1.0,
                "unit_type": "m2",
                "remarks": "A",
            }
        ],
        [
            {
                "name": "item 1",
                "unit_cost": 10.0,
                "qty_count": 1.0,
                "unit_type": "M2",
                "remarks": "a",
            },
            {
                "name": "Item 2",
                "unit_cost": 20.0,
                "qty_count": 2.0,
                "unit_type": "nos",
                "remarks": "B",
            },
        ],
    ]

    combined = extract_po_items_module._combine_purchase_order_items(chunk_results)

    assert len(combined.items) == 2


def test_extract_po_items_task_handles_single_chunk_inline(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed_payload: dict[str, object] = {}

    monkeypatch.setattr(
        extract_po_items_module,
        "get_task",
        lambda _task_id: type(
            "Task",
            (),
            {"payload": {"blob_link": "doc.pdf", "blob_type": "vercel"}},
        )(),
    )
    monkeypatch.setattr(extract_po_items_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(
        extract_po_items_module,
        "mark_task_completed",
        lambda _task_id, payload: completed_payload.update(payload),
    )
    monkeypatch.setattr(extract_po_items_module, "mark_task_failed", lambda _task_id, _error: None)
    monkeypatch.setattr(extract_po_items_module, "get_bytes", lambda _blob_link: b"Document body")
    monkeypatch.setattr(
        extract_po_items_module, "_extract_text", lambda _link, _data: "Document body"
    )
    monkeypatch.setattr(
        extract_po_items_module,
        "_split_document_into_chunks",
        lambda _text, **_kwargs: ["chunk"],
    )
    monkeypatch.setattr(
        extract_po_items_module,
        "extract_po_items_chunk_task",
        lambda _chunk: [
            {
                "name": "Item 1",
                "unit_cost": 10.0,
                "qty_count": 1.0,
                "unit_type": "m2",
                "remarks": "A",
            }
        ],
    )

    assert extract_po_items_module.extract_po_items_task("task-123") == "Processed 1 chunk"
    assert "items" in completed_payload


class _SignatureStub:
    def __init__(self, name: str, args: list[object]) -> None:
        self.name = name
        self.args = args
        self.errback: object | None = None

    def link_error(self, errback: object) -> None:
        self.errback = errback


def test_extract_po_items_task_fans_out_multiple_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created_signatures: list[_SignatureStub] = []
    captured_chord: dict[str, object] = {}

    def fake_signature(name: str, args: list[object]) -> _SignatureStub:
        signature = _SignatureStub(name=name, args=args)
        created_signatures.append(signature)
        return signature

    def fake_chord(header: list[_SignatureStub]):
        captured_chord["header"] = header

        def _apply(callback: _SignatureStub) -> None:
            captured_chord["callback"] = callback

        return _apply

    monkeypatch.setattr(
        extract_po_items_module,
        "get_task",
        lambda _task_id: type(
            "Task",
            (),
            {"payload": {"blob_link": "doc.pdf", "blob_type": "vercel"}},
        )(),
    )
    monkeypatch.setattr(extract_po_items_module, "mark_task_in_progress", lambda _task_id: None)
    monkeypatch.setattr(extract_po_items_module, "mark_task_failed", lambda _task_id, _error: None)
    monkeypatch.setattr(extract_po_items_module, "get_bytes", lambda _blob_link: b"Document body")
    monkeypatch.setattr(
        extract_po_items_module, "_extract_text", lambda _link, _data: "Document body"
    )
    monkeypatch.setattr(
        extract_po_items_module,
        "_split_document_into_chunks",
        lambda _text, **_kwargs: ["chunk-1", "chunk-2"],
    )
    monkeypatch.setattr(extract_po_items_module.celery_app, "signature", fake_signature)
    monkeypatch.setattr(extract_po_items_module, "chord", fake_chord)

    result = extract_po_items_module.extract_po_items_task("task-123")

    assert result == "Dispatched 2 chunks"
    assert "header" in captured_chord
    assert "callback" in captured_chord
    callback = captured_chord["callback"]
    assert isinstance(callback, _SignatureStub)
    assert callback.errback is not None
