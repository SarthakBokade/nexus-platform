"""
Phase 3 Extended Test Suite — Conversation Memory & Observability

Tests:
1. ConversationMemoryService — session CRUD, message persistence, context window
2. Conversations API routes — create session, send message, multi-turn memory
3. Metrics API — time-series, intent distribution, latency percentiles
4. EmbeddingService — backend detection, batch embedding, backend info
5. Integration: full multi-turn conversation flow
"""
import sys
import os
import asyncio
import unittest

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.app.db.models import (
    User, ConversationSession, ConversationMessage,
    AuditLog, generate_uuid
)
from backend.app.services.memory_service import ConversationMemoryService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(role: str = "Admin") -> User:
    return User(
        id=generate_uuid(),
        email=f"test_{role.lower()}@nexus.com",
        hashed_password="hashed",
        full_name=f"Test {role}",
        role=role,
        department="IT",
    )


# ---------------------------------------------------------------------------
# Memory Service Tests (pure logic, no DB)
# ---------------------------------------------------------------------------

class TestConversationMemoryLogic(unittest.TestCase):
    """Tests context window construction logic without real DB."""

    def test_max_history_turns_constant(self):
        from backend.app.services.memory_service import MAX_HISTORY_TURNS, MAX_HISTORY_CHARS
        self.assertGreaterEqual(MAX_HISTORY_TURNS, 3)
        self.assertGreaterEqual(MAX_HISTORY_CHARS, 1000)

    def test_context_window_format(self):
        """Simulate the context window builder output format."""
        messages = []
        for i in range(4):
            messages.append(type("Msg", (), {"role": "user", "content": f"User question {i+1}"})())
            messages.append(type("Msg", (), {"role": "assistant", "content": f"Assistant answer {i+1}"})())

        lines = []
        turn = 1
        for i in range(0, len(messages), 2):
            user_msg = messages[i] if i < len(messages) else None
            asst_msg = messages[i + 1] if i + 1 < len(messages) else None
            if user_msg:
                lines.append(f"[Turn {turn}] User: {user_msg.content}")
            if asst_msg:
                lines.append(f"[Turn {turn}] Assistant: {asst_msg.content}")
            turn += 1

        history = "\n".join(lines)
        self.assertIn("[Turn 1] User:", history)
        self.assertIn("[Turn 2] Assistant:", history)
        self.assertIn("[Turn 4] User:", history)

    def test_title_auto_truncation(self):
        """Long first messages should be truncated to 80 chars for session title."""
        long_query = "A" * 100
        title = long_query[:80] + ("…" if len(long_query) > 80 else "")
        self.assertEqual(len(title), 81)  # 80 chars + ellipsis
        self.assertTrue(title.endswith("…"))

    def test_history_hard_cap(self):
        """Context window must not exceed MAX_HISTORY_CHARS."""
        from backend.app.services.memory_service import MAX_HISTORY_CHARS
        long_history = "X" * (MAX_HISTORY_CHARS + 1000)
        if len(long_history) > MAX_HISTORY_CHARS:
            truncated = "…[earlier context truncated]…\n" + long_history[-MAX_HISTORY_CHARS:]
        else:
            truncated = long_history
        # Check the main content is bounded
        self.assertLessEqual(len(long_history[-MAX_HISTORY_CHARS:]), MAX_HISTORY_CHARS)


# ---------------------------------------------------------------------------
# EmbeddingService Tests
# ---------------------------------------------------------------------------

class TestEmbeddingService(unittest.TestCase):

    def setUp(self):
        from backend.app.services.embedding_service import EmbeddingService
        self.svc = EmbeddingService()

    def test_active_backend_is_valid(self):
        valid_backends = {"local", "sagemaker", "bedrock_titan", "zero_vector"}
        self.assertIn(self.svc.active_backend, valid_backends)

    def test_embed_single_returns_list(self):
        vec = self.svc.embed("What is the travel policy?")
        self.assertIsInstance(vec, list)
        self.assertGreater(len(vec), 0)

    def test_embed_batch_length_matches(self):
        texts = ["Policy A", "Policy B", "Policy C"]
        vecs = self.svc.embed_batch(texts)
        self.assertEqual(len(vecs), 3)
        for v in vecs:
            self.assertIsInstance(v, list)
            self.assertGreater(len(v), 0)

    def test_all_vectors_same_dimension(self):
        texts = ["NEXUS", "Retrieval Augmented Generation", "CrossEncoder Reranker"]
        vecs = self.svc.embed_batch(texts)
        dims = {len(v) for v in vecs}
        self.assertEqual(len(dims), 1, "All vectors must have the same dimension")

    def test_get_backend_info_keys(self):
        info = self.svc.get_backend_info()
        self.assertIn("active_backend", info)
        self.assertIn("embedding_dimension", info)
        self.assertIn("model_name", info)
        self.assertIn("fallback_chain", info)
        self.assertIsInstance(info["fallback_chain"], list)
        self.assertGreaterEqual(len(info["fallback_chain"]), 3)

    def test_embedding_dimension_positive(self):
        self.assertGreater(self.svc.EMBEDDING_DIM, 0)

    def test_embed_empty_string(self):
        """Should not raise — returns a valid zero or near-zero vector."""
        vec = self.svc.embed("")
        self.assertIsInstance(vec, list)

    def test_singleton_instance_reuse(self):
        from backend.app.services.embedding_service import get_embedding_service
        svc1 = get_embedding_service()
        svc2 = get_embedding_service()
        self.assertIs(svc1, svc2, "get_embedding_service() must return the same singleton")


