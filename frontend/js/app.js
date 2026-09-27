/* Comprehensive Enterprise Application UI Logic for NEXUS */

document.addEventListener("DOMContentLoaded", async () => {
    await initAuthSimulator();
    setupNavigation();
    setupUploadHandlers();
    await refreshDashboard();
});

async function initAuthSimulator() {
    const roleSelector = document.getElementById("role-simulator");
    
    try {
        await api.login("admin@nexus.com", "AdminPass123!");
        updateUserProfileUI(api.currentUser);
    } catch (e) {
        console.warn("Auto-login default failed:", e);
    }

    roleSelector.addEventListener("change", async (e) => {
        const selectedEmail = e.target.value;
        let password = "AdminPass123!";
        if (selectedEmail.includes("employee")) password = "Employee123!";
        if (selectedEmail.includes("hr")) password = "HRPass123!";
        if (selectedEmail.includes("finance")) password = "Finance123!";
        if (selectedEmail.includes("security")) password = "Security123!";

        try {
            await api.login(selectedEmail, password);
            updateUserProfileUI(api.currentUser);
            await refreshDashboard();
        } catch (err) {
            alert(`Authentication failed for ${selectedEmail}: ${err.message}`);
        }
    });
}

function updateUserProfileUI(user) {
    if (!user) return;
    document.getElementById("user-name-text").innerText = user.full_name;
    document.getElementById("user-role-text").innerText = user.role;
    document.getElementById("user-avatar-text").innerText = user.full_name.charAt(0).toUpperCase();
}

function setupNavigation() {
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            switchView(item.getAttribute("data-view"));
        });
    });
}

function switchView(viewId) {
    document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".view-panel").forEach(el => el.classList.remove("active"));

    const navItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    const viewPanel = document.getElementById(viewId);

    if (navItem) navItem.classList.add("active");
    if (viewPanel) viewPanel.classList.add("active");

    const titleMap = {
        "dashboard-view": "Enterprise Dashboard",
        "documents-view": "Document Intelligence Registry",
        "search-view": "Hybrid Retrieval & Reranking Studio",
        "chat-view": "Agentic RAG Chat & Citation Grounding",
        "compare-view": "Multi-Doc Comparison & Conflict Matrix",
        "eval-view": "ML Evaluation & Experiment Suite",
        "memory-view": "Conversation Memory & Multi-Turn Sessions",
        "system-view": "System Observability & Token Metrics"
    };
    document.getElementById("page-heading").innerText = titleMap[viewId] || "NEXUS Platform";

    if (viewId === "eval-view") loadEvalView();
    if (viewId === "system-view") loadSystemMetricsView();
}

