# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Laptop Security OpenEnv environment implementation."""

import random
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..models import (
        LaptopSecurityOpenenvAction,
        LaptopSecurityOpenenvObservation,
        LaptopSecurityOpenenvState,
    )
except ImportError:
    from models import (
        LaptopSecurityOpenenvAction,
        LaptopSecurityOpenenvObservation,
        LaptopSecurityOpenenvState,
    )


class LaptopSecurityOpenenvEnvironment(Environment):
    """Laptop theft detection environment with risk-aware rewards."""

    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, max_steps: int = 12):
        self._max_steps = max_steps
        self._state = LaptopSecurityOpenenvState(episode_id=str(uuid4()), step_count=0)

    def _sample_context(self) -> LaptopSecurityOpenenvState:
        return LaptopSecurityOpenenvState(
            episode_id=str(uuid4()),
            step_count=0,
            location=random.choice(["office", "home", "unknown"]),
            login=random.choice(["auth", "unauth"]),
            time=random.choice(["work", "off"]),
            movement=random.choice(["still", "moving"]),
        )

    def _risk_score(self) -> float:
        score = 0.0
        if self._state.location == "unknown":
            score += 0.45
        if self._state.login == "unauth":
            score += 0.35
        if self._state.time == "off":
            score += 0.10
        if self._state.movement == "moving":
            score += 0.10
        return min(score, 1.0)

    def _compute_threat(self) -> bool:
        return (
            self._state.location == "unknown"
            or self._state.login == "unauth"
            or (self._state.time == "off" and self._state.movement == "moving")
        )

    def _obs(self, message: str, reward: float = 0.0, done: bool = False) -> LaptopSecurityOpenenvObservation:
        self._state.risk_score = self._risk_score()
        self._state.threat = self._compute_threat()
        return LaptopSecurityOpenenvObservation(
            message=message,
            threat=self._state.threat,
            risk_score=self._state.risk_score,
            location=self._state.location,
            login=self._state.login,
            time=self._state.time,
            movement=self._state.movement,
            reward=reward,
            done=done,
            metadata={"step": self._state.step_count},
        )

    def reset(self) -> LaptopSecurityOpenenvObservation:
        self._state = self._sample_context()
        return self._obs("Environment reset", reward=0.0, done=False)

    def step(self, action: LaptopSecurityOpenenvAction) -> LaptopSecurityOpenenvObservation:  # type: ignore[override]
        self._state.step_count += 1

        if action.action == "noop":
            self._state.movement = random.choice(["still", "moving"])
        elif action.action == "alert":
            self._state.login = "auth"
        elif action.action == "lock":
            self._state.login = "auth"
            self._state.movement = "still"
        elif action.action == "wipe":
            self._state.location = "office"
            self._state.login = "auth"
            self._state.time = "work"
            self._state.movement = "still"

        threat = self._compute_threat()
        if threat:
            reward_map = {"noop": -15.0, "alert": 8.0, "lock": 12.0, "wipe": 5.0}
        else:
            reward_map = {"noop": 6.0, "alert": -2.0, "lock": -4.0, "wipe": -12.0}

        reward = reward_map[action.action]
        done = (not threat and action.action in {"alert", "lock"}) or self._state.step_count >= self._max_steps
        return self._obs(f"action={action.action}, threat={threat}", reward=reward, done=done)

    @property
    def state(self) -> LaptopSecurityOpenenvState:
        return self._state
