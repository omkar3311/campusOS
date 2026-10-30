/**
 * CampusOS AI - Production Enterprise SaaS Helpdesk Client
 * ChatGPT-Style Streaming & Multi-Session Conversation Engine
 */

const API_BASE = window.location.pathname.replace(/\/$/, "");

// ============================================================================
// STATE STORE
// ============================================================================

const State = {
    activeSessionId: null,
    conversations: {}, // { [id]: { id, title, createdAt, updatedAt, messages: [] } }
    isStreaming: false,
    stopStreamingRequested: false,
    theme: localStorage.getItem('campusos_theme') || 'light'
};

// ============================================================================
// DOM ELEMENTS
// ============================================================================

const DOM = {
    // Sidebar
    sidebar: document.getElementById('sidebar'),
    sidebarCollapseBtn: document.getElementById('sidebarCollapseBtn'),
    mobileMenuBtn: document.getElementById('mobileMenuBtn'),
    newChatBtn: document.getElementById('newChatBtn'),
    searchHistoryInput: document.getElementById('searchHistoryInput'),
    historyContainer: document.getElementById('historyContainer'),
    groupToday: document.getElementById('groupToday'),
    itemsToday: document.getElementById('itemsToday'),
    groupYesterday: document.getElementById('groupYesterday'),
    itemsYesterday: document.getElementById('itemsYesterday'),
    groupPastWeek: document.getElementById('groupPastWeek'),
    itemsPastWeek: document.getElementById('itemsPastWeek'),
    groupOlder: document.getElementById('groupOlder'),
    itemsOlder: document.getElementById('itemsOlder'),
    directoryBtnTrigger: document.getElementById('directoryBtnTrigger'),

    // Topbar & Modals
    activeSessionHeaderTitle: document.getElementById('activeSessionHeaderTitle'),
    renameSessionBtn: document.getElementById('renameSessionBtn'),
    directoryBtn: document.getElementById('directoryBtn'),
    exportChatBtn: document.getElementById('exportChatBtn'),
    themeToggleBtn: document.getElementById('themeToggleBtn'),
    directoryModal: document.getElementById('directoryModal'),
    renameModal: document.getElementById('renameModal'),
    renameInput: document.getElementById('renameInput'),
    saveRenameBtn: document.getElementById('saveRenameBtn'),

    // Chat Area
    chatViewport: document.getElementById('chatViewport'),
    chatHero: document.getElementById('chatHero'),
    messagesList: document.getElementById('messagesList'),
    thinkingRow: document.getElementById('thinkingRow'),
    scrollBottomBtn: document.getElementById('scrollBottomBtn'),
    stopGeneratingWrap: document.getElementById('stopGeneratingWrap'),
    stopGeneratingBtn: document.getElementById('stopGeneratingBtn'),
    promptCards: document.querySelectorAll('.prompt-card'),

    // Input Area
    chatInput: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendBtn'),
    charCount: document.getElementById('charCount'),
    toastStack: document.getElementById('toastStack')
};

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    setupReturnNavigation();
    initTheme();
    loadConversations();
    initEventListeners();
});

