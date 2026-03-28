/**
 * app.js — NEXUS Session UI
 * SSE consumer, agent graph, MCP cards, response streaming, drawer
 */

const API_BASE = 'http://localhost:8000';

// Session state
let currentSessionId = null;
let isStreaming = false;
let mcpCardMap = {};          // tool → card element (for updating running → done)
let currentTraceDetail = {};  // tool → MCPCardDetail (for drawer)

// Agent metadata
const AGENT_META = {
    nexus_core: { color: '#4285F4', bg: '#E8F0FE', label: 'NEXUS Core' },
    atlas:      { color: '#1a73e8', bg: '#E8F0FE', label: 'Atlas' },
    chrono:     { color: '#EA4335', bg: '#FCE8E6', label: 'Chrono' },
    sage:       { color: '#34A853', bg: '#E6F4EA', label: 'Sage' },
    dash:       { color: '#FBBC04', bg: '#FEF7E0', label: 'Dash' },
    mnemo:      { color: '#9334E6', bg: '#F3E8FD', label: 'Mnemo' },
    flux:       { color: '#00BCD4', bg: '#E0F7FA', label: 'Flux' },
    quest:      { color: '#FF6D00', bg: '#FFF3E0', label: 'Quest' },
    lumen:      { color: '#0F9D58', bg: '#E6F4EA', label: 'Lumen' },
    forge:      { color: '#C2185B', bg: '#FCE4EC', label: 'Forge' },
};

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    generateSessionId();
    initInput();
    initGraph();
    markAgentsReady();
});

function generateSessionId() {
    currentSessionId = 'session-' + Date.now();
    const el = document.getElementById('session-id');
    if (el) el.textContent = currentSessionId.slice(-8);
}

function markAgentsReady() {
    document.querySelectorAll('.agent-status-card').forEach(card => {
        const st = card.querySelector('.status-text');
        if (st) st.textContent = 'Ready';
    });
}

// ─────────────────────────────────────────────
// INPUT
// ─────────────────────────────────────────────

function initInput() {
    const input = document.getElementById('chat-input');
    if (!input) return;

    // Auto-resize
    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 120) + 'px';
    });

    // Enter = send, Shift+Enter = newline
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
}

// ─────────────────────────────────────────────
// SEND
// ─────────────────────────────────────────────

async function sendMessage() {
    if (isStreaming) return;

    const input  = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const prompt = input.value.trim();
    if (!prompt) return;

    // Reset session artifacts
    mcpCardMap = {};
    currentTraceDetail = {};

    // UI: disable input
    input.disabled = true;
    sendBtn.disabled = true;
    isStreaming = true;
    input.value = '';
    input.style.height = 'auto';

    // Clear empty state from left rail
    const emptyState = document.querySelector('#mcp-cards .empty-state');
    if (emptyState) emptyState.remove();

    // Hide previous suggestions
    const suggestionsEl = document.getElementById('suggestions');
    if (suggestionsEl) suggestionsEl.classList.add('hidden');

    // Show user message
    appendUserMessage(prompt);

    // Stream from backend
    try {
        await streamChat(prompt);
    } catch (err) {
        console.error('Stream error:', err);
        appendErrorMessage('Could not reach NEXUS backend. Make sure the server is running on port 8000.');
    } finally {
        isStreaming = false;
        input.disabled = false;
        sendBtn.disabled = false;
        input.focus();
    }
}

// ─────────────────────────────────────────────
// STREAMING — fetch POST + ReadableStream
// ─────────────────────────────────────────────

async function streamChat(prompt) {
    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            prompt,
            user_id: 'demo-user',
            session_id: currentSessionId,
            demo_mode: true,
        }),
    });

    if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
    }

    const reader  = response.body.getReader();
    const decoder = new TextDecoder();
    let   buffer  = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete line in buffer

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                handleSSELine(line.slice(6).trim());
            }
        }
    }

    // Process any remaining buffer
    if (buffer.startsWith('data: ')) {
        handleSSELine(buffer.slice(6).trim());
    }
}

// ─────────────────────────────────────────────
// SSE EVENT HANDLER
// ─────────────────────────────────────────────

function handleSSELine(raw) {
    if (!raw || raw === '') return;

    let event;
    try {
        event = JSON.parse(raw);
    } catch {
        return; // skip non-JSON lines
    }

    switch (event.type) {
        case 'heartbeat':
            break; // keep-alive, ignore

        case 'trace':
            handleTraceEvent(event);
            break;

        case 'response':
            handleResponseEvent(event);
            break;

        case 'complete':
            break; // stream naturally ends

        case 'error':
            appendErrorMessage(event.error || 'Unknown error from agent');
            break;

        default:
            console.warn('Unknown SSE event type:', event.type);
    }
}

