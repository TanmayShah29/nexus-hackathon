/**
 * agents.js — Agent roster interactions, animations, and utilities
 */

// Agent data (mirrored from index.html for standalone use)
const AGENTS_DATA = [
    {
        name: "nexus_core",
        display_name: "NEXUS Core",
        role: "Orchestrator",
        tagline: "Your Personal Coordinator",
        personality: "Silent and precise. Routes every intent to the right specialist.",
        color: "#4285F4",
        color_bg: "#E8F0FE",
        owned_mcps: ["all"],
        capabilities: ["Classifies user intent", "Coordinates all 9 specialist agents", "Retains full context"],
        status: "idle"
    },
    {
        name: "atlas",
        display_name: "Atlas",
        role: "Research agent",
        tagline: "Curious Scholar",
        personality: "Endlessly curious. Always cites sources.",
        color: "#1a73e8",
        color_bg: "#E8F0FE",
        owned_mcps: ["tavily_search", "brave_search", "wikipedia", "youtube_transcript", "web_scraper"],
        capabilities: ["Web search via Tavily and Brave", "Wikipedia retrieval", "YouTube transcript extraction", "Website scraping"],
        status: "idle"
    },
    {
        name: "chrono",
        display_name: "Chrono",
        role: "Scheduler agent",
        tagline: "Efficient Timekeeper",
        personality: "Punctual and assertive. Hates calendar conflicts.",
        color: "#EA4335",
        color_bg: "#FCE8E6",
        owned_mcps: ["google_calendar", "google_maps", "openweathermap"],
        capabilities: ["Calendar event management", "Scheduling conflict resolution", "Travel time calculation"],
        status: "idle"
    },
    {
        name: "sage",
        display_name: "Sage",
        role: "Notes agent",
        tagline: "Notes Librarian",
        personality: "Quiet and organised. Loves categories and tags.",
        color: "#34A853",
        color_bg: "#E6F4EA",
        owned_mcps: ["notion", "filesystem", "google_drive", "firestore"],
        capabilities: ["Note storage and retrieval", "Semantic search", "Document organization"],
        status: "idle"
    },
    {
        name: "mnemo",
        display_name: "Mnemo",
        role: "Memory agent",
        tagline: "Silent Watcher",
        personality: "Never speaks unless asked. Always present.",
        color: "#9334E6",
        color_bg: "#F3E8FD",
        owned_mcps: ["firestore", "firestore_vector"],
        capabilities: ["Working memory", "Daily activity log", "Long-term profile", "Semantic search"],
        status: "idle"
    },
    {
        name: "flux",
        display_name: "Flux",
        role: "Briefing agent",
        tagline: "Empathetic Peer",
        personality: "Reads between the lines. Adjusts tone based on mood.",
        color: "#00BCD4",
        color_bg: "#E0F7FA",
        owned_mcps: ["openweathermap", "firestore"],
        capabilities: ["Context synthesis", "Mood detection", "Daily briefings", "Proactive suggestions"],
        status: "idle"
    },
    {
        name: "dash",
        display_name: "Dash",
        role: "Tasks agent",
        tagline: "No-Nonsense Executor",
        personality: "Direct and energetic. Loves ticking things off.",
        color: "#FBBC04",
        color_bg: "#FEF7E0",
        owned_mcps: ["firestore", "notion"],
        capabilities: ["Task CRUD operations", "Auto-prioritization", "Goal decomposition"],
        status: "idle"
    },
    {
        name: "quest",
        display_name: "Quest",
        role: "Goals agent",
        tagline: "Goal Strategist",
        personality: "Thinks in 90-day horizons.",
        color: "#FF6D00",
        color_bg: "#FFF3E0",
        owned_mcps: ["firestore", "notion"],
        capabilities: ["Goal decomposition", "Milestone tracking", "Roadmap building"],
        status: "idle"
    },
    {
        name: "lumen",
        display_name: "Lumen",
        role: "Analytics agent",
        tagline: "Blunt Analyst",
        personality: "Only trusts numbers.",
        color: "#0F9D58",
        color_bg: "#E6F4EA",
        owned_mcps: ["firestore", "python_executor"],
        capabilities: ["Productivity reports", "Completion analysis", "Pattern detection"],
        status: "idle"
    },
    {
        name: "forge",
        display_name: "Forge",
        role: "Workflow engine",
        tagline: "No-Nonsense Execution",
        personality: "Methodical. Builds the plan before acting.",
        color: "#C2185B",
        color_bg: "#FCE4EC",
        owned_mcps: ["all"],
        capabilities: ["SequentialAgent pipelines", "ParallelAgent execution", "LoopAgent control"],
        status: "idle"
    }
];