function setupUploadHandlers() {
    const dropzone = document.getElementById("pdf-dropzone");
    const fileInput = document.getElementById("file-input");

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.style.borderColor = "var(--primary)"; });
    dropzone.addEventListener("dragleave", () => { dropzone.style.borderColor = "var(--border-color)"; });
    dropzone.addEventListener("drop", async (e) => {
        e.preventDefault();
        dropzone.style.borderColor = "var(--border-color)";
        if (e.dataTransfer.files.length > 0) await handleFileUpload(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener("change", async () => {
        if (fileInput.files.length > 0) await handleFileUpload(fileInput.files[0]);
    });
}

async function handleFileUpload(file) {
    const statusDiv = document.getElementById("upload-status");
    const logBox = document.getElementById("pipeline-log");

    statusDiv.style.color = "var(--primary)";
    statusDiv.innerText = `⏳ Uploading and parsing '${file.name}'...`;
    logBox.innerText += `\n[Ingestion] Received '${file.name}' (${(file.size/1024).toFixed(1)} KB).`;

    const metadata = {
        department: document.getElementById("meta-dept").value,
        access_level: document.getElementById("meta-access").value
    };

    try {
        const doc = await api.uploadDocument(file, metadata);
        statusDiv.style.color = "var(--accent-teal)";
        statusDiv.innerText = `✅ Ingested '${doc.filename}' (${doc.chunk_count} chunks generated across ${doc.page_count} pages).`;

        logBox.innerText += `\n[Parser] Page-aware extraction completed (${doc.page_count} pages).`;
        logBox.innerText += `\n[Chunker] Created ${doc.chunk_count} semantic chunks tagged '${doc.access_level}'.`;
        logBox.scrollTop = logBox.scrollHeight;

        await refreshDashboard();
    } catch (err) {
        statusDiv.style.color = "var(--accent-rose)";
        statusDiv.innerText = `❌ Ingestion Error: ${err.message}`;
        logBox.innerText += `\n[ERROR] ${err.message}`;
    }
}

async function refreshDashboard() {
    try {
        const docs = await api.getDocuments();
        document.getElementById("stat-doc-count").innerText = docs.length;
        const totalChunks = docs.reduce((acc, d) => acc + (d.chunk_count || 0), 0);
        document.getElementById("stat-chunk-count").innerText = totalChunks;

        const tbodyRecent = document.getElementById("recent-docs-tbody");
        const tbodyAll = document.getElementById("all-docs-tbody");

        if (docs.length === 0) {
            tbodyRecent.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No documents uploaded yet.</td></tr>`;
            tbodyAll.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted);">No documents in registry.</td></tr>`;
            return;
        }

        const renderRows = (docList, isFull = false) => {
            return docList.map(d => {
                const badgeClass = `badge-${d.access_level.toLowerCase()}`;
                const createdDate = new Date(d.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `
                    <tr>
                        <td style="font-weight: 600;">${d.filename}</td>
                        <td>${d.department}</td>
                        <td><span style="font-family: var(--font-code); font-size: 12px;">${d.version}</span></td>
                        <td><span class="badge ${badgeClass}">${d.access_level}</span></td>
                        <td>${d.page_count}</td>
                        <td>${d.chunk_count}</td>
                        ${isFull ? '' : `<td>${createdDate}</td>`}
                        ${isFull ? `<td><button class="btn btn-secondary" style="padding: 4px 10px; font-size: 11px;" onclick="viewDocDetail('${d.id}')">View</button></td>` : ''}
                    </tr>
                `;
            }).join("");
        };

        tbodyRecent.innerHTML = renderRows(docs.slice(0, 5));
        tbodyAll.innerHTML = renderRows(docs, true);
    } catch (e) {
        console.error("Dashboard refresh error:", e);
    }
}

/* SEARCH STUDIO */
async function runSearchQuery() {
    const query = document.getElementById("search-input").value;
    const mode = document.getElementById("search-mode").value;
    const box = document.getElementById("search-results-box");

    if (!query) return alert("Please enter a query.");

    box.innerHTML = `<p style="color: var(--primary);">⏳ Executing ${mode} search...</p>`;

    try {
        const res = await api.search(query, mode, 5);
        let html = `
            <div style="margin-bottom: 14px; font-size: 13px; color: var(--text-secondary);">
                Retrieved <strong>${res.results_count} candidates</strong> in <strong>${res.latency_ms} ms</strong> for role <strong>${res.user_role}</strong>.
            </div>
        `;

        res.results.forEach((r, idx) => {
            html += `
                <div class="card" style="margin-bottom: 12px; padding: 16px; background: var(--bg-surface-elevated);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-weight: 600; font-size: 14px;">#${idx+1} ${r.filename} (${r.version}) — Page ${r.page_number}</span>
                        <span class="badge badge-internal">Score: ${r.score}</span>
                    </div>
                    <p style="font-size: 13px; color: var(--text-primary); line-height: 1.5;">${r.content}</p>
                </div>
            `;
        });

        box.innerHTML = html;
    } catch (e) {
        box.innerHTML = `<p style="color: var(--accent-rose);">Error: ${e.message}</p>`;
    }
}

/* RAG CHAT & AGENTS */
async function sendChatMessage(customMsg = null) {
    const input = document.getElementById("chat-input");
    const query = customMsg || input.value;
    if (!query) return;

    if (!customMsg) input.value = "";

    const chatBox = document.getElementById("chat-messages");
    const traceBox = document.getElementById("agent-trace-box");
    const citBox = document.getElementById("citations-box");

    // Add User Message
    chatBox.innerHTML += `
        <div style="background: var(--bg-surface-elevated); padding: 14px; border-radius: var(--radius-md); align-self: flex-end; max-width: 80%;">
            <p style="font-size: 13px; font-weight: 600;">You: ${query}</p>
        </div>
    `;
    chatBox.scrollTop = chatBox.scrollHeight;

    traceBox.innerText += `\n[Agent] User Query Received: "${query}"`;
    traceBox.innerText += `\n[Router] Classifying intent...`;
    traceBox.scrollTop = traceBox.scrollHeight;

    try {
        const res = await api.chat(query);

        // Update Agent Trace
        res.agent_trace.forEach(st => {
            traceBox.innerText += `\n[Step: ${st.step}] ${JSON.stringify(st)}`;
        });
        traceBox.scrollTop = traceBox.scrollHeight;

        // Render Answer Markdown
        chatBox.innerHTML += `
            <div style="background: rgba(31, 41, 61, 0.7); padding: 16px; border-radius: var(--radius-md); border-left: 3px solid var(--accent-teal);">
                <div style="display: flex; justify-content: space-between; font-size: 11px; color: var(--text-secondary); margin-bottom: 8px;">
                    <span>Grounding Score: ${(res.grounding_score*100).toFixed(0)}%</span>
                    <span>Latency: ${res.metrics.latency_ms} ms</span>
                </div>
                <div style="font-size: 13px; line-height: 1.6; white-space: pre-line;">${res.answer}</div>
            </div>
        `;
        chatBox.scrollTop = chatBox.scrollHeight;

        // Render Citations with Interactive Inspector
        if (res.citations.length > 0) {
            window._lastCitations = res.citations;
            window._lastGroundingScore = res.grounding_score;
            citBox.innerHTML = res.citations.map((c, idx) => `
                <div class="citation-interactive-item" style="background: var(--bg-surface-elevated); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color); font-size: 12px; margin-bottom: 8px;" onclick="openCitationModalByIndex(${idx})">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: 600; color: var(--primary);">📄 ${c.document_name} — Page ${c.page}</span>
                        <span style="font-size: 10px; color: var(--accent-teal); font-weight: 600;">Verified ✓</span>
                    </div>
                    <div style="color: var(--text-secondary); font-size: 11px; margin-top: 4px; line-height: 1.4;">"${c.excerpt}"</div>
                    <div style="font-size: 10px; color: var(--primary); margin-top: 6px;">🔍 Click to inspect verified source passage →</div>
                </div>
            `).join("");
        } else {
            citBox.innerHTML = `<p style="font-size: 12px; color: var(--text-muted);">No direct citations required.</p>`;
        }

    } catch (e) {
        chatBox.innerHTML += `<div style="color: var(--accent-rose); font-size: 13px;">Error: ${e.message}</div>`;
    }
}

/* COMPARE & CONFLICTS */
async function runDocumentComparison() {
    const box = document.getElementById("compare-results-box");
    box.innerHTML = `<p style="color: var(--primary);">⏳ Loading Travel Policy 2024 vs 2025 comparison...</p>`;

    try {
        const docs = await api.getDocuments();
        const doc24 = docs.find(d => d.filename.includes("2024"));
        const doc25 = docs.find(d => d.filename.includes("2025"));

        if (!doc24 || !doc25) {
            return box.innerHTML = `<p style="color: var(--accent-rose);">Sample travel policies not found in registry. Ingest sample data first.</p>`;
        }

        const comp = await api.compare(doc24.id, doc25.id);
        
        let html = `
            <h4 style="margin-bottom: 12px; font-size: 14px;">Comparing ${comp.doc1.filename} vs ${comp.doc2.filename}</h4>
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th>Category / Section</th>
                            <th>2024 Value</th>
                            <th>2025 Value</th>
                            <th>Delta Change</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${comp.comparison_matrix.map(row => `
                            <tr>
                                <td style="font-weight:600;">${row.category_section}</td>
                                <td>${row.val_doc1}</td>
                                <td>${row.val_doc2}</td>
                                <td><span class="badge badge-internal">${row.change}</span></td>
                            </tr>
                        `).join("")}
                    </tbody>
                </table>
            </div>
        `;
        box.innerHTML = html;
    } catch (e) {
        box.innerHTML = `<p style="color: var(--accent-rose);">Error: ${e.message}</p>`;
    }
}

async function runConflictDetector() {
    const box = document.getElementById("compare-results-box");
    box.innerHTML = `<p style="color: var(--accent-amber);">⏳ Searching across documents for policy contradictions...</p>`;

    try {
        const res = await api.detectConflicts("remote work");
        if (!res.conflicts_detected) {
            return box.innerHTML = `<p>No contradictions detected.</p>`;
        }

        const conf = res.conflict_list[0];
        let html = `
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid var(--accent-amber); padding: 18px; border-radius: var(--radius-md);">
                <h4 style="color: var(--accent-amber); font-size: 15px; margin-bottom: 8px;">⚠️ ${conf.conflict_type}: Remote Work Limits</h4>
                <p style="font-size: 13px; margin-bottom: 12px;">${conf.details}</p>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                    ${conf.evidence.map(ev => `
                        <div style="background: var(--bg-surface); padding: 12px; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
                            <div style="font-weight: 600; font-size: 13px; color: var(--primary);">${ev.filename} (v${ev.version})</div>
                            <div style="font-size: 12px; margin-top: 4px;">Limit: <strong>${ev.days} days per week</strong></div>
                            <div style="font-size: 11px; color: var(--text-secondary); margin-top: 6px;">"${ev.excerpt}"</div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
        box.innerHTML = html;
    } catch (e) {
        box.innerHTML = `<p style="color: var(--accent-rose);">Error: ${e.message}</p>`;
    }
}

/* EVALUATION VIEW */
async function loadEvalView() {
    try {
        const runs = await api.getEvalRuns();
        const tbody = document.getElementById("eval-runs-tbody");
        
        if (runs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color: var(--text-muted);">No benchmark experiments run yet. Click "Run Benchmark Experiment" to evaluate.</td></tr>`;
            return;
        }

        tbody.innerHTML = runs.map(r => `
            <tr>
                <td style="font-weight:600;">${r.run_name}</td>
                <td><span class="badge badge-internal">${r.retrieval_strategy}</span></td>
                <td>${r.recall_at_5}</td>
                <td>${r.precision_at_5}</td>
                <td>${r.mrr}</td>
                <td>${r.ndcg}</td>
                <td style="color: var(--accent-teal); font-weight:600;">${r.faithfulness_score}</td>
                <td>${r.avg_latency_ms} ms</td>
            </tr>
        `).join("");

        // Update Stat Cards with latest run
        const latest = runs[0];
        document.getElementById("eval-recall").innerText = latest.recall_at_5;
        document.getElementById("eval-precision").innerText = latest.precision_at_5;
        document.getElementById("eval-mrr").innerText = latest.mrr;
        document.getElementById("eval-faith").innerText = latest.faithfulness_score;

    } catch (e) {
        console.error("Eval view load error:", e);
    }
}

async function runBenchmarkEvaluation() {
    alert("Running ML Benchmark Experiment across gold-standard dataset...");
    try {
        await api.runEvalBenchmark("hybrid_rerank");
        await loadEvalView();
    } catch (e) {
        alert("Benchmark error: " + e.message);
    }
}

/* SYSTEM METRICS VIEW */
async function loadSystemMetricsView() {
    try {
        const health = await api.getHealth();
        document.getElementById("system-health-box").innerHTML = `
STATUS: ${health.status.toUpperCase()}
PROJECT: ${health.project} v${health.version}
UPTIME: ${health.uptime_seconds} s | MEMORY: ${health.memory_usage_mb} MB | DB: ${health.database}
BEDROCK ENABLED: ${health.aws_bedrock_enabled} | QDRANT IN-MEMORY: ${health.qdrant_in_memory}
        `;

        const logs = await api.getAuditLogs();
        const tbody = document.getElementById("audit-logs-tbody");
        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; color: var(--text-muted);">No query logs recorded yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr>
                <td>${new Date(l.created_at).toLocaleTimeString()}</td>
                <td style="font-weight:600;">${l.query_text}</td>
                <td>${l.intent_classified || 'simple_qa'}</td>
                <td>${l.total_tokens}</td>
                <td>${l.latency_ms} ms</td>
                <td>$${l.estimated_cost.toFixed(4)}</td>
                <td>${((l.grounding_score||0)*100).toFixed(0)}%</td>
            </tr>
        `).join("");
    } catch (e) {
        console.error("Metrics view error:", e);
    }
}

/* DEMO SCENARIOS TRIGGER */
async function triggerDemo(demoNum) {
    switchView("chat-view");
    const chatInput = document.getElementById("chat-input");

    if (demoNum === 1) {
        await sendChatMessage("What is the international travel reimbursement limit?");
    } else if (demoNum === 2) {
        await sendChatMessage("Compare the 2024 and 2025 travel policies and tell me what changed.");
    } else if (demoNum === 3) {
        await sendChatMessage("Are there conflicting policies regarding remote work?");
    } else if (demoNum === 4) {
        await sendChatMessage("Analyze all cybersecurity-related documents and produce an executive summary of major policy changes introduced in 2025.");
    } else if (demoNum === 7) {
        // Test RBAC Denial as Employee accessing Confidential document
        const roleSel = document.getElementById("role-simulator");
        roleSel.value = "employee@nexus.com";
        roleSel.dispatchEvent(new Event("change"));
        
        setTimeout(async () => {
            await sendChatMessage("Show me the cybersecurity SOP password rules.");
        }, 500);
    }
}

async function viewDocDetail(docId) {
    try {
        const detail = await api.getDocumentDetail(docId);
        alert(`Document: ${detail.filename}\nVersion: ${detail.version}\nAccess Level: ${detail.access_level}\nTotal Chunks: ${detail.chunk_count}\nFirst Chunk Excerpt:\n\n${detail.chunks[0]?.content.substring(0, 250)}...`);
    } catch (e) {
        alert("Access Denied or Error: " + e.message);
    }
}

/* Citation Inspector Modal Logic */
function openCitationModalByIndex(idx) {
    if (!window._lastCitations || !window._lastCitations[idx]) return;
    const c = window._lastCitations[idx];
    const score = window._lastGroundingScore || 0.95;
    
    document.getElementById("modal-doc-title").innerText = c.document_name || "Document Citation";
    document.getElementById("modal-doc-page").innerText = `Page ${c.page || 1}`;
    document.getElementById("modal-doc-section").innerText = c.section ? `Section: ${c.section}` : "Section: General";
    
    const pct = Math.round(score * 100);
    document.getElementById("modal-grounding-pct").innerText = `${pct}%`;
    document.getElementById("modal-grounding-fill").style.width = `${pct}%`;
    
    document.getElementById("modal-doc-excerpt").innerText = `"${c.excerpt}"`;
    
    document.getElementById("citation-modal").classList.add("active");
}

function closeCitationModal() {
    document.getElementById("citation-modal").classList.remove("active");
}

/* ====================================================================
   PHASE 3: MULTI-TURN CONVERSATION MEMORY
   ==================================================================== */

let activeSessionId = null;

async function initConversationMemory() {
    await loadConversationSessions();
    // Patch the switchView to load conversation view
    const origSwitch = window.switchViewOrig || switchView;
    window.switchViewOrig = origSwitch;
}

async function createNewSession() {
    try {
        const session = await api.createConversationSession();
        activeSessionId = session.id;
        await loadConversationSessions();
        loadSessionMessages(session.id);
        renderSessionActive(session);
    } catch (e) {
        console.error("Create session error:", e);
    }
}

async function loadConversationSessions() {
    const listEl = document.getElementById("sessions-list");
    if (!listEl) return;
    try {
        const sessions = await api.listConversationSessions();
        if (sessions.length === 0) {
            listEl.innerHTML = `<div style="color:var(--text-muted);font-size:12px;padding:8px;">No conversations yet. Start one above.</div>`;
            return;
        }
        listEl.innerHTML = sessions.map(s => `
            <div class="session-item ${s.id === activeSessionId ? 'active' : ''}"
                 id="session-item-${s.id}"
                 onclick="selectSession('${s.id}')"
                 style="padding: 10px 12px; border-radius: var(--radius-sm); margin-bottom: 6px; cursor: pointer;
                        background: ${s.id === activeSessionId ? 'var(--bg-surface-elevated)' : 'transparent'};
                        border: 1px solid ${s.id === activeSessionId ? 'var(--primary)' : 'var(--border-color)'};
                        transition: all 0.2s;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <span style="font-size:12px;font-weight:600;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px;" title="${s.title}">${s.title}</span>
                    <button onclick="event.stopPropagation(); deleteSession('${s.id}')"
                            style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px;padding:0 2px;"
                            title="Delete session">×</button>
                </div>
                <div style="font-size:10px;color:var(--text-muted);margin-top:2px;">${s.turn_count} turns</div>
            </div>
        `).join("");
    } catch (e) {
        console.error("Load sessions error:", e);
    }
}

async function selectSession(sessionId) {
    activeSessionId = sessionId;
    await loadConversationSessions();
    try {
        const session = await api.getConversationSession(sessionId);
        renderSessionActive(session);
    } catch (e) { console.error(e); }
}

function renderSessionActive(session) {
    const msgBox = document.getElementById("memory-chat-messages");
    if (!msgBox) return;
    if (!session.messages || session.messages.length === 0) {
        msgBox.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">
            No messages yet. Start the conversation below.
        </div>`;
        return;
    }
    msgBox.innerHTML = session.messages.map(m => {
        if (m.role === "user") {
            return `<div style="background:var(--bg-surface-elevated);padding:12px 16px;border-radius:var(--radius-md);align-self:flex-end;max-width:78%;margin-bottom:8px;">
                <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">You</div>
                <div style="font-size:13px;line-height:1.5;">${m.content}</div>
            </div>`;
        } else {
            const score = m.grounding_score ? `${(m.grounding_score*100).toFixed(0)}%` : "—";
            const citCount = (m.citations || []).length;
            return `<div style="background:rgba(31,41,61,0.7);padding:14px 16px;border-radius:var(--radius-md);border-left:3px solid var(--accent-teal);margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:8px;">
                    <span>NEXUS Agent</span>
                    <span>Grounding: ${score} | ${m.latency_ms}ms | ${citCount} citation${citCount !== 1 ? 's' : ''}</span>
                </div>
                <div style="font-size:13px;line-height:1.6;white-space:pre-line;">${m.content}</div>
            </div>`;
        }
    }).join("");
    msgBox.scrollTop = msgBox.scrollHeight;
}

async function sendMemoryChatMessage() {
    const input = document.getElementById("memory-chat-input");
    const query = input?.value?.trim();
    if (!query || !activeSessionId) {
        if (!activeSessionId) {
            alert("Please create or select a conversation session first.");
        }
        return;
    }
    input.value = "";

    const msgBox = document.getElementById("memory-chat-messages");
    const useMemory = document.getElementById("use-memory-toggle")?.checked !== false;

    // Optimistically render user message
    msgBox.innerHTML += `
        <div style="background:var(--bg-surface-elevated);padding:12px 16px;border-radius:var(--radius-md);align-self:flex-end;max-width:78%;margin-bottom:8px;">
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px;">You</div>
            <div style="font-size:13px;line-height:1.5;">${query}</div>
        </div>
        <div id="typing-indicator" style="color:var(--primary);font-size:12px;padding:8px;animation:pulse 1.5s infinite;">
            ⚡ NEXUS Agent thinking${useMemory ? ' (with conversation memory)' : ''}...
        </div>
    `;
    msgBox.scrollTop = msgBox.scrollHeight;

    const historyTurnsEl = document.getElementById("memory-turns-used");

    try {
        const res = await api.sendConversationMessage(activeSessionId, query, useMemory);
        document.getElementById("typing-indicator")?.remove();

        const citCount = (res.citations || []).length;
        msgBox.innerHTML += `
            <div style="background:rgba(31,41,61,0.7);padding:14px 16px;border-radius:var(--radius-md);border-left:3px solid var(--accent-teal);margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;font-size:10px;color:var(--text-muted);margin-bottom:8px;">
                    <span>NEXUS Agent${res.history_turns_used > 0 ? ` | 💬 ${res.history_turns_used} prior turns used` : ''}</span>
                    <span>Grounding: ${(res.grounding_score*100).toFixed(0)}% | ${res.metrics?.latency_ms}ms | ${citCount} citation${citCount !== 1 ? 's' : ''}</span>
                </div>
                <div style="font-size:13px;line-height:1.6;white-space:pre-line;">${res.answer}</div>
            </div>
        `;
        if (historyTurnsEl) historyTurnsEl.innerText = res.history_turns_used;
        msgBox.scrollTop = msgBox.scrollHeight;
        await loadConversationSessions();
    } catch (e) {
        document.getElementById("typing-indicator")?.remove();
        msgBox.innerHTML += `<div style="color:var(--accent-rose);font-size:13px;padding:8px;">Error: ${e.message}</div>`;
    }
}

async function deleteSession(sessionId) {
    if (!confirm("Delete this conversation? This cannot be undone.")) return;
    try {
        await api.deleteConversationSession(sessionId);
        if (activeSessionId === sessionId) {
            activeSessionId = null;
            const msgBox = document.getElementById("memory-chat-messages");
            if (msgBox) msgBox.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">Select or create a conversation.</div>`;
        }
        await loadConversationSessions();
    } catch (e) { console.error(e); }
}

/* ====================================================================
   PHASE 3: OBSERVABILITY DASHBOARD (CANVAS CHARTS)
   ==================================================================== */

async function loadObservabilityDashboard() {
    await loadSystemMetricsView();
    await loadEnhancedMetrics();
}

async function loadEnhancedMetrics() {
    try {
        // Load all metrics in parallel
        const [timeseries, intentDist, modelUsage, latencyPercentiles, embedBackend] = await Promise.all([
            api.getMetricsTimeseries(),
            api.getIntentDistribution(),
            api.getModelUsage(),
            api.getLatencyPercentiles(),
            api.getEmbeddingBackend(),
        ]);

        renderTimeseriesChart(timeseries.buckets);
        renderIntentDistribution(intentDist.distribution);
        renderModelUsageTable(modelUsage.models);
        renderLatencyPercentiles(latencyPercentiles);
        renderEmbeddingBackendCard(embedBackend);
    } catch (e) {
        console.error("Enhanced metrics load error:", e);
    }
}

function renderTimeseriesChart(buckets) {
    const container = document.getElementById("timeseries-chart-container");
    if (!container) return;

    if (!buckets || buckets.length === 0) {
        container.innerHTML = `<div style="text-align:center;color:var(--text-muted);padding:40px;font-size:13px;">
            No time-series data yet. Make some queries first.
        </div>`;
        return;
    }

    // SVG-based sparkline chart
    const W = 580, H = 130, PAD = 30;
    const maxQ = Math.max(...buckets.map(b => b.queries), 1);
    const maxLat = Math.max(...buckets.map(b => b.avg_latency_ms), 1);

    const xStep = buckets.length > 1 ? (W - PAD * 2) / (buckets.length - 1) : (W - PAD * 2);

    const queryPoints = buckets.map((b, i) => ({
        x: PAD + i * xStep,
        y: H - PAD - ((b.queries / maxQ) * (H - PAD * 2))
    }));
    const latPoints = buckets.map((b, i) => ({
        x: PAD + i * xStep,
        y: H - PAD - ((b.avg_latency_ms / maxLat) * (H - PAD * 2))
    }));

    const toPath = (pts) => pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');

    container.innerHTML = `
        <div style="margin-bottom:10px;font-size:13px;font-weight:600;color:var(--text-primary);">
            📈 Query Volume & Latency Over Time
            <span style="font-size:11px;font-weight:400;color:var(--text-muted);margin-left:12px;">
                <span style="color:var(--primary);">■</span> Queries
                <span style="color:var(--accent-teal);margin-left:8px;">■</span> Avg Latency
            </span>
        </div>
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;overflow:visible;">
            <!-- Grid lines -->
            ${[0.25, 0.5, 0.75, 1].map(t => `
                <line x1="${PAD}" y1="${H - PAD - t*(H-PAD*2)}"
                      x2="${W - PAD}" y2="${H - PAD - t*(H-PAD*2)}"
                      stroke="rgba(255,255,255,0.06)" stroke-width="1"/>
            `).join('')}
            <!-- Axes -->
            <line x1="${PAD}" y1="${PAD}" x2="${PAD}" y2="${H-PAD}" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
            <line x1="${PAD}" y1="${H-PAD}" x2="${W-PAD}" y2="${H-PAD}" stroke="rgba(255,255,255,0.15)" stroke-width="1"/>
            <!-- Query line fill -->
            <defs>
                <linearGradient id="qGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="var(--primary)" stop-opacity="0.3"/>
                    <stop offset="100%" stop-color="var(--primary)" stop-opacity="0"/>
                </linearGradient>
                <linearGradient id="lGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="var(--accent-teal)" stop-opacity="0.2"/>
                    <stop offset="100%" stop-color="var(--accent-teal)" stop-opacity="0"/>
                </linearGradient>
            </defs>
            <path d="${toPath(queryPoints)} L ${queryPoints[queryPoints.length-1].x} ${H-PAD} L ${queryPoints[0].x} ${H-PAD} Z" fill="url(#qGrad)"/>
            <path d="${toPath(queryPoints)}" fill="none" stroke="var(--primary)" stroke-width="2" stroke-linejoin="round"/>
            <path d="${toPath(latPoints)}" fill="none" stroke="var(--accent-teal)" stroke-width="2" stroke-linejoin="round" stroke-dasharray="4 2"/>
            <!-- Data points -->
            ${queryPoints.map((p, i) => `
                <circle cx="${p.x}" cy="${p.y}" r="3" fill="var(--primary)" stroke="var(--bg-base)" stroke-width="1.5">
                    <title>${buckets[i].hour}: ${buckets[i].queries} queries</title>
                </circle>
            `).join('')}
            <!-- X labels (show every 2nd) -->
            ${buckets.filter((_, i) => i % Math.ceil(buckets.length / 5) === 0).map((b, i, arr) => {
                const origIdx = buckets.indexOf(b);
                const x = queryPoints[origIdx]?.x || 0;
                return `<text x="${x}" y="${H-2}" text-anchor="middle" font-size="9" fill="rgba(255,255,255,0.4)">${b.hour.slice(11)}</text>`;
            }).join('')}
        </svg>
    `;
}

function renderIntentDistribution(distribution) {
    const container = document.getElementById("intent-distribution-container");
    if (!container) return;

    if (!distribution || distribution.length === 0) {
        container.innerHTML = `<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:20px;">No intent data yet.</div>`;
        return;
    }

    const colors = {
        "simple_qa": "var(--primary)",
        "compare_docs": "var(--accent-teal)",
        "detect_conflict": "var(--accent-amber)",
        "executive_report": "var(--accent-rose)"
    };
    const labels = {
        "simple_qa": "Simple Q&A",
        "compare_docs": "Document Compare",
        "detect_conflict": "Conflict Detection",
        "executive_report": "Executive Report"
    };

    container.innerHTML = `
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:12px;">🧠 Intent Distribution</div>
        ${distribution.map(d => `
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">
                    <span style="color:${colors[d.intent]||'var(--text-secondary)'};">${labels[d.intent]||d.intent}</span>
                    <span style="color:var(--text-muted);">${d.count} (${d.percentage}%)</span>
                </div>
                <div style="background:rgba(255,255,255,0.08);border-radius:99px;height:6px;overflow:hidden;">
                    <div style="width:${d.percentage}%;height:100%;background:${colors[d.intent]||'var(--primary)'};border-radius:99px;transition:width 0.6s ease;"></div>
                </div>
            </div>
        `).join('')}
    `;
}

function renderModelUsageTable(models) {
    const container = document.getElementById("model-usage-container");
    if (!container) return;

    if (!models || models.length === 0) {
        container.innerHTML = `<div style="text-align:center;color:var(--text-muted);font-size:12px;padding:20px;">No model usage data.</div>`;
        return;
    }

    container.innerHTML = `
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:12px;">🤖 Model Usage & Cost</div>
        <div class="table-container" style="max-height:160px;overflow-y:auto;">
            <table>
                <thead><tr><th>Model</th><th>Calls</th><th>Tokens</th><th>Cost (USD)</th><th>Avg Lat.</th></tr></thead>
                <tbody>
                ${models.map(m => `
                    <tr>
                        <td style="font-size:11px;font-family:var(--font-code);">${m.model.split('-').slice(0,3).join('-')}</td>
                        <td>${m.calls}</td>
                        <td>${m.total_tokens.toLocaleString()}</td>
                        <td style="color:var(--accent-teal);">$${m.total_cost_usd.toFixed(4)}</td>
                        <td>${m.avg_latency_ms.toFixed(0)}ms</td>
                    </tr>
                `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

function renderLatencyPercentiles(data) {
    const container = document.getElementById("latency-percentiles-container");
    if (!container) return;

    container.innerHTML = `
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:14px;">⚡ Latency Percentiles (${data.count} queries)</div>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;">
            ${[
                {label:"P50", value: data.p50},
                {label:"P90", value: data.p90},
                {label:"P95", value: data.p95, highlight: true},
                {label:"P99", value: data.p99}
            ].map(p => `
                <div style="background:var(--bg-surface-elevated);border-radius:var(--radius-sm);padding:12px;text-align:center;
                     border:1px solid ${p.highlight ? 'var(--primary)' : 'var(--border-color)'};">
                    <div style="font-size:10px;color:var(--text-muted);margin-bottom:4px;">${p.label}</div>
                    <div style="font-size:18px;font-weight:700;color:${p.highlight ? 'var(--primary)' : 'var(--text-primary)'};">${p.value || 0}</div>
                    <div style="font-size:9px;color:var(--text-muted);">ms</div>
                </div>
            `).join('')}
        </div>
        <div style="margin-top:10px;font-size:11px;color:var(--text-muted);">
            Min: ${data.min||0}ms &nbsp;|&nbsp; Max: ${data.max||0}ms
        </div>
    `;
}

function renderEmbeddingBackendCard(info) {
    const container = document.getElementById("embedding-backend-container");
    if (!container) return;

    const backendColors = {
        "local": "var(--accent-amber)",
        "sagemaker": "var(--accent-teal)",
        "bedrock_titan": "var(--primary)",
        "zero_vector": "var(--accent-rose)"
    };
    const backendLabels = {
        "local": "Local sentence-transformers",
        "sagemaker": "Amazon SageMaker Endpoint",
        "bedrock_titan": "Amazon Bedrock Titan Embeddings",
        "zero_vector": "Zero-Vector (Fallback)"
    };

    const color = backendColors[info.active_backend] || "var(--text-secondary)";
    container.innerHTML = `
        <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:12px;">🧮 Embedding Backend</div>
        <div style="background:var(--bg-surface-elevated);border-radius:var(--radius-md);padding:16px;border:1px solid ${color}40;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                <div style="width:10px;height:10px;border-radius:50%;background:${color};box-shadow:0 0 8px ${color};"></div>
                <span style="font-weight:600;color:${color};">${backendLabels[info.active_backend]||info.active_backend}</span>
            </div>
            <div style="font-size:12px;color:var(--text-secondary);line-height:1.7;">
                <div>Model: <code style="font-family:var(--font-code);font-size:11px;color:var(--text-primary);">${info.model_name}</code></div>
                <div>Dimension: <strong>${info.embedding_dimension}</strong></div>
                <div style="margin-top:8px;font-size:10px;color:var(--text-muted);">
                    Fallback chain: ${info.fallback_chain.join(' → ')}
                </div>
            </div>
        </div>
    `;
}

/* Document delete functionality */
async function deleteDocument(docId, filename) {
    if (!confirm(`Delete "${filename}"? This will also remove all indexed chunks.`)) return;
    try {
        await api.deleteDocument(docId);
        await refreshDashboard();
    } catch (e) {
        alert("Delete error: " + e.message);
    }
}

/* Override switchView to handle new views */
const _origSwitchView = switchView;
window.switchView = function(viewId) {
    _origSwitchView(viewId);
    if (viewId === "memory-view") {
        initConversationMemory();
    }
    if (viewId === "system-view") {
        loadObservabilityDashboard();
    }
};