// ─────────────────────────────────────────────
// TRACE EVENT → MCP card + graph + right rail
// ─────────────────────────────────────────────

function handleTraceEvent(event) {
    const { agent, agent_display_name, tool, tool_display_name, action, status, detail } = event;

    const cardKey = `${agent}:${tool}`;

    if (status === 'running') {
        // Create or update MCP card
        if (!mcpCardMap[cardKey]) {
            mcpCardMap[cardKey] = createMCPCard(agent, agent_display_name, tool, tool_display_name, action, 'running');
        } else {
            updateMCPCardAction(mcpCardMap[cardKey], action, 'running');
        }
        setAgentWorking(agent, action);

    } else if (status === 'done') {
        const card = mcpCardMap[cardKey];
        if (card) {
            updateMCPCardAction(card, action, 'done');
        } else {
            // Card wasn't created for running (e.g. emit_memory_save shorthand)
            mcpCardMap[cardKey] = createMCPCard(agent, agent_display_name, tool, tool_display_name, action, 'done');
        }

        // Store detail for drawer
        if (detail) {
            currentTraceDetail[cardKey] = detail;
        }

        setAgentIdle(agent);

    } else if (status === 'error') {
        const card = mcpCardMap[cardKey];
        if (card) updateMCPCardAction(card, action, 'error');
        setAgentIdle(agent);
    }
}

// ─────────────────────────────────────────────
// RESPONSE EVENT → center panel
// ─────────────────────────────────────────────

function handleResponseEvent(event) {
    const result = event.result;
    if (!result) return;

    // Render markdown-ish response
    appendAgentResponse(result.agent, result.agent_display_name, result.full_response);

    // Show suggestions
    if (result.suggestions && result.suggestions.length > 0) {
        showSuggestions(result.suggestions);
    }

    // Mnemo glow
    if (result.memory_writes && result.memory_writes.length > 0) {
        flashMnemo();
    }
}

// ─────────────────────────────────────────────
// MCP CARDS — left rail
// ─────────────────────────────────────────────

function createMCPCard(agent, agentLabel, tool, toolLabel, action, status) {
    const meta = AGENT_META[agent] || { color: '#4285F4', bg: '#E8F0FE', label: agentLabel };
    const container = document.getElementById('mcp-cards');

    const card = document.createElement('div');
    card.className = `mcp-card ${status}`;
    card.dataset.agent = agent;
    card.dataset.tool = tool;
    card.style.setProperty('--agent-color', meta.color);

    card.innerHTML = `
        <div class="mcp-card-header">
            <div class="agent-dot" style="background:${meta.color}"></div>
            <span class="mcp-agent-name" style="color:${meta.color}">${escHtml(agentLabel)}</span>
            <span class="tool-name">${escHtml(toolLabel)}</span>
        </div>
        <div class="mcp-action">${escHtml(action)}</div>
        ${status === 'running' ? '<div class="mcp-pulse"></div>' : ''}
    `;

    card.addEventListener('click', () => openDrawer(agent, agentLabel, tool, toolLabel));
    container.appendChild(card);
    return card;
}

function updateMCPCardAction(card, action, status) {
    const actionEl = card.querySelector('.mcp-action');
    if (actionEl) actionEl.textContent = action;

    card.classList.remove('running', 'done', 'error');
    card.classList.add(status);

    // Remove pulse indicator on completion
    const pulse = card.querySelector('.mcp-pulse');
    if (pulse && status !== 'running') pulse.remove();
}

// ─────────────────────────────────────────────
// AGENT GRAPH — center panel
// ─────────────────────────────────────────────

function initGraph() {
    document.querySelectorAll('.graph-node').forEach(node => {
        node.addEventListener('click', () => {
            const agent = node.dataset.agent;
            console.log('Graph node clicked:', agent);
        });
    });
}

function setAgentWorking(agent, action) {
    // Graph node
    const node = document.querySelector(`.graph-node[data-agent="${agent}"]`);
    if (node) node.classList.add('active');

    // Right rail card
    const card = document.querySelector(`.agent-status-card[data-agent="${agent}"]`);
    if (card) {
        card.classList.add('active');
        const dots = card.querySelector('.thinking-dots');
        const text = card.querySelector('.status-text');
        if (dots) dots.classList.remove('hidden');
        if (text) text.textContent = action ? action.slice(0, 24) + '…' : 'Thinking…';
    }
}

function setAgentIdle(agent) {
    // Graph node
    const node = document.querySelector(`.graph-node[data-agent="${agent}"]`);
    if (node) node.classList.remove('active');

    // Right rail card
    const card = document.querySelector(`.agent-status-card[data-agent="${agent}"]`);
    if (card) {
        card.classList.remove('active');
        const dots = card.querySelector('.thinking-dots');
        const text = card.querySelector('.status-text');
        if (dots) dots.classList.add('hidden');
        if (text) {
            text.textContent = 'Done ✓';
            setTimeout(() => { if (text) text.textContent = 'Ready'; }, 3000);
        }
    }
}

