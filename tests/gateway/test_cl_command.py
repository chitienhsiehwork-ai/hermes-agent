from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from gateway.config import Platform
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionEntry, SessionSource, build_session_key


def _make_event(text="/cl"):
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="12345", chat_type="dm")
    return MessageEvent(text=text, message_type=MessageType.TEXT, source=source)


def _make_runner(entry):
    runner = object.__new__(GatewayRunner)
    runner.config = SimpleNamespace(group_sessions_per_user=True, thread_sessions_per_user=False)
    runner._running_agents = {}
    runner.session_store = MagicMock()
    runner.session_store._generate_session_key.side_effect = lambda source: build_session_key(
        source,
        group_sessions_per_user=True,
        thread_sessions_per_user=False,
    )
    runner.session_store.get_or_create_session.return_value = entry
    runner.session_store.load_transcript.return_value = []
    return runner


@pytest.mark.asyncio
async def test_cl_command_reports_api_usage_from_session_store():
    """/cl should show API-reported input/output/cache tokens, not empty state."""
    source = SessionSource(platform=Platform.TELEGRAM, chat_id="12345", chat_type="dm")
    key = build_session_key(source, group_sessions_per_user=True, thread_sessions_per_user=False)
    entry = SessionEntry(
        session_key=key,
        session_id="s1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        input_tokens=12000,
        output_tokens=800,
        total_tokens=12800,
        cache_read_tokens=9000,
        cache_write_tokens=2000,
        last_prompt_tokens=12000,
    )
    runner = _make_runner(entry)

    result = await runner._handle_cl_command(_make_event("/cl"))

    assert "12,000 prompt tokens" in result
    assert "input 12,000 · output 800 · total 12,800" in result
    assert "cache read 9,000 · write 2,000" in result
    assert "no context data yet" not in result
