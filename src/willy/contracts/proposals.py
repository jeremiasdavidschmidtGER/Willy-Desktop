"""Behaviour proposals: defined now; produced from Gate B on. Any future LLM
output must be reduced to a BehaviourProposal before entering the pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class BehaviourProposal:
    behaviour_id: str
    animation_id: str | None
    dialogue_intent: str | None
    audio_id: str | None
    state_changes: Mapping[str, int]  # e.g. {"irritation": 2}


class ProposalValidator(Protocol):
    def validate(self, proposal: BehaviourProposal) -> BehaviourProposal | None:
        """Return possibly-adjusted proposal, or None to reject."""
        ...
