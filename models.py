# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Data models for the Laptop Security OpenEnv environment."""

from typing import Literal

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


class LaptopSecurityOpenenvAction(Action):
    """Action sent to the laptop security environment."""

    action: Literal["noop", "alert", "lock", "wipe"] = Field(
        ...,
        description="Security action: noop, alert, lock, or wipe",
    )


class LaptopSecurityOpenenvObservation(Observation):
    """Observation returned by the laptop security environment."""

    message: str = Field(default="", description="Human-readable environment message")
    threat: bool = Field(default=False, description="Whether a theft risk is currently detected")
    risk_score: float = Field(default=0.0, description="Risk score from 0 to 1")
    location: str = Field(default="office", description="Current device location context")
    login: str = Field(default="auth", description="Authentication status")
    time: str = Field(default="work", description="Time context")
    movement: str = Field(default="still", description="Device movement state")


class LaptopSecurityOpenenvState(State):
    """Internal state for laptop security episode progression."""

    location: str = Field(default="office", description="Current location")
    login: str = Field(default="auth", description="Authentication status")
    time: str = Field(default="work", description="Time category")
    movement: str = Field(default="still", description="Movement category")
    threat: bool = Field(default=False, description="Latest computed threat")
    risk_score: float = Field(default=0.0, description="Latest computed risk score")
