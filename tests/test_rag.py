import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from rag import RagIndex, _chunk_text, scan_docs, search_knowledge
from state_db import StateDB


def _write_sample(tmp_path):
    (tmp_path / "a.md").write_text("测试助手是统合思念体的外星人，负责观察地球。", encoding="utf-8")
    (tmp_path / "b.txt").write_text("阿布量化交易系统每天输出净值表。", encoding="utf-8")
    return tmp_path


def test_scan_and_search(tmp_path):
    src = _write_sample(tmp_path)
    db = StateDB(tmp_path / "state.db")
    count = asyncio.run(scan_docs([src], db))
    assert count >= 2
    hits = db.search_documents("外星人")
    assert len(hits) >= 1
    assert "a.md" in hits[0]["title"]


def test_rag_index_rebuild(tmp_path):
    src = _write_sample(tmp_path)
    db = StateDB(tmp_path / "state.db")
    index = RagIndex(db)
    count = asyncio.run(index.rebuild([src]))
    assert count >= 2
    assert len(index.query("外星人")) >= 1


def test_search_formatted_text(tmp_path):
    src = _write_sample(tmp_path)
    db = StateDB(tmp_path / "state.db")
    asyncio.run(scan_docs([src], db))
    text = search_knowledge(db, "外星人")
    assert "a.md" in text
    assert "没有找到" not in text


def test_search_knowledge_empty(tmp_path):
    db = StateDB(tmp_path / "state.db")
    text = search_knowledge(db, "不存在的内容")
    assert "没有找到" in text


def test_detailed_knowledge_returns_evidence_beyond_preview(tmp_path):
    db = StateDB(tmp_path / "state.db")
    content = "来源线索：真香。\n\n" + "背景材料。" * 45 + "\n\n传播经过：先拒绝后接受，衍生为态度反转模板。"
    db.add_document("meme.md", 0, "真香详解", content)
    reply = search_knowledge(db, "真香", limit=1)
    assert "传播经过：先拒绝后接受" in reply
    assert db.document_content("not-indexed.md#0") == ""
    db.close()


def test_chunking_keeps_origin_paragraph_whole():
    origin = "出处与传播：" + "不可拆断的因果说明。" * 8
    text = "前言。" * 25 + "\n\n" + origin
    chunks = _chunk_text(text, size=120, overlap=10)
    assert any(origin in chunk for chunk in chunks)
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_long_paragraph_chunking_keeps_tail():
    text = "剧情说明" * 100 + "独有结尾"
    chunks = _chunk_text(text, size=100, overlap=10)
    assert chunks[-1].endswith("独有结尾")
    assert all(len(chunk) <= 100 for chunk in chunks)


def test_local_prefetch_provides_matching_work_but_skips_chitchat(tmp_path):
    from types import SimpleNamespace
    from handlers import _local_knowledge_context

    db = StateDB(tmp_path / "state.db")
    db.add_document("anime.md", 0, "孤独摇滚！.md", "后藤一里加入结束乐队。")
    bridge = SimpleNamespace(cfg={}, state_db=db)
    assert "后藤一里" in _local_knowledge_context(bridge, "孤独摇滚！讲了什么")
    assert _local_knowledge_context(bridge, "我先下班啦") == ""
    bridge.cfg["knowledge_tool_enabled"] = False
    assert _local_knowledge_context(bridge, "孤独摇滚！讲了什么") == ""
    db.close()


def test_agent_client_builds_knowledge_tool(tmp_path):
    from agent_client import AgentClient

    cfg = {
        "api_key": "test-key",
        "api_base_url": "http://127.0.0.1:9/v1",
        "tools_enabled": True,
        "shell_enabled": False,
        "file_tools_enabled": False,
        "web_search_enabled": False,
        "knowledge_tool_enabled": True,
        "state_db_file": str(tmp_path / "state.db"),
    }
    client = AgentClient(cfg)
    tools = client._build_tools()
    assert any(getattr(t, "name", None) == "search_knowledge" for t in tools)