// Initialize the page
document.addEventListener('DOMContentLoaded', () => {
    initScrollAnimations();
    initRosterScroll();
    initAgentInteractions();
});

/**
 * Animate elements when they come into view
 */
function initScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-in');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observe hero content
    const heroContent = document.querySelector('.hero-content');
    if (heroContent) {
        heroContent.style.opacity = '0';
        heroContent.style.transform = 'translateY(30px)';
        observer.observe(heroContent);
    }

    // Observe agent cards
    document.querySelectorAll('.agent-card').forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transitionDelay = `${index * 100}ms`;
        observer.observe(card);
    });
}

/**
 * Add scroll navigation to roster
 */
function initRosterScroll() {
    const roster = document.getElementById('agent-roster');
    if (!roster) return;

    let isDown = false;
    let startX;
    let scrollLeft;

    roster.addEventListener('mousedown', (e) => {
        isDown = true;
        roster.style.cursor = 'grabbing';
        startX = e.pageX - roster.offsetLeft;
        scrollLeft = roster.scrollLeft;
    });

    roster.addEventListener('mouseleave', () => {
        isDown = false;
        roster.style.cursor = 'grab';
    });

    roster.addEventListener('mouseup', () => {
        isDown = false;
        roster.style.cursor = 'grab';
    });

    roster.addEventListener('mousemove', (e) => {
        if (!isDown) return;
        e.preventDefault();
        const x = e.pageX - roster.offsetLeft;
        const walk = (x - startX) * 2;
        roster.scrollLeft = scrollLeft - walk;
    });

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (e.key === 'ArrowLeft') {
            roster.scrollBy({ left: -340, behavior: 'smooth' });
        } else if (e.key === 'ArrowRight') {
            roster.scrollBy({ left: 340, behavior: 'smooth' });
        }
    });
}

/**
 * Handle agent card interactions
 */
function initAgentInteractions() {
    const cards = document.querySelectorAll('.agent-card');
    
    cards.forEach(card => {
        card.addEventListener('click', () => {
            const agentName = card.dataset.agent;
            toggleAgentDetails(agentName, card);
        });
        
        // Hover effects
        card.addEventListener('mouseenter', () => {
            card.style.zIndex = '10';
        });
        
        card.addEventListener('mouseleave', () => {
            card.style.zIndex = '1';
        });
    });
}

/**
 * Toggle agent details expansion
 */
function toggleAgentDetails(agentName, card) {
    const capabilities = card.querySelector('.agent-capabilities');
    if (!capabilities) return;
    
    const isHidden = capabilities.classList.contains('hidden');
    
    if (isHidden) {
        // Close all other cards
        document.querySelectorAll('.agent-capabilities').forEach(cap => {
            if (!cap.classList.contains('hidden')) {
                cap.classList.add('hidden');
            }
        });
        // Open this one
        capabilities.classList.remove('hidden');
        card.classList.add('expanded');
    } else {
        capabilities.classList.add('hidden');
        card.classList.remove('expanded');
    }
}

/**
 * Get agent by name
 */
function getAgent(name) {
    return AGENTS_DATA.find(a => a.name === name);
}

/**
 * Format MCP tool name for display
 */
function formatMcpName(mcp) {
    return mcp.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

/**
 * Export for use in other modules
 */
window.AGENTS_DATA = AGENTS_DATA;
window.getAgent = getAgent;
window.formatMcpName = formatMcpName;
window.toggleAgentDetails = toggleAgentDetails;