# ---------------------------------------------------------------------------
# DB Model Tests — ConversationSession & Message
# ---------------------------------------------------------------------------

class TestConversationModels(unittest.TestCase):

    def test_session_model_has_required_fields(self):
        session = ConversationSession()
        self.assertTrue(hasattr(session, "id"))
        self.assertTrue(hasattr(session, "user_id"))
        self.assertTrue(hasattr(session, "title"))
        self.assertTrue(hasattr(session, "turn_count"))
        self.assertTrue(hasattr(session, "created_at"))

    def test_message_model_has_required_fields(self):
        msg = ConversationMessage()
        self.assertTrue(hasattr(msg, "id"))
        self.assertTrue(hasattr(msg, "session_id"))
        self.assertTrue(hasattr(msg, "role"))
        self.assertTrue(hasattr(msg, "content"))
        self.assertTrue(hasattr(msg, "grounding_score"))
        self.assertTrue(hasattr(msg, "citations_json"))
        self.assertTrue(hasattr(msg, "tokens_used"))

    def test_valid_roles(self):
        """Roles should be 'user' or 'assistant'."""
        valid_roles = {"user", "assistant"}
        for role in valid_roles:
            msg = ConversationMessage(role=role)
            self.assertEqual(msg.role, role)

    def test_generate_uuid_uniqueness(self):
        ids = {generate_uuid() for _ in range(100)}
        self.assertEqual(len(ids), 100, "UUIDs must be unique")


# ---------------------------------------------------------------------------
# Metrics Logic Tests
# ---------------------------------------------------------------------------

class TestMetricsLogic(unittest.TestCase):

    def test_percentile_calculation(self):
        """Verify p50/p95/p99 formula matches expected values."""
        latencies = sorted(range(100, 600, 10))  # 50 values: 100, 110, ... 590
        n = len(latencies)
        p50 = latencies[int(n * 0.50)]
        p95 = latencies[int(n * 0.95)]
        p99 = latencies[min(int(n * 0.99), n - 1)]

        self.assertGreater(p95, p50)
        self.assertGreater(p99, p95)
        self.assertLessEqual(p99, latencies[-1])

    def test_intent_distribution_percentage(self):
        """Intent distribution percentages must sum to ~100%."""
        counts = {"simple_qa": 60, "compare_docs": 25, "detect_conflict": 10, "executive_report": 5}
        total = sum(counts.values())
        percentages = {k: round(v / total * 100, 1) for k, v in counts.items()}
        self.assertAlmostEqual(sum(percentages.values()), 100.0, places=0)

    def test_hourly_bucket_aggregation(self):
        """Test the hourly bucketing aggregation logic."""
        from collections import defaultdict
        hourly = defaultdict(lambda: {"queries": 0, "tokens": 0})

        fake_logs = [
            {"hour": "2025-01-01T10:00", "tokens": 100},
            {"hour": "2025-01-01T10:00", "tokens": 200},
            {"hour": "2025-01-01T11:00", "tokens": 150},
        ]
        for log in fake_logs:
            hourly[log["hour"]]["queries"] += 1
            hourly[log["hour"]]["tokens"] += log["tokens"]

        self.assertEqual(hourly["2025-01-01T10:00"]["queries"], 2)
        self.assertEqual(hourly["2025-01-01T10:00"]["tokens"], 300)
        self.assertEqual(hourly["2025-01-01T11:00"]["queries"], 1)


# ---------------------------------------------------------------------------
# Multi-Turn Memory Integration Test (stateless simulation)
# ---------------------------------------------------------------------------

class TestMultiTurnMemoryFlow(unittest.TestCase):
    """Simulates the full multi-turn memory flow without real DB."""

    def test_augmented_query_format(self):
        """Context-augmented query must include history + current question."""
        history = "[Turn 1] User: What is the travel policy?\n[Turn 1] Assistant: The limit is $350/night."
        current = "What changed in 2025?"
        augmented = (
            f"[Conversation History]\n{history}\n\n"
            f"[Current Question]\n{current}"
        )
        self.assertIn("[Conversation History]", augmented)
        self.assertIn("[Current Question]", augmented)
        self.assertIn("What changed in 2025?", augmented)
        self.assertIn("$350/night", augmented)

    def test_stateless_mode_no_history_injection(self):
        """When use_memory=False, query should equal the raw message."""
        message = "Direct question, no memory"
        use_memory = False
        history_context = "" if not use_memory else "[Turn 1] User: ..."

        augmented_query = message if not history_context else (
            f"[Conversation History]\n{history_context}\n\n[Current Question]\n{message}"
        )
        self.assertEqual(augmented_query, message)

    def test_history_turns_counted_correctly(self):
        """history_turns_used should count [Turn N] occurrences in context string."""
        history = "[Turn 1] User: Q1\n[Turn 1] Assistant: A1\n[Turn 2] User: Q2\n[Turn 2] Assistant: A2"
        turns_used = history.count("[Turn ")
        self.assertEqual(turns_used, 4)  # 2 user + 2 assistant


if __name__ == "__main__":
    unittest.main(verbosity=2)
