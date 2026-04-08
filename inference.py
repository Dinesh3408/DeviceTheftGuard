"""Inference script for hackathon evaluation.

Usage:
    python inference.py

Environment variables:
    OPENENV_BASE_URL: Environment server URL (default: http://localhost:8000)
    HF_TOKEN: Hugging Face access token (required for router model calls)
    API_BASE_URL: Router base URL (default: https://router.huggingface.co/v1)
    MODEL_NAME: Router model name (default: openai/gpt-4o-mini)
"""

from __future__ import annotations

import json
import os
from typing import Literal

from openai import OpenAI

from client import LaptopSecurityOpenenvEnv
from models import LaptopSecurityOpenenvAction, LaptopSecurityOpenenvObservation

ActionName = Literal["noop", "alert", "lock", "wipe"]


def _fallback_policy(obs: LaptopSecurityOpenenvObservation) -> ActionName:
    if obs.threat and obs.risk_score >= 0.8:
        return "wipe"
    if obs.threat and obs.risk_score >= 0.6:
        return "lock"
    if obs.threat:
        return "alert"
    return "noop"


def _llm_policy(
    obs: LaptopSecurityOpenenvObservation,
    client: OpenAI,
    model: str,
) -> ActionName:
    prompt = (
        "You are selecting one security action for a laptop theft prevention RL environment.\n"
        "Return JSON only: {\"action\": \"noop|alert|lock|wipe\"}.\n"
        f"observation={obs.model_dump_json()}"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    content = resp.choices[0].message.content or "{}"
    try:
        action = json.loads(content).get("action", "noop")
    except Exception:
        action = "noop"
    if action not in {"noop", "alert", "lock", "wipe"}:
        action = "noop"
    return action  # type: ignore[return-value]


def main() -> None:
    env_base_url = os.getenv("OPENENV_BASE_URL", "http://localhost:8000")
    hf_token = os.getenv("HF_TOKEN")
    api_base_url = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    model_name = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")

    llm_client = None
    if hf_token:
        llm_client = OpenAI(
            api_key=hf_token,
            base_url=api_base_url,
        )

    total_reward = 0.0
    steps_executed = 0
    with LaptopSecurityOpenenvEnv(base_url=env_base_url).sync() as env:
        reset_result = env.reset()
        obs = reset_result.observation
        print(f"START threat={obs.threat} risk={obs.risk_score:.2f}")

        for step in range(1, 21):
            steps_executed = step
            action_name = (
                _llm_policy(obs, llm_client, model_name) if llm_client else _fallback_policy(obs)
            )
            result = env.step(LaptopSecurityOpenenvAction(action=action_name))
            obs = result.observation
            step_reward = float(result.reward or 0.0)
            total_reward += step_reward

            print(
                f"STEP step={step} action={action_name} "
                f"threat={obs.threat} risk={obs.risk_score:.2f} "
                f"reward={step_reward:.2f} done={result.done}"
            )
            if result.done:
                break

    print(f"END total_reward={total_reward:.2f} steps={steps_executed}")


if __name__ == "__main__":
    main()
