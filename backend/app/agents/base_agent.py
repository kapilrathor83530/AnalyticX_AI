"""Base Specialized Agent Class for Analyticx AI Agentic System."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import time


class BaseSpecializedAgent(ABC):
    """Abstract base class for all 8 specialized agents."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __repr__(self) -> str:
        return f"<{self.name}: {self.description}>"
