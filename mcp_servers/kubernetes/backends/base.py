"""
Abstract RuntimeBackend interface for infrastructure inspection.
Supports Docker backend (Week 2) and Kubernetes backend (Week 3).
"""

from abc import ABC, abstractmethod
from typing import Any


class RuntimeBackend(ABC):
    """Abstract interface defining the infrastructure query contract."""

    @abstractmethod
    def get_pod_status(self, service: str) -> dict[str, Any]:
        """
        Get current container/pod status for a service.
        Matches contracts/mcp_tools.md.
        """

    @abstractmethod
    def get_events(self, service: str, minutes: int = 15) -> dict[str, Any]:
        """
        Get recent lifecycle events for a service container/pod.
        Matches contracts/mcp_tools.md.
        """

    @abstractmethod
    def get_logs(
        self,
        service: str,
        minutes: int = 10,
        level: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Get structured JSON log lines for a service within time window.
        Matches proposed get_logs contract.
        """

    @abstractmethod
    def list_services(self) -> dict[str, Any]:
        """
        List all registered services and their current runtime state.
        Matches proposed list_services contract.
        """
