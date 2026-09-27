/* Complete API Service Module for NEXUS Platform */

const API_BASE = "/api/v1";

class NexusAPI {
    constructor() {
        this.token = localStorage.getItem("nexus_token") || null;
        this.currentUser = JSON.parse(localStorage.getItem("nexus_user") || "null");
    }

    setAuth(token, user) {
        this.token = token;
        this.currentUser = user;
        localStorage.setItem("nexus_token", token);
        localStorage.setItem("nexus_user", JSON.stringify(user));
    }

    clearAuth() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem("nexus_token");
        localStorage.removeItem("nexus_user");
    }

    getHeaders(isMultipart = false) {
        const headers = {};
        if (this.token) {
            headers["Authorization"] = `Bearer ${this.token}`;
        }
        if (!isMultipart) {
            headers["Content-Type"] = "application/json";
        }
        return headers;
    }

    async login(email, password) {
        const formData = new URLSearchParams();
        formData.append("username", email);
        formData.append("password", password);

        const response = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Authentication failed");
        }

        const data = await response.json();
        this.setAuth(data.access_token, data.user);
        return data;
    }

    async getHealth() {
        const res = await fetch(`${API_BASE}/health`);
        return await res.json();
    }

    async getDocuments(department = null) {
        let url = `${API_BASE}/documents`;
        if (department) {
            url += `?department=${encodeURIComponent(department)}`;
        }
        const res = await fetch(url, { headers: this.getHeaders() });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to fetch documents");
        }
        return await res.json();
    }

    async uploadDocument(file, metadata = {}) {
        const formData = new FormData();
        formData.append("file", file);
        
        if (metadata.department) formData.append("department", metadata.department);
        if (metadata.document_type) formData.append("document_type", metadata.document_type);
        if (metadata.version) formData.append("version", metadata.version);
        if (metadata.effective_date) formData.append("effective_date", metadata.effective_date);
        if (metadata.access_level) formData.append("access_level", metadata.access_level);

        const res = await fetch(`${API_BASE}/documents/upload`, {
            method: "POST",
            headers: this.getHeaders(true),
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Document upload failed");
        }
        return await res.json();
    }

    async getDocumentDetail(docId) {
        const res = await fetch(`${API_BASE}/documents/${docId}`, { headers: this.getHeaders() });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to fetch document details");
        }
        return await res.json();
    }

    async search(query, mode = "hybrid_rerank", topK = 5) {
        const res = await fetch(`${API_BASE}/search`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ query, mode, top_k: topK })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Search request failed");
        }
        return await res.json();
    }

    async chat(message) {
        const res = await fetch(`${API_BASE}/chat`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ message })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Chat request failed");
        }
        return await res.json();
    }

    async compare(docId1, docId2) {
        const res = await fetch(`${API_BASE}/compare`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ doc_id_1: docId1, doc_id_2: docId2 })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Comparison failed");
        }
        return await res.json();
    }

    async detectConflicts(topic) {
        const res = await fetch(`${API_BASE}/compare/conflicts`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ topic })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Conflict detection failed");
        }
        return await res.json();
    }

    async getEvalRuns() {
        const res = await fetch(`${API_BASE}/evaluation/runs`, { headers: this.getHeaders() });
        if (!res.ok) return [];
        return await res.json();
    }

    async runEvalBenchmark(strategy = "hybrid_rerank") {
        const res = await fetch(`${API_BASE}/evaluation/run`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ strategy })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Benchmark run failed");
        }
        return await res.json();
    }

    async getMetricsSummary() {
        const res = await fetch(`${API_BASE}/metrics/summary`, { headers: this.getHeaders() });
        if (!res.ok) return null;
        return await res.json();
    }

    async getAuditLogs() {
        const res = await fetch(`${API_BASE}/metrics/logs`, { headers: this.getHeaders() });
        if (!res.ok) return [];
        return await res.json();
    }

    // ------------------------------------------------------------------ //
    // Phase 3: Enhanced Metrics                                            //
    // ------------------------------------------------------------------ //

    async getMetricsTimeseries(hours = 24) {
        const res = await fetch(`${API_BASE}/metrics/timeseries?hours=${hours}`, { headers: this.getHeaders() });
        if (!res.ok) return { buckets: [] };
        return await res.json();
    }

    async getIntentDistribution() {
        const res = await fetch(`${API_BASE}/metrics/intent-distribution`, { headers: this.getHeaders() });
        if (!res.ok) return { distribution: [] };
        return await res.json();
    }

    async getModelUsage() {
        const res = await fetch(`${API_BASE}/metrics/model-usage`, { headers: this.getHeaders() });
        if (!res.ok) return { models: [] };
        return await res.json();
    }

    async getLatencyPercentiles() {
        const res = await fetch(`${API_BASE}/metrics/latency-percentiles`, { headers: this.getHeaders() });
        if (!res.ok) return { p50: 0, p90: 0, p95: 0, p99: 0, count: 0 };
        return await res.json();
    }

    async getEmbeddingBackend() {
        const res = await fetch(`${API_BASE}/metrics/embedding-backend`, { headers: this.getHeaders() });
        if (!res.ok) return { active_backend: "unknown", embedding_dimension: 0, model_name: "N/A", fallback_chain: [] };
        return await res.json();
    }

    // ------------------------------------------------------------------ //
    // Phase 3: Conversation Memory                                         //
    // ------------------------------------------------------------------ //

    async createConversationSession(title = null) {
        const res = await fetch(`${API_BASE}/conversations`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ title })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to create session");
        }
        return await res.json();
    }

    async listConversationSessions() {
        const res = await fetch(`${API_BASE}/conversations`, { headers: this.getHeaders() });
        if (!res.ok) return [];
        return await res.json();
    }

    async getConversationSession(sessionId) {
        const res = await fetch(`${API_BASE}/conversations/${sessionId}`, { headers: this.getHeaders() });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Session not found");
        }
        return await res.json();
    }

    async deleteConversationSession(sessionId) {
        const res = await fetch(`${API_BASE}/conversations/${sessionId}`, {
            method: "DELETE",
            headers: this.getHeaders()
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Delete failed");
        }
        return await res.json();
    }

    async sendConversationMessage(sessionId, message, useMemory = true) {
        const res = await fetch(`${API_BASE}/conversations/${sessionId}/messages`, {
            method: "POST",
            headers: this.getHeaders(),
            body: JSON.stringify({ message, use_memory: useMemory })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Message failed");
        }
        return await res.json();
    }

    // ------------------------------------------------------------------ //
    // Phase 3: Document Delete                                             //
    // ------------------------------------------------------------------ //

    async deleteDocument(docId) {
        const res = await fetch(`${API_BASE}/documents/${docId}`, {
            method: "DELETE",
            headers: this.getHeaders()
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Delete failed");
        }
        return await res.json();
    }
}

const api = new NexusAPI();

