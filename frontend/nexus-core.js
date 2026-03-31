/* nexus-core.js — Shared NEXUS client
 *
 * Single source of truth for:
 *  - Session ID (tab-scoped via sessionStorage)
 *  - Supabase client init
 *  - SSE streaming to /chat
 *  - getHealth() helper used by memory.html
 *  - Agent color map for D3 graphs
 */

const API_BASE =
    window.NEXUS_CONFIG?.API_BASE ||
    document.currentScript?.dataset?.apiBase ||
    'http://localhost:8000';

const NEXUS_API_TOKEN =
    window.NEXUS_CONFIG?.API_TOKEN || 'nexus_secret';

const SUPABASE_URL = 'https://vcggjnrhwmvtimzhffpq.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZjZ2dqbnJod212dGltemhmZnBxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ4ODU2NTMsImV4cCI6MjA5MDQ2MTY1M30.XG93I6LJtyodKpkrjD6Lg1NCmFzbBphqXeIjk3-yfbI';

const NEXUS_CORE = {
    /* Tab-scoped session — each tab has its own conversation */
    sessionId: (function () {
        let id = sessionStorage.getItem('nexus_session_id');
        if (!id) {
            id = 'nexus-' + Math.random().toString(36).slice(2, 11);
            sessionStorage.setItem('nexus_session_id', id);
        }
        return id;
    })(),

    isStreaming: false,
    isReady: false,
    supabase: null,

    /* Agent → color map, used by D3 graphs and trace cards */
    AGENT_COLORS: {
        orchestrator: '#4285F4',
        atlas:        '#1a73e8',
        chrono:       '#EA4335',
        sage:         '#34A853',
        mnemo:        '#9334E6',
        tasks:        '#AB47BC',
        goals:        '#F9AB00',
        briefing:     '#26A69A',
        analytics:    '#00BCD4',
        workflow:     '#FF7043',
        booster:      '#FFFFFF',
        system:       '#888888',
    },

    init: async function () {
        await new Promise((resolve) => {
            const s = document.createElement('script');
            s.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
            s.onload = () => {
                try {
                    this.supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
                } catch (e) {
                    console.warn('NEXUS: Supabase init failed:', e);
                }
                resolve();
            };
            s.onerror = () => {
                console.warn('NEXUS: Supabase CDN failed — memory features disabled.');
                resolve();
            };
            document.head.appendChild(s);
        });

        this.isReady = true;
        console.log(`NEXUS ready | session=${this.sessionId} | api=${API_BASE}`);
        document.dispatchEvent(new CustomEvent('nexus:ready'));
    },

    whenReady: function (cb) {
        if (this.isReady) cb();
        else document.addEventListener('nexus:ready', cb, { once: true });
    },

    /* Health check — used by memory.html */
    getHealth: async function () {
        try {
            const res = await fetch(`${API_BASE}/health`, {
                headers: { 'Authorization': `Bearer ${NEXUS_API_TOKEN}` }
            });
            if (!res.ok) return null;
            return await res.json();
        } catch (_) {
            return null;
        }
    },

    /* SSE streaming to /chat */
    executeFlow: async function (prompt, onEvent) {
        if (!prompt.trim() || this.isStreaming) return;
        this.isStreaming = true;

        try {
            const res = await fetch(`${API_BASE}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${NEXUS_API_TOKEN}`,
                },
                body: JSON.stringify({
                    prompt,
                    user_id: 'default_user',
                    session_id: this.sessionId,
                }),
            });

            if (!res.ok) {
                let msg = `HTTP ${res.status}`;
                try { const b = await res.json(); msg = b.error || b.detail || msg; } catch (_) {}
                onEvent({ type: 'error', error: msg });
                return;
            }

            const reader = res.body.getReader();
            const dec = new TextDecoder();
            let buf = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buf += dec.decode(value, { stream: true });
                const lines = buf.split('\n');
                buf = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const raw = line.slice(6).trim();
                    if (!raw || raw === '[DONE]') continue;
                    try { onEvent(JSON.parse(raw)); }
                    catch (_) { console.warn('NEXUS: bad SSE JSON:', raw); }
                }
            }
        } catch (e) {
            onEvent({ type: 'error', error: e.message });
        } finally {
            this.isStreaming = false;
        }
    },
};

NEXUS_CORE.init();
