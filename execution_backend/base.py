"""ExecutionBackend interface.

V1 ships LocalExecutor only. DockerExecutor/VMExecutor/CauslyExecutor are
future work — same interface, stronger isolation.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import ExecutionRequest, ExecutionResult


class ExecutionBackend(ABC):
    """Runs analytical code and returns a structured ExecutionResult."""

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Run request.code and return its result, error, or timeout/limit outcome."""
        raise NotImplementedError
