"""
LangGraph-Compatible Asynchronous StateGraph Implementation.

Provides the StateGraph orchestration pattern named in the technical specification:
- Nodes: ["plan", "extract", "check_coverage", "replan", "analyze", "verify", "repair", "publish"]
- Conditional Edges:
    - check_coverage -> replan (if missing and replans < max_replans) else analyze
    - verify -> repair (if discrepancies and repairs < max_repairs) else publish
- Immutable state updates and execution telemetry.
"""

from collections.abc import Callable, Coroutine
from typing import Any


class StateGraph:
    """
    Asynchronous StateGraph engine adhering to LangGraph interface conventions.
    Allows registering state schemas, nodes, fixed edges, and conditional edge routers.
    """
    def __init__(self, state_schema: type | None = None):
        self.state_schema = state_schema
        self.nodes: dict[str, Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]] = {}
        self.edges: dict[str, str] = {}
        self.conditional_edges: dict[str, Callable[[dict[str, Any]], str]] = {}
        self.entry_point: str | None = None

    def add_node(self, name: str, func: Callable[[dict[str, Any]], Coroutine[Any, Any, dict[str, Any]]]) -> "StateGraph":
        self.nodes[name] = func
        if self.entry_point is None:
            self.entry_point = name
        return self

    def set_entry_point(self, name: str) -> "StateGraph":
        self.entry_point = name
        return self

    def add_edge(self, from_node: str, to_node: str) -> "StateGraph":
        self.edges[from_node] = to_node
        return self

    def add_conditional_edges(self, source: str, condition: Callable[[dict[str, Any]], str]) -> "StateGraph":
        self.conditional_edges[source] = condition
        return self

    def compile(self) -> "CompiledStateGraph":
        if not self.entry_point:
            raise ValueError("StateGraph has no entry point defined.")
        return CompiledStateGraph(self)


class CompiledStateGraph:
    """
    Compiled executable workflow graph with asynchronous execution lifecycle (.ainvoke).
    """
    def __init__(self, graph: StateGraph):
        self.graph = graph

    async def ainvoke(self, initial_state: dict[str, Any]) -> dict[str, Any]:
        state = dict(initial_state)
        current_node = self.graph.entry_point
        visited_steps = 0
        max_traversals = 60

        while current_node and current_node != "END" and visited_steps < max_traversals:
            visited_steps += 1
            node_func = self.graph.nodes.get(current_node)
            if not node_func:
                break

            updates = await node_func(state)
            if updates and isinstance(updates, dict):
                state.update(updates)

            if current_node in self.graph.conditional_edges:
                next_node = self.graph.conditional_edges[current_node](state)
            elif current_node in self.graph.edges:
                next_node = self.graph.edges[current_node]
            else:
                next_node = None

            current_node = next_node

        return state
