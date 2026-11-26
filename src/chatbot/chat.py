from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import anthropic
from anthropic.types import MessageParam
from dotenv import load_dotenv

DEFAULT_MODEL = "claude-sonnet-5-5"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Keep answers clear and concise."
DEFAULT_MAX_TURNS = 20
DEFAULT_INPUT_PRICE = Decimal("2")
DEFAULT_OUTPUT_PRICE = Decimal("10")
PRICE_SCALE = Decimal("1000000")
LOG_FIELDS = [
    "timestamp_utc",
    "model",
    "input_tokens",
    "output_tokens",
    "estimated_cost_usd",
]


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: Decimal = DEFAULT_INPUT_PRICE,
    output_price_per_million: Decimal = DEFAULT_OUTPUT_PRICE,
) -> Decimal:
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must not be negative")
    if input_price_per_million < 0 or output_price_per_million < 0:
        raise ValueError("token prices must not be negative")

    return (
        Decimal(input_tokens) * input_price_per_million
        + Decimal(output_tokens) * output_price_per_million
    ) / PRICE_SCALE


def append_cost_log(
    path: str | Path,
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: Decimal = DEFAULT_INPUT_PRICE,
    output_price_per_million: Decimal = DEFAULT_OUTPUT_PRICE,
) -> Decimal:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists() or log_path.stat().st_size == 0
    cost = estimate_cost_usd(
        input_tokens,
        output_tokens,
        input_price_per_million,
        output_price_per_million,
    )

    with log_path.open("a", encoding="utf-8", newline="") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=LOG_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": f"{cost:.10f}",
            }
        )

    return cost


def run_chat_loop(
    client: anthropic.Anthropic,
    *,
    model: str,
    system_prompt: str,
    cost_log_path: str | Path,
    max_turns: int = DEFAULT_MAX_TURNS,
    input_price_per_million: Decimal = DEFAULT_INPUT_PRICE,
    output_price_per_million: Decimal = DEFAULT_OUTPUT_PRICE,
    input_fn: Callable[[str], str] | None = None,
    output_fn: Callable[..., None] = print,
) -> None:
    if max_turns < 1:
        raise ValueError("max_turns must be at least 1")

    read_input = input if input_fn is None else input_fn
    history: list[MessageParam] = []
    turns = 0

    while turns < max_turns:
        try:
            prompt = read_input("You: ").strip()
        except EOFError:
            output_fn()
            break

        if prompt.lower() in {"/exit", "/quit"}:
            break
        if not prompt:
            continue

        history.append({"role": "user", "content": prompt})
        output_fn("Assistant: ", end="", flush=True)
        response_text: list[str] = []

        try:
            with client.messages.stream(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=history,
            ) as stream:
                for text in stream.text_stream:
                    response_text.append(text)
                    output_fn(text, end="", flush=True)
                message = stream.get_final_message()
        except anthropic.APIError:
            history.pop()
            output_fn()
            raise

        output_fn()
        history.append({"role": "assistant", "content": "".join(response_text)})
        cost = append_cost_log(
            cost_log_path,
            model=message.model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
            input_price_per_million=input_price_per_million,
            output_price_per_million=output_price_per_million,
        )
        output_fn(
            f"Tokens: {message.usage.input_tokens} in / "
            f"{message.usage.output_tokens} out | estimated ${cost:.6f}"
        )
        turns += 1


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Stream a Claude chat and log token costs.")
    parser.add_argument("--model", default=os.getenv("ANTHROPIC_MODEL", DEFAULT_MODEL))
    parser.add_argument(
        "--max-turns",
        type=int,
        default=int(os.getenv("CHAT_MAX_TURNS", str(DEFAULT_MAX_TURNS))),
    )
    parser.add_argument(
        "--cost-log",
        default=os.getenv("COST_LOG_PATH", "cost_log.csv"),
    )
    parser.add_argument(
        "--input-price-per-million",
        type=Decimal,
        default=Decimal(os.getenv("INPUT_PRICE_PER_MILLION_USD", "2")),
    )
    parser.add_argument(
        "--output-price-per-million",
        type=Decimal,
        default=Decimal(os.getenv("OUTPUT_PRICE_PER_MILLION_USD", "10")),
    )
    args = parser.parse_args(argv)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "replace-me":
        print("Set ANTHROPIC_API_KEY in .env before starting the chat.", file=sys.stderr)
        return 2
    if args.max_turns < 1:
        parser.error("--max-turns must be at least 1")
    if args.input_price_per_million < 0 or args.output_price_per_million < 0:
        parser.error("token prices must not be negative")

    client = anthropic.Anthropic(api_key=api_key, max_retries=5)
    print("Chat started. Enter /exit to stop.")
    try:
        run_chat_loop(
            client,
            model=args.model,
            system_prompt=os.getenv("CHAT_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            cost_log_path=args.cost_log,
            max_turns=args.max_turns,
            input_price_per_million=args.input_price_per_million,
            output_price_per_million=args.output_price_per_million,
        )
    except anthropic.APIError as exc:
        print(f"Anthropic request failed after retries: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())