// Dynamic Return Navigation & CampusOS Header Sync
function setupReturnNavigation() {
    const urlParams = new URLSearchParams(window.location.search);
    const explicitReturn = urlParams.get('return_to') || urlParams.get('back') || urlParams.get('redirect');
    if (explicitReturn) {
        sessionStorage.setItem('campusos_return_url', explicitReturn);
    }
    const savedReturn = sessionStorage.getItem('campusos_return_url');
    const role = urlParams.get('role') || 'student';
    const name = urlParams.get('name') || (role === 'hod' ? 'HOD Admin' : (role === 'teacher' ? 'Faculty' : 'Student'));
    
    let returnUrl = explicitReturn || savedReturn;
    if (!returnUrl) {
        if (role === 'hod') returnUrl = '/main_dashboard';
        else if (role === 'teacher') returnUrl = '/class_dashboard';
        else if (role === 'student') returnUrl = '/student';
        else if (document.referrer && !document.referrer.includes('/agent/')) returnUrl = document.referrer;
        else returnUrl = '/main_dashboard';
    }

    let returnLabel = 'Portal';
    if (role === 'hod') returnLabel = 'HOD Dashboard';
    else if (role === 'teacher') returnLabel = 'Class Dashboard';
    else if (role === 'student') returnLabel = 'Student Portal';

    const backBtn = document.getElementById('backToPortalBtn');
    const backText = document.getElementById('backToPortalText');
    if (backBtn) {
        backBtn.href = returnUrl;
        backBtn.onclick = (e) => {
            e.preventDefault();
            window.location.href = returnUrl;
        };
    }
    if (backText) {
        backText.textContent = returnLabel;
    }

    // Sync User Badge in Topbar
    const displayNameEl = document.getElementById('userDisplayName');
    const roleTagEl = document.getElementById('userRoleTag');
    if (displayNameEl) {
        displayNameEl.textContent = name;
    }
    if (roleTagEl) {
        roleTagEl.textContent = role.toUpperCase();
        if (role === 'hod') roleTagEl.style.background = 'linear-gradient(135deg, #f59e0b, #ef4444)';
        else if (role === 'teacher') roleTagEl.style.background = 'linear-gradient(135deg, #10b981, #06b6d4)';
        else roleTagEl.style.background = 'linear-gradient(135deg, #2563eb, #38bdf8)';
    }

    // Preserve query parameters on Agent Nav Tabs
    const query = window.location.search;
    if (query) {
        document.querySelectorAll('.agent-nav-link').forEach(link => {
            const base = link.getAttribute('href').split('?')[0];
            link.setAttribute('href', base + query);
        });
    }
}

function initTheme() {
    document.documentElement.setAttribute('data-theme', State.theme);
}

function toggleTheme() {
    State.theme = State.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', State.theme);
    localStorage.setItem('campusos_theme', State.theme);
    showToast(`Switched to ${State.theme} theme`, 'info');
}

// ============================================================================
// CONVERSATIONS & SESSION MANAGEMENT (Temporary Per-Visit Sessions)
// ============================================================================

function loadConversations() {
    // Clear any legacy persistent storage so chats reset on refresh
    try {
        localStorage.removeItem('campusos_conversations');
        localStorage.removeItem('campusos_active_session_id');
    } catch (e) {}

    // Initialize with a fresh, isolated temporary session
    State.conversations = {};
    createNewConversation(false);
}

function saveConversations() {
    // Conversations remain in-memory for the current tab lifecycle only.
    // Refreshing the page automatically gives a clean, fresh new consultation.
}

