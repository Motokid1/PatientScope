from langgraph.runtime import Runtime

from app.observability import stage
from app.rag.state import AuthContext, RAGState


def timed_node(name, node, uses_runtime=False):
    if uses_runtime:

        async def timed_runtime(state: RAGState, runtime: Runtime[AuthContext]):
            with stage(name):
                return await node(state, runtime)

        return timed_runtime

    async def timed(state):
        with stage(name):
            return await node(state)

    return timed
