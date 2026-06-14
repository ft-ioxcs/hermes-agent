import pytest

from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.platforms.base import MessageEvent, MessageType
from gateway.run import GatewayRunner
from gateway.session import SessionSource
from hermes_cli import goals


class _FakeEntry:
    session_id = "sid-gateway-moa-goal"


class _Adapter:
    def __init__(self):
        self.queued = []


@pytest.mark.asyncio
async def test_goal_continuation_inherits_active_moa_preset(tmp_path, monkeypatch):
    home = tmp_path / ".hermes"
    home.mkdir()
    (home / "config.yaml").write_text(
        """
moa:
  default_preset: default
  presets:
    default: {}
    review:
      reference_models:
        - provider: openai-codex
          model: gpt-5.5
      aggregator:
        provider: openrouter
        model: anthropic/claude-opus-4.8
goals:
  max_turns: 5
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("HERMES_HOME", str(home))
    goals._DB_CACHE.clear()

    runner = object.__new__(GatewayRunner)
    runner.config = GatewayConfig(
        platforms={Platform.DISCORD: PlatformConfig(enabled=True, token="token")}
    )
    runner.adapters = {Platform.DISCORD: _Adapter()}
    runner._moa_active_presets = {"agent:main:discord:channel:chat": "review"}

    def session_key_for_source(_source):
        return "agent:main:discord:channel:chat"

    def enqueue_fifo(_quick_key, event, adapter):
        adapter.queued.append((_quick_key, event))

    async def defer_notice(*_args, **_kwargs):
        return None

    runner._session_key_for_source = session_key_for_source
    runner._enqueue_fifo = enqueue_fifo
    runner._goal_max_turns_from_config = lambda: 5
    runner._defer_goal_status_notice_after_delivery = defer_notice

    source = SessionSource(
        platform=Platform.DISCORD,
        chat_id="chat",
        chat_type="channel",
        user_id="user",
    )

    mgr = goals.GoalManager("sid-gateway-moa-goal", default_max_turns=5)
    mgr.set("keep working")
    monkeypatch.setattr(
        goals.GoalManager,
        "evaluate_after_turn",
        lambda self, response, user_initiated=True: {
            "should_continue": True,
            "continuation_prompt": "continue goal",
            "message": "still working",
        },
    )

    try:
        await GatewayRunner._post_turn_goal_continuation(
            runner,
            session_entry=_FakeEntry(),
            source=source,
            final_response="not done yet",
        )
        assert runner.adapters[Platform.DISCORD].queued
        _key, event = runner.adapters[Platform.DISCORD].queued[0]
        assert event.text == "continue goal"
        assert event._moa_config["reference_models"] == [
            {"provider": "openai-codex", "model": "gpt-5.5"}
        ]
    finally:
        goals._DB_CACHE.clear()
