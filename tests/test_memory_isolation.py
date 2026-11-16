"""私聊长期记忆隔离：不同 QQ 号不能读到彼此的记忆。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bridge import Bridge


def _bare_bridge(memory_path: Path) -> Bridge:
    """只带内存路径的最小 Bridge，够测记忆读写。"""
    bridge = Bridge.__new__(Bridge)
    bridge.memory_path = memory_path
    return bridge


def test_memory_file_is_per_user(tmp_path):
    """每个用户解析到独立的记忆文件。"""
    bridge = _bare_bridge(tmp_path / "memory.md")
    a = bridge._memory_path_for("3197142392")
    b = bridge._memory_path_for("3997107559")
    assert a != b
    assert a.name == "memory-3197142392.md"
    assert b.name == "memory-3997107559.md"
    # 不传用户时退回旧的共享文件
    assert bridge._memory_path_for("") == bridge.memory_path


def test_write_does_not_leak_between_users(tmp_path):
    """A 的记忆写不进 B 的文件。"""
    bridge = _bare_bridge(tmp_path / "memory.md")
    asyncio.run(bridge._write_memory("A 的专属记忆", "3197142392"))

    assert "A 的专属记忆" in bridge._read_memory("3197142392")
    assert "A 的专属记忆" not in bridge._read_memory("3997107559")


def test_falls_back_to_shared_file_when_user_file_missing(tmp_path):
    """用户还没自己的文件时，退回共享 memory.md，不至于丢光记忆。"""
    shared = tmp_path / "memory.md"
    shared.write_text("共享记忆内容", encoding="utf-8")
    bridge = _bare_bridge(shared)
    assert "共享记忆内容" in bridge._read_memory("3997107559")


def test_user_file_takes_precedence_over_shared(tmp_path):
    """有了自己的文件就只读自己的，不再混入共享内容。"""
    shared = tmp_path / "memory.md"
    shared.write_text("共享记忆内容", encoding="utf-8")
    bridge = _bare_bridge(shared)
    user_file = bridge._memory_path_for("3197142392")
    user_file.write_text("我的私有记忆", encoding="utf-8")

    text = bridge._read_memory("3197142392")
    assert "我的私有记忆" in text
    assert "共享记忆内容" not in text
