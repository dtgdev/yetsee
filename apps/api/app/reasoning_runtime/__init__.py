from app.reasoning_runtime.registry import registry
from app.reasoning_runtime.reasoners.graph import GraphReasoner

try:
    registry.register(GraphReasoner())
except ValueError:
    pass

__all__ = ["registry"]
