# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Laptop Security Openenv Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import (
        LaptopSecurityOpenenvAction,
        LaptopSecurityOpenenvObservation,
        LaptopSecurityOpenenvState,
    )
except ImportError:
    from models import (  # type: ignore
        LaptopSecurityOpenenvAction,
        LaptopSecurityOpenenvObservation,
        LaptopSecurityOpenenvState,
    )


class LaptopSecurityOpenenvEnv(
    EnvClient[LaptopSecurityOpenenvAction, LaptopSecurityOpenenvObservation, LaptopSecurityOpenenvState]
):
    """
    Client for the Laptop Security Openenv Environment.

    This client maintains a persistent WebSocket connection to the environment server,
    enabling efficient multi-step interactions with lower latency.
    Each client instance has its own dedicated environment session on the server.

    Example:
        >>> # Connect to a running server
        >>> with LaptopSecurityOpenenvEnv(base_url="http://localhost:8000") as client:
        ...     result = client.reset()
        ...     print(result.observation.echoed_message)
        ...
        ...     result = client.step(LaptopSecurityOpenenvAction(message="Hello!"))
        ...     print(result.observation.echoed_message)

    Example with Docker:
        >>> # Automatically start container and connect
        >>> client = LaptopSecurityOpenenvEnv.from_docker_image("laptop_security_openenv-env:latest")
        >>> try:
        ...     result = client.reset()
        ...     result = client.step(LaptopSecurityOpenenvAction(message="Test"))
        ... finally:
        ...     client.close()
    """

    def _step_payload(self, action: LaptopSecurityOpenenvAction) -> Dict:
        """
        Convert LaptopSecurityOpenenvAction to JSON payload for step message.

        Args:
            action: LaptopSecurityOpenenvAction instance

        Returns:
            Dictionary representation suitable for JSON encoding
        """
        return {"action": action.action}

    def _parse_result(self, payload: Dict) -> StepResult[LaptopSecurityOpenenvObservation]:
        """
        Parse server response into StepResult[LaptopSecurityOpenenvObservation].

        Args:
            payload: JSON response data from server

        Returns:
            StepResult with LaptopSecurityOpenenvObservation
        """
        obs_data = payload.get("observation", {})
        observation = LaptopSecurityOpenenvObservation(
            message=obs_data.get("message", ""),
            threat=obs_data.get("threat", False),
            risk_score=obs_data.get("risk_score", 0.0),
            location=obs_data.get("location", "office"),
            login=obs_data.get("login", "auth"),
            time=obs_data.get("time", "work"),
            movement=obs_data.get("movement", "still"),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> LaptopSecurityOpenenvState:
        """
        Parse server response into State object.

        Args:
            payload: JSON response from state request

        Returns:
            State object with episode_id and step_count
        """
        return LaptopSecurityOpenenvState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            location=payload.get("location", "office"),
            login=payload.get("login", "auth"),
            time=payload.get("time", "work"),
            movement=payload.get("movement", "still"),
            threat=payload.get("threat", False),
            risk_score=payload.get("risk_score", 0.0),
        )
