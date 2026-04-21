"""Compatibility alias: orchestration uses llama-cpp-python via ``OrchestrationAgent``."""

from agents.manager import OrchestrationAgent as LlamaCppOrchestrationAgent

__all__ = ["LlamaCppOrchestrationAgent"]