function flashMnemo() {
    const card = document.querySelector('.agent-status-card[data-agent="mnemo"]');
    if (!card) return;
    const text = card.querySelector('.status-text');
    card.classList.add('active');
    card.style.setProperty('--agent-color', '#9334E6');
    if (text) text.textContent = 'Memory saved ✓';
    setTimeout(() => {
        card.classList.remove('active');
        if (text) text.textContent = 'Ready';
    }, 3000);
}

// ─────────────────────────────────────────────
// RESPONSE — center panel
// ─────────────────────────────────────────────

function appendUserMessage(text) {
    const content = document.getElementById('response-content');
    const el = document.createElement('div');
    el.className = 'response-block user-message';
    el.innerHTML = `<div class="response-text user-text">${escHtml(text)}</div>`;
    content.appendChild(el);
    scrollResponse();
}

function appendAgentResponse(agent, agentLabel, markdown) {
    const content = document.getElementById('response-content');
    const meta = AGENT_META[agent] || { color: '#4285F4', bg: '#E8F0FE' };

    const el = document.createElement('div');
    el.className = 'response-block agent-message';
    el.innerHTML = `
        <span class="agent-tag" style="background:${meta.bg};color:${meta.color}">${escHtml(agentLabel)}</span>
        <div class="response-text">${renderMarkdown(markdown)}</div>
    `;
    content.appendChild(el);
    scrollResponse();
}

function appendErrorMessage(msg) {
    const content = document.getElementById('response-content');
    const el = document.createElement('div');
    el.className = 'response-block error-message';
    el.innerHTML = `<div class="response-text" style="color:#EA4335">⚠ ${escHtml(msg)}</div>`;
    content.appendChild(el);
    scrollResponse();
}

function scrollResponse() {
    const area = document.getElementById('response-area');
    if (area) area.scrollTop = area.scrollHeight;
}

// ─────────────────────────────────────────────
// SUGGESTIONS
// ─────────────────────────────────────────────

function showSuggestions(suggestions) {
    const container = document.getElementById('suggestions');
    const chips = document.getElementById('suggestion-chips');
    if (!container || !chips) return;

    chips.innerHTML = suggestions.map(s => `
        <button class="suggestion-chip" onclick="handleSuggestion(this, '${escAttr(s.prompt)}')">${escHtml(s.label)}</button>
    `).join('');

    container.classList.remove('hidden');
}

function handleSuggestion(btn, prompt) {
    const input = document.getElementById('chat-input');
    if (input) {
        input.value = prompt;
        input.focus();
    }
    sendMessage();
}

// ─────────────────────────────────────────────
// MCP DETAIL DRAWER
// ─────────────────────────────────────────────

function openDrawer(agent, agentLabel, tool, toolLabel) {
    const overlay = document.getElementById('drawer-overlay');
    const drawer  = document.getElementById('mcp-drawer');
    const title   = document.getElementById('drawer-title');
    const content = document.getElementById('drawer-content');

    if (!overlay || !drawer) return;

    const meta   = AGENT_META[agent] || { color: '#4285F4' };
    const cardKey = `${agent}:${tool}`;
    const detail  = currentTraceDetail[cardKey];

    title.innerHTML = `
        <span style="color:${meta.color}">${escHtml(agentLabel)}</span>
        <span style="color:#5f6368;font-weight:400"> · ${escHtml(toolLabel)}</span>
    `;

    if (detail) {
        content.innerHTML = renderDrawerDetail(detail);
    } else {
        // Fallback: try to fetch from backend
        fetchAndRenderDetail(content, agent, tool);
    }

    overlay.classList.remove('hidden');
    drawer.classList.remove('hidden');
}

