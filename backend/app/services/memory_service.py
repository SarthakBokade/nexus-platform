"""
Conversation Memory Service
Manages multi-turn chat sessions with a sliding context window.
Stores each turn (user + assistant) as ConversationMessage rows and
builds a truncated history string that fits within LLM context limits.
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from backend.app.db.models import ConversationSession, ConversationMessage, generate_uuid, utc_now

logger = logging.getLogger("nexus.services.memory")

MAX_HISTORY_TURNS = 6       # Keep last N turns in context (1 turn = user+assistant)
MAX_HISTORY_CHARS = 4000    # Hard cap on history string length


class ConversationMemoryService:
    """
    Manages per-session multi-turn conversation history.

    Design choices:
    - Sliding window (last N turns) keeps token usage bounded.
    - Full history is always persisted to DB for audit/recall.
    - Sessions are auto-titled from the first user message.
    """

    # ------------------------------------------------------------------ #
    # Session Management                                                   #
    # ------------------------------------------------------------------ #

    async def create_session(
        self,
        db: AsyncSession,
        user_id: str,
        title: Optional[str] = None
    ) -> ConversationSession:
        session = ConversationSession(
            id=generate_uuid(),
            user_id=user_id,
            title=title or "New Conversation",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        logger.info(f"Created session {session.id} for user {user_id}")
        return session

    async def get_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str
    ) -> Optional[ConversationSession]:
        res = await db.execute(
            select(ConversationSession).where(
                ConversationSession.id == session_id,
                ConversationSession.user_id == user_id
            )
        )
        return res.scalars().first()

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20
    ) -> List[ConversationSession]:
        res = await db.execute(
            select(ConversationSession)
            .where(ConversationSession.user_id == user_id)
            .order_by(ConversationSession.updated_at.desc())
            .limit(limit)
        )
        return list(res.scalars().all())

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: str,
        user_id: str
    ) -> bool:
        session = await self.get_session(db, session_id, user_id)
        if not session:
            return False
        await db.delete(session)
        await db.commit()
        return True

    # ------------------------------------------------------------------ #
    # Message Persistence                                                  #
    # ------------------------------------------------------------------ #

    async def add_user_message(
        self,
        db: AsyncSession,
        session_id: str,
        content: str,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(msg)
        # Auto-title session from first user message
        await db.execute(
            update(ConversationSession)
            .where(
                ConversationSession.id == session_id,
                ConversationSession.title == "New Conversation"
            )
            .values(title=content[:80] + ("…" if len(content) > 80 else ""))
        )
        await db.commit()
        return msg

    async def add_assistant_message(
        self,
        db: AsyncSession,
        session_id: str,
        content: str,
        intent_classified: Optional[str] = None,
        grounding_score: Optional[float] = None,
        citations: Optional[List[Dict]] = None,
        agent_trace: Optional[List[Dict]] = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> ConversationMessage:
        msg = ConversationMessage(
            session_id=session_id,
            role="assistant",
            content=content,
            intent_classified=intent_classified,
            grounding_score=grounding_score,
            citations_json=citations or [],
            agent_trace_json=agent_trace or [],
            tokens_used=tokens_used,
            latency_ms=latency_ms,
        )
        db.add(msg)

        # Increment turn counter on session
        await db.execute(
            update(ConversationSession)
            .where(ConversationSession.id == session_id)
            .values(
                turn_count=ConversationSession.turn_count + 1,
                updated_at=utc_now()
            )
        )
        await db.commit()
        return msg

    async def get_messages(
        self,
        db: AsyncSession,
        session_id: str,
        limit: int = 50
    ) -> List[ConversationMessage]:
        res = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.session_id == session_id)
            .order_by(ConversationMessage.created_at.asc())
            .limit(limit)
        )
        return list(res.scalars().all())

    # ------------------------------------------------------------------ #
    # Context Window Builder                                               #
    # ------------------------------------------------------------------ #

    async def build_context_window(
        self,
        db: AsyncSession,
        session_id: str,
        current_query: str
    ) -> str:
        """
        Constructs a formatted conversation history string for injection into the LLM prompt.
        Uses a sliding window of the last MAX_HISTORY_TURNS turns, capped at MAX_HISTORY_CHARS.

        Returns: A formatted string like:
            [Turn 1] User: ...
            [Turn 1] Assistant: ...
            [Turn 2] User: ...
        """
        messages = await self.get_messages(db, session_id)
        if not messages:
            return ""

        # Take last N*2 messages (user+assistant pairs)
        window = messages[-(MAX_HISTORY_TURNS * 2):]

        lines = []
        turn = 1
        for i in range(0, len(window), 2):
            user_msg = window[i] if i < len(window) else None
            asst_msg = window[i + 1] if i + 1 < len(window) else None

            if user_msg:
                lines.append(f"[Turn {turn}] User: {user_msg.content}")
            if asst_msg:
                # Truncate very long assistant responses in history
                asst_content = asst_msg.content[:600] + "…" if len(asst_msg.content) > 600 else asst_msg.content
                lines.append(f"[Turn {turn}] Assistant: {asst_content}")
            turn += 1

        history_str = "\n".join(lines)

        # Hard character cap
        if len(history_str) > MAX_HISTORY_CHARS:
            history_str = "…[earlier context truncated]…\n" + history_str[-MAX_HISTORY_CHARS:]

        return history_str