function createNewConversation(switchAndNotify = true) {
    const id = `session_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    const now = new Date().toISOString();

    State.conversations[id] = {
        id: id,
        title: 'New Consultation',
        createdAt: now,
        updatedAt: now,
        messages: []
    };

    State.activeSessionId = id;
    renderHistorySidebar();
    renderCurrentConversation();

    if (switchAndNotify) {
        DOM.chatInput.focus();
        showToast('Started new consultation', 'info');
    }
}

function switchConversation(sessionId) {
    if (State.isStreaming) return;
    if (!State.conversations[sessionId]) return;

    State.activeSessionId = sessionId;
    renderHistorySidebar();
    renderCurrentConversation();

    // Close mobile sidebar if open
    DOM.sidebar.classList.remove('mobile-open');
}

function deleteConversation(sessionId, event) {
    if (event) event.stopPropagation();

    delete State.conversations[sessionId];
    const remainingIds = Object.keys(State.conversations);

    if (remainingIds.length === 0) {
        createNewConversation(false);
    } else if (State.activeSessionId === sessionId) {
        State.activeSessionId = remainingIds[0];
    }

    renderHistorySidebar();
    renderCurrentConversation();
    showToast('Conversation removed', 'info');
}

function renameConversation(sessionId, newTitle) {
    if (!newTitle.trim()) return;
    if (State.conversations[sessionId]) {
        State.conversations[sessionId].title = newTitle.trim();
        State.conversations[sessionId].updatedAt = new Date().toISOString();
        saveConversations();
        renderHistorySidebar();
        updateTopHeader();
        showToast('Conversation renamed', 'success');
    }
}

// ============================================================================
// SIDEBAR HISTORY RENDERING (Grouped by Date)
// ============================================================================

function renderHistorySidebar() {
    const query = DOM.searchHistoryInput.value.trim().toLowerCase();

    DOM.itemsToday.innerHTML = '';
    DOM.itemsYesterday.innerHTML = '';
    DOM.itemsPastWeek.innerHTML = '';
    DOM.itemsOlder.innerHTML = '';

    const todayDate = new Date();
    todayDate.setHours(0, 0, 0, 0);

    const yesterdayDate = new Date(todayDate);
    yesterdayDate.setDate(yesterdayDate.getDate() - 1);

    const weekAgoDate = new Date(todayDate);
    weekAgoDate.setDate(weekAgoDate.getDate() - 7);

    // Sort descending by updatedAt
    const sessions = Object.values(State.conversations).sort((a, b) => {
        return new Date(b.updatedAt || b.createdAt) - new Date(a.updatedAt || a.createdAt);
    });

    let countToday = 0, countYesterday = 0, countWeek = 0, countOlder = 0;

    sessions.forEach(sess => {
        if (query && !sess.title.toLowerCase().includes(query)) return;

        const updated = new Date(sess.updatedAt || sess.createdAt);
        const itemEl = createHistoryItemElement(sess);

        if (updated >= todayDate) {
            DOM.itemsToday.appendChild(itemEl);
            countToday++;
        } else if (updated >= yesterdayDate) {
            DOM.itemsYesterday.appendChild(itemEl);
            countYesterday++;
        } else if (updated >= weekAgoDate) {
            DOM.itemsPastWeek.appendChild(itemEl);
            countWeek++;
        } else {
            DOM.itemsOlder.appendChild(itemEl);
            countOlder++;
        }
    });

    DOM.groupToday.classList.toggle('has-items', countToday > 0);
    DOM.groupYesterday.classList.toggle('has-items', countYesterday > 0);
    DOM.groupPastWeek.classList.toggle('has-items', countWeek > 0);
    DOM.groupOlder.classList.toggle('has-items', countOlder > 0);

    updateTopHeader();
}

function createHistoryItemElement(sess) {
    const el = document.createElement('div');
    const isActive = sess.id === State.activeSessionId;
    el.className = `history-item ${isActive ? 'active' : ''}`;
    el.onclick = () => switchConversation(sess.id);

    el.innerHTML = `
        <span class="history-title" title="${escapeHtml(sess.title)}">${escapeHtml(sess.title)}</span>
        <div class="history-actions">
            <button class="item-action-btn edit-btn" title="Rename conversation">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20h9"></path>
                    <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                </svg>
            </button>
            <button class="item-action-btn del-btn" title="Delete conversation">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
            </button>
        </div>
    `;

    const editBtn = el.querySelector('.edit-btn');
    editBtn.onclick = (e) => {
        e.stopPropagation();
        openRenameModal(sess.id, sess.title);
    };

    const delBtn = el.querySelector('.del-btn');
    delBtn.onclick = (e) => deleteConversation(sess.id, e);

    return el;
}

function updateTopHeader() {
    const active = State.conversations[State.activeSessionId];
    if (active) {
        DOM.activeSessionHeaderTitle.textContent = active.title;
    }
}

// ============================================================================
// CHAT RENDERING
// ============================================================================

function renderCurrentConversation() {
    const active = State.conversations[State.activeSessionId];
    if (!active || !active.messages || active.messages.length === 0) {
        DOM.chatHero.style.display = 'flex';
        DOM.messagesList.innerHTML = '';
        return;
    }

    DOM.chatHero.style.display = 'none';
    DOM.messagesList.innerHTML = '';

    active.messages.forEach((msg, idx) => {
        renderMessageRow(msg, idx, false);
    });

    scrollToBottom();
}

function renderMessageRow(msg, idx, isNew = true) {
    const isUser = msg.role === 'user';
    const isGuardrail = msg.status === 'guardrail_blocked';

    const row = document.createElement('div');
    row.className = `msg-row ${isUser ? 'user-row' : 'agent-row'} ${isGuardrail ? 'guardrail-row' : ''}`;
    row.id = `msg_${idx}`;

    let parsedHtml = '';
    if (isUser) {
        parsedHtml = escapeHtml(msg.content);
    } else if (window.marked) {
        try {
            parsedHtml = marked.parse(msg.content);
        } catch (e) {
            parsedHtml = escapeHtml(msg.content);
        }
    } else {
        parsedHtml = escapeHtml(msg.content);
    }

    let sourcesHtml = '';
    if (!isUser && msg.sources && msg.sources.length > 0) {
        const pills = msg.sources.map(s => `<span class="source-pill">📄 ${escapeHtml(s)}</span>`).join('');
        sourcesHtml = `
            <div class="sources-card">
                <button class="sources-header-btn" onclick="toggleSources(this)">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                    <span>${msg.sources.length} Official Knowledge Sources</span>
                </button>
                <div class="sources-chips-wrap" style="display: none;">
                    ${pills}
                </div>
            </div>
        `;
    }

    let guardrailTag = '';
    if (isGuardrail) {
        guardrailTag = `
            <div class="guardrail-tag">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"></polygon>
                    <line x1="12" y1="8" x2="12" y2="12"></line>
                    <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <span>Safety Guardrail Active</span>
            </div>
        `;
    }

    row.innerHTML = `
        <div class="${isUser ? 'user-bubble-avatar' : 'agent-avatar'}">
            ${isUser ? 'You' : `
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
            `}
        </div>
        <div class="msg-bubble-wrap">
            <div class="msg-bubble">
                ${guardrailTag}
                <div class="msg-content">${parsedHtml}</div>
                ${sourcesHtml}
            </div>
            ${!isUser ? `
                <div class="msg-action-bar">
                    <span>${msg.latency_ms ? `${msg.latency_ms}ms` : 'CampusOS Engine'}</span>
                    <div class="action-btns-group">
                        <button class="action-tool-btn" onclick="copyMessage(this)" title="Copy answer">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                            </svg>
                            <span>Copy</span>
                        </button>
                        <button class="action-tool-btn" onclick="speakMessage(this)" title="Read answer">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
                                <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
                            </svg>
                            <span>Speak</span>
                        </button>
                    </div>
                </div>
            ` : ''}
        </div>
    `;

    DOM.messagesList.appendChild(row);
    return row;
}

function toggleSources(btn) {
    const wrap = btn.nextElementSibling;
    const isHidden = wrap.style.display === 'none';
    wrap.style.display = isHidden ? 'flex' : 'none';
    btn.querySelector('svg').style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0)';
}

function copyMessage(btn) {
    const wrap = btn.closest('.msg-bubble-wrap');
    const content = wrap.querySelector('.msg-content').innerText;
    navigator.clipboard.writeText(content).then(() => {
        const span = btn.querySelector('span');
        const prev = span.textContent;
        span.textContent = 'Copied!';
        setTimeout(() => span.textContent = prev, 2000);
    });
}

function speakMessage(btn) {
    if (!('speechSynthesis' in window)) {
        showToast('Text-to-speech not supported in browser', 'warning');
        return;
    }
    const wrap = btn.closest('.msg-bubble-wrap');
    const content = wrap.querySelector('.msg-content').innerText;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(content);
    window.speechSynthesis.speak(utterance);
}

// ============================================================================
// CHATGPT-STYLE FRONTEND STREAMING ENGINE
// ============================================================================

async function handleSendMessage() {
    const text = DOM.chatInput.value.trim();
    if (!text || State.isStreaming) return;

    // Reset input
    DOM.chatInput.value = '';
    DOM.chatInput.style.height = 'auto';
    DOM.charCount.textContent = '0/3000';
    DOM.chatHero.style.display = 'none';

    const active = State.conversations[State.activeSessionId];
    const now = new Date().toISOString();

    // 1. Add User Message
    const userMsg = {
        role: 'user',
        content: text,
        timestamp: now
    };
    active.messages.push(userMsg);
    active.updatedAt = now;

    // Auto-title conversation on first message
    if (active.messages.length === 1) {
        active.title = text.slice(0, 36) + (text.length > 36 ? '...' : '');
        updateTopHeader();
    }

    saveConversations();
    renderHistorySidebar();
    renderMessageRow(userMsg, active.messages.length - 1);
    scrollToBottom();

    // 2. Start Thinking Placeholder
    State.isStreaming = true;
    State.stopStreamingRequested = false;
    DOM.thinkingRow.style.display = 'flex';
    DOM.sendBtn.disabled = true;
    DOM.stopGeneratingWrap.style.display = 'flex';
    scrollToBottom();

    try {
        // Fetch full answer from backend
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: text,
                session_id: State.activeSessionId
            })
        });

        const data = await response.json();
        DOM.thinkingRow.style.display = 'none';

        // 3. Stream typing in frontend (ChatGPT Style)
        await streamResponseTyping(data.answer, data.sources, data.latency_ms, data.status);

    } catch (err) {
        console.error('Chat error:', err);
        DOM.thinkingRow.style.display = 'none';
        State.isStreaming = false;
        DOM.sendBtn.disabled = false;
        DOM.stopGeneratingWrap.style.display = 'none';
        showToast('Network error while querying helpdesk', 'error');
    }
}

async function streamResponseTyping(fullText, sources, latency_ms, status) {
    const active = State.conversations[State.activeSessionId];
    const isGuardrail = status === 'guardrail_blocked';

    // Create placeholder row in DOM
    const row = document.createElement('div');
    row.className = `msg-row agent-row ${isGuardrail ? 'guardrail-row' : ''}`;
    row.innerHTML = `
        <div class="agent-avatar">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
            </svg>
        </div>
        <div class="msg-bubble-wrap">
            <div class="msg-bubble">
                <div class="msg-content"><span class="typing-cursor"></span></div>
            </div>
        </div>
    `;
    DOM.messagesList.appendChild(row);
    const contentEl = row.querySelector('.msg-content');

    // Tokenize into natural words/chunks
    const words = fullText.split(' ');
    let currentText = '';

    for (let i = 0; i < words.length; i++) {
        if (State.stopStreamingRequested) {
            currentText = fullText;
            break;
        }

        currentText += (i === 0 ? '' : ' ') + words[i];

        // Render live markdown + blinking cursor
        if (window.marked) {
            contentEl.innerHTML = marked.parse(currentText) + '<span class="typing-cursor"></span>';
        } else {
            contentEl.textContent = currentText;
        }

        scrollToBottom();

        // Variable natural delay (punctuations pause longer)
        const word = words[i];
        let delay = 18;
        if (word.endsWith('.') || word.endsWith('!') || word.endsWith('?')) {
            delay = 65;
        } else if (word.endsWith(',') || word.endsWith(';')) {
            delay = 35;
        }

        await new Promise(r => setTimeout(r, delay));
    }

    // Finished streaming - finalize UI
    State.isStreaming = false;
    DOM.sendBtn.disabled = false;
    DOM.stopGeneratingWrap.style.display = 'none';

    // Save final message to conversation
    const finalMsg = {
        role: 'assistant',
        content: currentText,
        sources: sources || [],
        latency_ms: latency_ms,
        status: status,
        timestamp: new Date().toISOString()
    };
    active.messages.push(finalMsg);
    active.updatedAt = new Date().toISOString();
    saveConversations();
    renderHistorySidebar();

    // Re-render message row cleanly with source chips & action buttons
    row.remove();
    renderMessageRow(finalMsg, active.messages.length - 1);
    scrollToBottom();
}

function stopGenerating() {
    State.stopStreamingRequested = true;
    showToast('Generation halted', 'info');
}

function scrollToBottom() {
    setTimeout(() => {
        DOM.chatViewport.scrollTop = DOM.chatViewport.scrollHeight;
    }, 20);
}

// ============================================================================
// MODALS & ACTIONS
// ============================================================================

function openRenameModal(sessionId, currentTitle) {
    DOM.renameInput.value = currentTitle;
    DOM.renameModal.classList.add('active');
    DOM.saveRenameBtn.onclick = () => {
        renameConversation(sessionId, DOM.renameInput.value);
        closeModal('renameModal');
    };
    setTimeout(() => DOM.renameInput.focus(), 100);
}

function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

function exportCurrentChat() {
    const active = State.conversations[State.activeSessionId];
    if (!active || !active.messages || active.messages.length === 0) {
        showToast('No messages to export in this conversation', 'warning');
        return;
    }

    let md = `# CampusOS AI Consultation - ${active.title}\n`;
    md += `**Date:** ${new Date(active.createdAt).toLocaleString()}\n\n---\n\n`;

    active.messages.forEach(m => {
        md += `### ${m.role === 'user' ? 'Student' : 'CampusOS Helpdesk Agent'}\n`;
        md += `${m.content}\n\n`;
        if (m.sources && m.sources.length > 0) {
            md += `*Sources: ${m.sources.join(', ')}*\n\n`;
        }
    });

    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${active.title.toLowerCase().replace(/[^a-z0-9]/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported conversation as Markdown', 'success');
}

function showToast(message, type = 'info', duration = 2800) {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${escapeHtml(message)}</span>`;
    DOM.toastStack.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(20px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

function initEventListeners() {
    // Sidebar Collapse
    DOM.sidebarCollapseBtn.addEventListener('click', () => {
        DOM.sidebar.classList.toggle('collapsed');
    });

    DOM.mobileMenuBtn.addEventListener('click', () => {
        DOM.sidebar.classList.toggle('mobile-open');
    });

    // New Chat Action
    DOM.newChatBtn.addEventListener('click', () => createNewConversation(true));

    // Search Filter
    DOM.searchHistoryInput.addEventListener('input', renderHistorySidebar);

    // Send Message
    DOM.sendBtn.addEventListener('click', handleSendMessage);
    DOM.stopGeneratingBtn.addEventListener('click', stopGenerating);

    // Prompt Card Clicks
    DOM.promptCards.forEach(card => {
        card.addEventListener('click', () => {
            const prompt = card.getAttribute('data-prompt');
            DOM.chatInput.value = prompt;
            handleSendMessage();
        });
    });

    // Auto-Resize Textarea & Character Count
    DOM.chatInput.addEventListener('input', () => {
        DOM.chatInput.style.height = 'auto';
        DOM.chatInput.style.height = Math.min(DOM.chatInput.scrollHeight, 160) + 'px';
        DOM.charCount.textContent = `${DOM.chatInput.value.length}/3000`;
    });

    DOM.chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    });

    // Scroll Detection for Floating Scroll-To-Bottom Button
    DOM.chatViewport.addEventListener('scroll', () => {
        const threshold = 150;
        const isNearBottom = DOM.chatViewport.scrollHeight - DOM.chatViewport.scrollTop - DOM.chatViewport.clientHeight < threshold;
        DOM.scrollBottomBtn.style.display = isNearBottom ? 'none' : 'flex';
    });

    DOM.scrollBottomBtn.addEventListener('click', scrollToBottom);

    // Topbar Actions
    DOM.themeToggleBtn.addEventListener('click', toggleTheme);
    DOM.directoryBtn.addEventListener('click', () => openModal('directoryModal'));
    DOM.directoryBtnTrigger.addEventListener('click', () => openModal('directoryModal'));
    DOM.exportChatBtn.addEventListener('click', exportCurrentChat);

    DOM.renameSessionBtn.addEventListener('click', () => {
        const active = State.conversations[State.activeSessionId];
        if (active) openRenameModal(active.id, active.title);
    });

    // Keyboard Shortcuts
    document.addEventListener('keydown', (e) => {
        // Alt + N -> New Chat
        if (e.altKey && e.key.toLowerCase() === 'n') {
            e.preventDefault();
            createNewConversation(true);
        }
        // Focus chat input on /
        if (e.key === '/' && document.activeElement !== DOM.chatInput && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            DOM.chatInput.focus();
        }
    });

    // Modal Close handlers
    document.querySelectorAll('.close-modal, [data-close]').forEach(btn => {
        btn.addEventListener('click', () => {
            const modalId = btn.getAttribute('data-close');
            if (modalId) closeModal(modalId);
        });
    });

    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) backdrop.classList.remove('active');
        });
    });
}
