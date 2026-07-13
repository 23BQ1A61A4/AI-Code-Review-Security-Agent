"""
Base agent interface — Module 2.

Every independent agent in the pipeline (Code Analysis now; Security
Vulnerability, Remediation, PR Summary in later modules) implements this
same shape so a future orchestrator can call them uniformly. This base
class only standardizes the interface — it does NOT combine their logic.
Each agent still lives in its own file, with its own class, its own prompt
(if it uses one), and is invoked independently.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute this agent's analysis and return its own result type."""
        raise NotImplementedError
