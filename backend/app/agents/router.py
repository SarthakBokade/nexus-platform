import time
import logging
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.rbac import User
from backend.app.agents.state_graph import DocumentIntelligenceGraph, AgentState

logger = logging.getLogger("nexus.agents.router")
doc_graph = DocumentIntelligenceGraph()


class AgentRouter:
    """
    Stateful Router & Task Orchestrator.
    Classifies user intent, constructs execution traces, delegates to specialized agents/tools,
    and runs post-generation claim verification using DocumentIntelligenceGraph.
    """

    def classify_intent(self, query: str) -> str:
        state = AgentState(
            query=query,
            user_role="Admin",
            allowed_access_levels=["Public", "Internal"]
        )
        return doc_graph.classify_intent_node(state).intent

    async def execute_agent_workflow(
        self,
        db: AsyncSession,
        user: User,
        query: str
    ) -> Dict[str, Any]:
        return await doc_graph.run(db, user, query)
