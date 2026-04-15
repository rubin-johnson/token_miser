"""Quality scoring via Anthropic API (Claude as judge)."""
from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

from token_miser.task import RubricDimension

JUDGE_MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 2000


@dataclass
class DimensionScore:
    dimension: str
    score: float
    reason: str


def score_quality(
    prompt: str,
    output: str,
    dimensions: list[RubricDimension],
    api_key: str | None = None,
) -> list[DimensionScore]:
    """Score Claude's output against quality rubric dimensions.

    Uses a Claude judge to evaluate each dimension on a 0-1 scale.
    """
    if not dimensions:
        return []

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    judge_prompt = _build_judge_prompt(prompt, output, dimensions)

    message = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": judge_prompt}],
    )

    text = message.content[0].text if message.content else ""
    return _parse_scores(text, dimensions)


def _build_judge_prompt(prompt: str, output: str, dimensions: list[RubricDimension]) -> str:
    dim_list = "\n".join(f'- "{d.dimension}": {d.prompt}' for d in dimensions)
    return f"""You are a code quality judge. Evaluate the following output against the given rubric.

TASK PROMPT:
{prompt}

CLAUDE OUTPUT:
{output}

RUBRIC DIMENSIONS:
{dim_list}

Respond with a JSON array. Each element must have:
- "dimension": the dimension name (string)
- "score": a float between 0.0 and 1.0
- "reason": one sentence explaining the score

Example: [{{"dimension": "correctness", "score": 0.85, "reason": "All tests pass but one edge case missed."}}]

Return ONLY the JSON array, no other text."""


def _parse_scores(text: str, dimensions: list[RubricDimension]) -> list[DimensionScore]:
    # Extract JSON from possible markdown code fences
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        cleaned = "\n".join(lines)

    raw = json.loads(cleaned)
    scores = []
    for item in raw:
        score = float(item["score"])
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"Score {score} out of range [0, 1] for dimension {item['dimension']}")
        reason = item.get("reason", "")
        if not reason:
            raise ValueError(f"Empty reason for dimension {item['dimension']}")
        scores.append(DimensionScore(dimension=item["dimension"], score=score, reason=reason))
    return scores
