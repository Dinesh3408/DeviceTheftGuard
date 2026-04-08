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
import math
import os
import sys
import urllib.error
import urllib.request
from typing import Literal

from openai import OpenAI

from client import LaptopSecurityOpenenvEnv
from models import LaptopSecurityOpenenvAction, LaptopSecurityOpenenvObservation

ActionName = Literal["noop", "alert", "lock", "wipe"]
TASK_NAME = "device_theft_guard_openenv"


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
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
    except Exception as exc:
        print(f"LLM call failed, using fallback policy: {exc}", file=sys.stderr)
        return _fallback_policy(obs)

    try:
        action = json.loads(content).get("action", "noop")
    except Exception:
        print("LLM response parse failed, using fallback policy", file=sys.stderr)
        return _fallback_policy(obs)
    if action not in {"noop", "alert", "lock", "wipe"}:
        print(f"LLM returned invalid action '{action}', using fallback policy", file=sys.stderr)
        return _fallback_policy(obs)
    return action  # type: ignore[return-value]


def _warn_if_env_unreachable(env_base_url: str) -> None:
    if "huggingface.co/spaces/" in env_base_url:
        print(
            "OPENENV_BASE_URL points to a Hugging Face page URL. Use the .hf.space runtime URL instead.",
            file=sys.stderr,
        )
        return

    health_url = f"{env_base_url.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=5.0) as response:
            if response.status >= 400:
                print(f"Health check returned HTTP {response.status} at {health_url}", file=sys.stderr)
    except urllib.error.URLError as exc:
        print(f"Health check failed at {health_url}: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"Health check failed at {health_url}: {exc}", file=sys.stderr)


def _score_from_reward(total_reward: float, steps: int) -> float:
    # Map average reward to a bounded score in (0, 1), then clamp for strictness.
    avg_reward = total_reward / max(steps, 1)
    raw = 1.0 / (1.0 + math.exp(-avg_reward / 4.0))
    return max(0.001, min(0.999, raw))


def main() -> None:
    env_base_url = os.getenv("OPENENV_BASE_URL", "http://localhost:8000")
    hf_token = os.getenv("HF_TOKEN")
    api_base_url = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    model_name = os.getenv("MODEL_NAME", "openai/gpt-4o-mini")
    task_count = max(3, int(os.getenv("NUM_TASKS", "3")))

    llm_client = None
    if hf_token:
        llm_client = OpenAI(
            api_key=hf_token,
            base_url=api_base_url,
        )

    task_names = [f"{TASK_NAME}_task_{i}" for i in range(1, task_count + 1)]
    _warn_if_env_unreachable(env_base_url)
    try:
        with LaptopSecurityOpenenvEnv(base_url=env_base_url).sync() as env:
            for task_name in task_names:
                total_reward = 0.0
                steps_executed = 0
                reset_result = env.reset()
                obs = reset_result.observation
                print(
                    f"[START] task={task_name} threat={obs.threat} risk={obs.risk_score:.2f}",
                    flush=True,
                )

                for step in range(1, 21):
                    steps_executed = step
                    action_name = (
                        _llm_policy(obs, llm_client, model_name)
                        if llm_client
                        else _fallback_policy(obs)
                    )
                    result = env.step(LaptopSecurityOpenenvAction(action=action_name))
                    obs = result.observation
                    step_reward = float(result.reward or 0.0)
                    total_reward += step_reward

                    print(
                        f"[STEP] task={task_name} step={step} reward={step_reward:.2f} done={result.done}",
                        flush=True,
                    )
                    if result.done:
                        break

                score = _score_from_reward(total_reward, steps_executed)
                print(
                    f"[END] task={task_name} score={score:.4f} steps={steps_executed} "
                    f"total_reward={total_reward:.2f}",
                    flush=True,
                )

    except Exception as exc:
        # Emit parseable task blocks even on connection/runtime failures.
        print(f"Fatal inference error: {exc}", file=sys.stderr)
        for task_name in task_names:
            print(f"[START] task={task_name}", flush=True)
            print(
                f"[END] task={task_name} score=0.0010 steps=0 total_reward=0.00 status=error",
                flush=True,
            )


if __name__ == "__main__":
    main()