function renderDrawerDetail(detail) {
    let html = '';

    // Steps
    if (detail.steps && detail.steps.length > 0) {
        html += `<div class="drawer-section"><h4>What ${detail.agent_display_name} did</h4>`;
        detail.steps.forEach(step => {
            const tagColor = { success: '#34A853', info: '#1a73e8', warning: '#EA4335', error: '#EA4335' }[step.tag_type] || '#5f6368';
            html += `
                <div class="drawer-step">
                    <div class="step-title">${escHtml(step.title)}</div>
                    <div class="step-desc">${escHtml(step.description)}</div>
                    ${step.result_summary ? `<div class="step-result">${escHtml(step.result_summary)}</div>` : ''}
                    ${step.tag ? `<span class="step-tag" style="background:${tagColor}20;color:${tagColor}">${escHtml(step.tag)}</span>` : ''}
                </div>
            `;
        });
        html += '</div>';
    }

    // State writes
    if (detail.session_state_writes && detail.session_state_writes.length > 0) {
        html += `<div class="drawer-section"><h4>Data passed to next agent</h4>`;
        detail.session_state_writes.forEach(w => {
            html += `
                <div class="drawer-step">
                    <div class="step-title" style="font-family:monospace;font-size:12px">${escHtml(w.key)}</div>
                    <div class="step-desc">${escHtml(w.value_summary)}</div>
                    ${w.read_by ? `<div class="step-result">Read by: ${w.read_by.join(', ')}</div>` : ''}
                </div>
            `;
        });
        html += '</div>';
    }

    // Conflicts resolved
    if (detail.conflicts_resolved && detail.conflicts_resolved.length > 0) {
        html += `<div class="drawer-section"><h4>Conflicts resolved</h4>`;
        detail.conflicts_resolved.forEach(c => {
            html += `
                <div class="drawer-step">
                    <div class="step-title" style="color:#EA4335">⚠ ${escHtml(c.conflict)}</div>
                    <div class="step-desc" style="color:#34A853">✓ ${escHtml(c.resolution)}</div>
                </div>
            `;
        });
        html += '</div>';
    }

    // Memory writes
    if (detail.memory_writes && detail.memory_writes.length > 0) {
        html += `<div class="drawer-section"><h4>Saved to memory (Mnemo)</h4>`;
        detail.memory_writes.forEach(m => {
            html += `
                <div class="drawer-step">
                    <span class="step-tag" style="background:#F3E8FD;color:#9334E6">${escHtml(m.layer_display)}</span>
                    <div class="step-desc" style="margin-top:6px">${escHtml(m.content)}</div>
                    ${m.importance_score ? `<div class="step-result">Importance: ${m.importance_score}/5</div>` : ''}
                </div>
            `;
        });
        html += '</div>';
    }

    // Raw output
    if (detail.raw_output_summary) {
        html += `
            <div class="drawer-section">
                <h4>Raw output summary</h4>
                <div class="drawer-step"><div class="step-desc">${escHtml(detail.raw_output_summary)}</div></div>
            </div>
        `;
    }

    if (!html) {
        html = '<div class="drawer-section"><p style="color:#5f6368;font-size:14px">No detail available for this tool call.</p></div>';
    }

    return html;
}

async function fetchAndRenderDetail(contentEl, agent, tool) {
    contentEl.innerHTML = '<p style="padding:16px;color:#5f6368">Loading detail…</p>';
    try {
        const resp = await fetch(`${API_BASE}/mcp-detail/${currentSessionId}/${tool}`);
        if (resp.ok) {
            const detail = await resp.json();
            contentEl.innerHTML = renderDrawerDetail(detail);
        } else {
            contentEl.innerHTML = '<div class="drawer-section"><p style="color:#5f6368;font-size:14px">No detail available. Run a workflow first.</p></div>';
        }
    } catch {
        contentEl.innerHTML = '<div class="drawer-section"><p style="color:#EA4335;font-size:14px">Could not load detail.</p></div>';
    }
}

function closeDrawer() {
    document.getElementById('drawer-overlay')?.classList.add('hidden');
    document.getElementById('mcp-drawer')?.classList.add('hidden');
}

// ─────────────────────────────────────────────
// GRAPH
// ─────────────────────────────────────────────

function initGraph() {
    document.querySelectorAll('.graph-node').forEach(node => {
        node.style.cursor = 'pointer';
    });
}

// ─────────────────────────────────────────────
// MARKDOWN RENDERER (minimal, safe)
// ─────────────────────────────────────────────

function renderMarkdown(text) {
    if (!text) return '';
    return text
        // Headings
        .replace(/^## (.+)$/gm, '<h3 class="response-heading">$1</h3>')
        .replace(/^### (.+)$/gm, '<h4 class="response-subheading">$1</h4>')
        // Bold
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        // Bullet list
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
        // Numbered list
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        // Inline code
        .replace(/`(.+?)`/g, '<code class="inline-code">$1</code>')
        // Paragraphs (double newline)
        .replace(/\n\n/g, '</p><p class="response-para">')
        // Line breaks
        .replace(/\n/g, '<br>');
}

// ─────────────────────────────────────────────
// UTILITIES
// ─────────────────────────────────────────────

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escAttr(str) {
    if (!str) return '';
    return String(str).replace(/'/g, '&#39;').replace(/"/g, '&quot;');
}

// ─────────────────────────────────────────────
// GLOBAL EXPORTS
// ─────────────────────────────────────────────

window.sendMessage     = sendMessage;
window.closeDrawer     = closeDrawer;
window.handleSuggestion = handleSuggestion;
