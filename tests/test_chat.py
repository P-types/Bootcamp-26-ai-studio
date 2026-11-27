import csv
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from chatbot.chat import append_cost_log, estimate_cost_usd, run_chat_loop


class FakeStream:
    def __init__(self, response: SimpleNamespace) -> None:
        self.text_stream = iter(response.text_chunks)
        self.response = response

    def __enter__(self) -> "FakeStream":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def get_final_message(self) -> SimpleNamespace:
        return self.response.message


class FakeMessages:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.responses = [
            SimpleNamespace(
                text_chunks=["Hello", " there."],
                message=SimpleNamespace(
                    model="claude-sonnet-5-5",
                    usage=SimpleNamespace(input_tokens=5, output_tokens=3),
                ),
            ),
            SimpleNamespace(
                text_chunks=["How can I help?"],
                message=SimpleNamespace(
                    model="claude-sonnet-5-5",
                    usage=SimpleNamespace(input_tokens=12, output_tokens=5),
                ),
            ),
        ]

    def stream(self, **kwargs: object) -> FakeStream:
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return FakeStream(self.responses[len(self.calls) - 1])


class FakeClient:
    def __init__(self) -> None:
        self.messages = FakeMessages()


def test_estimate_cost_usd() -> None:
    cost = estimate_cost_usd(1_000_000, 1_000_000)

    assert cost == Decimal("12")


def test_append_cost_log_writes_header_and_cost(tmp_path: Path) -> None:
    path = tmp_path / "cost_log.csv"

    cost = append_cost_log(
        path,
        model="claude-sonnet-5-5",
        input_tokens=100,
        output_tokens=20,
    )

    with path.open(encoding="utf-8", newline="") as log_file:
        rows = list(csv.DictReader(log_file))

    assert cost == Decimal("0.0004")
    assert len(rows) == 1
    assert rows[0]["model"] == "claude-sonnet-5-5"
    assert rows[0]["input_tokens"] == "100"
    assert rows[0]["output_tokens"] == "20"
    assert Decimal(rows[0]["estimated_cost_usd"]) == cost
    assert rows[0]["timestamp_utc"]


def test_chat_streams_and_sends_conversation_history(tmp_path: Path) -> None:
    client = FakeClient()
    prompts = iter(["Hi", "Continue", "/exit"])
    output: list[str] = []

    run_chat_loop(
        client,  # type: ignore[arg-type]
        model="claude-sonnet-5-5",
        system_prompt="Be helpful.",
        cost_log_path=tmp_path / "cost_log.csv",
        max_turns=3,
        input_fn=lambda _: next(prompts),
        output_fn=lambda text="", **_: output.append(str(text)),
    )

    assert output.count("Assistant: ") == 2
    assert "Hello" in output
    assert " there." in output
    assert len(client.messages.calls) == 2
    second_history = client.messages.calls[1]["messages"]
    assert second_history == [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello there."},
        {"role": "user", "content": "Continue"},
    ]

    with (tmp_path / "cost_log.csv").open(encoding="utf-8", newline="") as log_file:
        rows = list(csv.DictReader(log_file))
    assert len(rows) == 2


def test_chat_stops_at_max_turns(tmp_path: Path) -> None:
    client = FakeClient()
    prompts = iter(["First", "This must not be sent"])

    run_chat_loop(
        client,  # type: ignore[arg-type]
        model="claude-sonnet-5-5",
        system_prompt="Be helpful.",
        cost_log_path=tmp_path / "cost_log.csv",
        max_turns=1,
        input_fn=lambda _: next(prompts),
        output_fn=lambda *_args, **_kwargs: None,
    )

    assert len(client.messages.calls) == 1