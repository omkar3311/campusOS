/**
 * CampusOS StudyIQ - Single Page Application Engine
 * Vanilla JavaScript implementation matching ResumeIQ architecture & ergonomics
 */

const API_BASE = window.location.pathname.replace(/\/$/, "");

// Global Application State
const state = {
  activeView: 'chat',
  activeMode: 'auto',
  activeDocument: '',
  documents: [],
  focusTopic: '',
  isProcessing: false,
  plannerData: null,
  quizData: null,
  flashcardsData: null
};

// Mode Map
const MODE_MAP = {
  'auto': { name: 'Auto-Infer Mode', icon: '' },
  'concept': { name: 'Concept Explainer', icon: '' },
  'plan': { name: 'Study Planner', icon: '' },
  'assignment': { name: 'Assignment Helper', icon: '' },
  'quiz': { name: 'Quiz Generator', icon: '' },
  'cram': { name: 'Exam Crammer', icon: '' }
};

// Sample Topics for Instant Testing
const SAMPLE_TOPICS = {
  data_structures: "Binary Search Trees, Graph Traversals (BFS/DFS), and Hash Table Collisions",
  dbms: "Database Normalization (1NF, 2NF, 3NF, BCNF) and ACID Transactions",
  rag_ai: "Retrieval-Augmented Generation Architecture, Vector Embeddings, and ChromaDB Retrieval"
};

// ==========================================================================
// Initialization on DOM Ready (Clean Slate Per Page Visit/Refresh)
// ==========================================================================
document.addEventListener('DOMContentLoaded', async () => {
  setupReturnNavigation();
  initNavigation();
  initChatEvents();
  initUploadModal();
  initAcademicGenerators();
  
  // Wipe session memory and loaded documents on fresh page visit / refresh
  try {
    await fetch(`${API_BASE}/api/reset-session`, { method: 'POST' });
  } catch (e) {
    console.warn('Session reset on page load:', e);
  }
  
  fetchSystemStatus();
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

// ==========================================================================
// System Status & Documents Fetching
// ==========================================================================
async function fetchSystemStatus() {
  try {
    const res = await fetch(`${API_BASE}/api/status`);
    const data = await res.json();
    
    state.documents = data.documents || [];
    updateDocumentDropdowns();
    updateStatusIndicators(data);
    renderDocumentsTable();
    renderChatWelcome();
    loadAuditMetrics();

    if (state.documents.length > 0 && !state.activeDocument) {
      state.activeDocument = state.documents[0].filename;
      updateDocumentDropdowns();
    }
  } catch (err) {
    console.error('Error fetching system status:', err);
    showToast('Could not connect to backend server', 'error');
  }
}

function updateStatusIndicators(data) {
  const countEl = document.getElementById('sidebar-doc-count');
  if (countEl) {
    countEl.textContent = `${state.documents.length} Loaded`;
  }
  const topDocBadge = document.getElementById('top-doc-badge');
  if (topDocBadge) {
    if (state.activeDocument) {
      topDocBadge.textContent = state.activeDocument;
      topDocBadge.style.display = 'inline-flex';
    } else {
      topDocBadge.style.display = 'none';
    }
  }
}

function updateDocumentDropdowns() {
  const select = document.getElementById('sidebar-doc-select');
  if (!select) return;

  select.innerHTML = '';
  
  if (state.documents.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No Documents Loaded';
    select.appendChild(opt);
    select.disabled = true;
    return;
  }

  select.disabled = false;
  state.documents.forEach(doc => {
    const opt = document.createElement('option');
    opt.value = doc.filename;
    opt.textContent = `${doc.filename} (${doc.chunks} chunks)`;
    if (doc.filename === state.activeDocument) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });

  select.onchange = (e) => {
    state.activeDocument = e.target.value;
    showToast(`Active study material set to: ${state.activeDocument}`, 'info');
    updateStatusIndicators();
  };
}

// ==========================================================================
// Navigation & View Switching
// ==========================================================================
function initNavigation() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = item.getAttribute('data-view');
      switchView(targetView);
    });
  });

  const btnLoadSample = document.getElementById('btn-load-sample');
  if (btnLoadSample) {
    btnLoadSample.addEventListener('click', loadSampleDocument);
  }

  const btnOpenUpload = document.getElementById('btn-open-upload');
  if (btnOpenUpload) {
    btnOpenUpload.addEventListener('click', openUploadModal);
  }

  const btnTopbarUpload = document.getElementById('btn-topbar-upload');
  if (btnTopbarUpload) {
    btnTopbarUpload.addEventListener('click', openUploadModal);
  }
}

function switchView(viewName) {
  state.activeView = viewName;

  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  document.querySelectorAll('.view-container').forEach(container => {
    if (container.id === `view-${viewName}`) {
      container.classList.add('active');
    } else {
      container.classList.remove('active');
    }
  });

  const titles = {
    'chat': { title: 'AI Study Copilot & Academic Assistant', desc: 'Ask questions, explain complex theories, or generate revision roadmaps' },
    'documents': { title: 'Study Materials & Knowledge Base', desc: 'Manage textbooks, notes, syllabus files, and vector embeddings' },
    'planner': { title: 'Exam Revision & Study Schedule Generator', desc: 'Structured day-by-day exam roadmap grounded in active study material' },
    'quiz': { title: 'Smart Practice Quiz & MCQ Studio', desc: 'Generate interactive practice questions strictly grounded in your textbook' },
    'flashcards': { title: 'Key Concepts & Definition Flashcards', desc: 'Essential terms, formulas, theorems, and exam tips' },
    'audit': { title: 'Vector Store Index & Chunks Telemetry', desc: 'Inspect semantic retrieval parameters and chunk distribution' }
  };

  const info = titles[viewName] || { title: 'StudyIQ SaaS', desc: 'Academic Intelligence' };
  document.getElementById('topbar-title').textContent = info.title;
  document.getElementById('topbar-desc').textContent = info.desc;

  if (viewName === 'documents') {
    renderDocumentsTable();
  } else if (viewName === 'audit') {
    loadAuditMetrics();
  }
}

// ==========================================================================
// Sample Study Material Loader
// ==========================================================================
async function loadSampleDocument() {
  const btn = document.getElementById('btn-load-sample');
  const originalText = btn.innerHTML;
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span>Loading Demo...</span>`;
  }

  try {
    const res = await fetch(`${API_BASE}/api/load-sample`, { method: 'POST' });
    const data = await res.json();
    
    if (res.ok && data.success) {
      showToast(data.message, 'success');
      await fetchSystemStatus();
      switchView('chat');
    } else {
      showToast(data.detail || 'Failed to load sample textbook', 'error');
    }
  } catch (err) {
    console.error('Error loading sample:', err);
    showToast('Failed to connect to server', 'error');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// ==========================================================================
// VIEW 1: Interactive Chat Copilot
// ==========================================================================
function initChatEvents() {
  const chatInput = document.getElementById('chat-input-textarea');
  const btnSend = document.getElementById('btn-chat-send');
  const btnToggleTopic = document.getElementById('btn-toggle-chat-topic');
  const topicDrawer = document.getElementById('chat-topic-drawer');
  const btnResetSession = document.getElementById('btn-reset-chat');

  const pills = document.querySelectorAll('.mode-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeMode = pill.getAttribute('data-mode');
      const indicator = document.getElementById('active-mode-indicator');
      if (indicator) {
        indicator.textContent = `Mode: ${MODE_MAP[state.activeMode]?.name || 'Auto-Infer'}`;
      }
    });
  });

  if (btnToggleTopic && topicDrawer) {
    btnToggleTopic.addEventListener('click', () => {
      topicDrawer.classList.toggle('open');
      btnToggleTopic.classList.toggle('active');
    });
  }

const btnSampleTopic = document.getElementById('btn-chat-sample-topic');
  if (btnSampleTopic) {
    btnSampleTopic.addEventListener('click', () => {
      const textarea = document.getElementById('chat-topic-textarea');
      textarea.value = SAMPLE_TOPICS.data_structures;
      showToast('Sample topic attached to AI context', 'info');
    });
  }

  if (btnSend) {
    btnSend.addEventListener('click', sendChatMessage);
  }

  if (chatInput) {
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendChatMessage();
      }
    });

    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });
  }

  if (btnResetSession) {
    btnResetSession.addEventListener('click', async () => {
      try {
        await fetch(`${API_BASE}/api/reset-session`, { method: 'POST' });
        showToast('Study session memory cleared', 'info');
        const history = document.getElementById('chat-history-container');
        if (history) history.innerHTML = '';
        renderChatWelcome();
      } catch (err) {
        showToast('Error resetting session', 'error');
      }
    });
  }
}

function renderChatWelcome() {
  const history = document.getElementById('chat-history-container');
  if (!history) return;

  if (state.documents.length === 0) {
    history.innerHTML = `
      <div class="chat-welcome" id="chat-welcome-screen">
        <div class="welcome-icon-box" style="background: rgba(245, 158, 11, 0.1); color: var(--warning); border-color: rgba(245, 158, 11, 0.3);">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
        </div>
        <h2>No Study Material Uploaded Yet</h2>
        <p>StudyAgent requires your course textbook, syllabus, or lecture notes to provide grounded explanations and revision roadmaps.</p>
        
        <div style="display: flex; gap: 12px; margin-top: 8px;">
          <button class="btn btn-primary" onclick="openUploadModal()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="17 8 12 3 7 8"></polyline><line x1="12" y1="3" x2="12" y2="15"></line></svg>
            <span>Upload Study Material (PDF/TXT)</span>
          </button>
          <button class="btn btn-demo" onclick="loadSampleDocument()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 6px;"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>
            <span>Load Demo Study Guide</span>
          </button>
        </div>
      </div>
    `;
    return;
  }

  history.innerHTML = `
    <div class="chat-welcome" id="chat-welcome-screen">
      <div class="welcome-icon-box">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
          <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
          <line x1="9" y1="7" x2="15" y2="7"></line>
          <line x1="9" y1="11" x2="15" y2="11"></line>
        </svg>
      </div>
      <h2>What would you like to master today?</h2>
      <p>StudyAgent is grounded in your active material: <strong>${escapeHtml(state.activeDocument || 'Study Document')}</strong>.</p>
      
      <div class="prompt-chips-grid">
        <div class="prompt-chip" data-prompt="Explain the most complex core concept from this document in simple terms with intuitive examples." data-mode="concept">
          <div class="chip-tag">Concept Explainer</div>
          <div class="chip-title">Deep Concept Explanation</div>
          <div class="chip-desc">Intuitive breakdown of difficult formulas & theories</div>
        </div>

        <div class="prompt-chip" data-prompt="Create a high-impact 7-day revision schedule with daily milestones for upcoming exams." data-mode="plan">
          <div class="chip-tag">Revision Planner</div>
          <div class="chip-title">7-Day Exam Roadmap</div>
          <div class="chip-desc">Organized timetable covering all major chapters</div>
        </div>

        <div class="prompt-chip" data-prompt="Give me step-by-step problem-solving methods and key takeaways for coursework assignments." data-mode="assignment">
          <div class="chip-tag">Assignment Helper</div>
          <div class="chip-title">Assignment Guidance</div>
          <div class="chip-desc">Methodologies, proofs, and architectural trade-offs</div>
        </div>

        <div class="prompt-chip" data-prompt="Generate 5 practice multiple-choice questions (MCQs) with detailed answer keys and explanations." data-mode="quiz">
          <div class="chip-tag">Practice Quiz</div>
          <div class="chip-title">Self-Assessment MCQs</div>
          <div class="chip-desc">Test comprehension with grounded questions</div>
        </div>
      </div>
    </div>
  `;

  document.querySelectorAll('.prompt-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      const mode = chip.getAttribute('data-mode') || 'auto';
      state.activeMode = mode;
      document.getElementById('chat-input-textarea').value = prompt;
      sendChatMessage();
    });
  });
}

async function sendChatMessage() {
  if (state.isProcessing) return;

  const chatInput = document.getElementById('chat-input-textarea');
  const message = chatInput.value.trim();
  if (!message) return;

  if (state.documents.length === 0) {
    showToast('Please upload or load a study document first!', 'warning');
    openUploadModal();
    return;
  }

  const welcome = document.getElementById('chat-welcome-screen');
  if (welcome) welcome.remove();

  const history = document.getElementById('chat-history-container');

  appendUserMessage(message);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  const thinkingId = 'thinking-' + Date.now();
  appendThinkingIndicator(thinkingId);
  history.scrollTop = history.scrollHeight;

  state.isProcessing = true;
  document.getElementById('btn-chat-send').disabled = true;

  const topicTextarea = document.getElementById('chat-topic-textarea');
  const topicContent = topicTextarea ? topicTextarea.value.trim() : '';

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        mode: state.activeMode,
        topic: topicContent || null,
        filename: state.activeDocument || null
      })
    });

    const data = await res.json();
    removeElement(thinkingId);

    if (res.ok) {
      appendAssistantMessage(data.answer, data.mode_used, data.guardrail_blocked);
    } else {
      appendAssistantMessage(`**Error**: ${data.detail || 'Failed to process request.'}`, 'System Error', true);
    }
  } catch (err) {
    console.error('Chat error:', err);
    removeElement(thinkingId);
    appendAssistantMessage('Connection to server failed. Please ensure the backend is running.', 'Network Error', true);
  } finally {
    state.isProcessing = false;
    document.getElementById('btn-chat-send').disabled = false;
    history.scrollTop = history.scrollHeight;
  }
}

function appendUserMessage(text) {
  const history = document.getElementById('chat-history-container');
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg user';
  msgEl.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </svg>
    </div>
    <div class="msg-body">
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-meta">
        <span>You</span> • <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      </div>
    </div>
  `;
  history.appendChild(msgEl);
}

function appendAssistantMessage(text, modeUsed, isBlocked = false) {
  const history = document.getElementById('chat-history-container');
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg assistant';

  let renderedHtml = '';
  if (typeof marked !== 'undefined') {
    renderedHtml = marked.parse(text);
  } else {
    renderedHtml = escapeHtml(text).replace(/\n/g, '<br>');
  }

  const modeName = MODE_MAP[modeUsed]?.name || modeUsed || 'Grounded Response';
  const copyBtnId = 'copy-' + Date.now();

  msgEl.innerHTML = `
    <div class="msg-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
      </svg>
    </div>
    <div class="msg-body">
      <div class="msg-bubble markdown-body ${isBlocked ? 'guardrail-blocked' : ''}">
        ${renderedHtml}
      </div>
      <div class="msg-meta">
        <span class="mode-badge-tag">${escapeHtml(modeName)}</span>
        <span>${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        <button class="btn-copy-msg" id="${copyBtnId}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          Copy
        </button>
      </div>
    </div>
  `;
  history.appendChild(msgEl);

  const copyBtn = document.getElementById(copyBtnId);
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(text);
      showToast('Response copied to clipboard', 'info');
    });
  }
}

function appendThinkingIndicator(id) {
  const history = document.getElementById('chat-history-container');
  const thinkEl = document.createElement('div');
  thinkEl.id = id;
  thinkEl.className = 'chat-msg assistant';
  thinkEl.innerHTML = `
    <div class="msg-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
      </svg>
    </div>
    <div class="msg-body">
      <div class="thinking-box">
        <div class="pulsing-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Retrieving & synthesizing grounded answer...</span>
      </div>
    </div>
  `;
  history.appendChild(thinkEl);
}


function initUploadModal() {
  const modal = document.getElementById('upload-modal');
  const btnTrigger = document.getElementById('btn-open-upload');
  const btnTopbarTrigger = document.getElementById('btn-topbar-upload');
  const btnClose = document.getElementById('btn-close-upload');
  const dropzone = document.getElementById('dropzone-input');
  const fileInput = document.getElementById('file-upload-element');
  const btnSubmit = document.getElementById('btn-submit-upload');

  let selectedFiles = [];

  if (btnTrigger) btnTrigger.addEventListener('click', openUploadModal);
  if (btnTopbarTrigger) btnTopbarTrigger.addEventListener('click', openUploadModal);
  if (btnClose) btnClose.addEventListener('click', closeUploadModal);

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeUploadModal();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('dragover');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      if (e.dataTransfer.files.length > 0) {
        selectedFiles = Array.from(e.dataTransfer.files);
        updateUploadPreview(selectedFiles);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) {
        selectedFiles = Array.from(fileInput.files);
        updateUploadPreview(selectedFiles);
      }
    });
  }

  if (btnSubmit) {
    btnSubmit.addEventListener('click', async () => {
      if (selectedFiles.length === 0) {
        showToast('Please select at least one PDF, TXT, DOCX, or MD file', 'warning');
        return;
      }

      const formData = new FormData();
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      btnSubmit.disabled = true;
      btnSubmit.innerHTML = `<span>Indexing Documents...</span>`;

      try {
        const res = await fetch(`${API_BASE}/api/upload`, {
          method: 'POST',
          body: formData
        });

        const data = await res.json();
        if (res.ok && (data.success || data.status === 'success')) {
          showToast(`Successfully indexed ${data.uploaded_count || selectedFiles.length} file(s)!`, 'success');
          closeUploadModal();
          selectedFiles = [];
          updateUploadPreview([]);
          if (fileInput) fileInput.value = '';
          await fetchSystemStatus();
        } else {
          showToast(data.detail || 'Upload failed', 'error');
        }
      } catch (err) {
        console.error('Upload error:', err);
        showToast('Error uploading files to server', 'error');
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<span>Index Documents</span>`;
      }
    });
  }
}

function openUploadModal() {
  const modal = document.getElementById('upload-modal');
  if (modal) {
    modal.classList.add('open');
    modal.classList.add('active');
  }
}

function closeUploadModal() {
  const modal = document.getElementById('upload-modal');
  if (modal) {
    modal.classList.remove('open');
    modal.classList.remove('active');
  }
}

window.openUploadModal = openUploadModal;
window.closeUploadModal = closeUploadModal;

function updateUploadPreview(files) {
  const listEl = document.getElementById('upload-file-list');
  if (!listEl) return;
  listEl.innerHTML = '';

  files.forEach(f => {
    const item = document.createElement('div');
    item.className = 'file-preview-item';
    item.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>
        <strong>${escapeHtml(f.name)}</strong>
      </div>
      <span style="color: var(--text-dim);">${(f.size / 1024).toFixed(1)} KB</span>
    `;
    listEl.appendChild(item);
  });
}



function renderDocumentsTable() {
  const tbody = document.getElementById('documents-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (state.documents.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--text-muted); padding: 24px;">
          No study documents indexed yet. Upload a PDF or click "Load Demo Textbook".
        </td>
      </tr>
    `;
    return;
  }

  state.documents.forEach(doc => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><strong>${escapeHtml(doc.filename)}</strong></td>
      <td>${doc.size_mb || 0.1} MB</td>
      <td><span class="mode-badge-pill">${doc.chunks || 0} Chunks</span></td>
      <td>${doc.uploaded_at || 'Recently'}</td>
      <td>
        <button class="btn btn-sm btn-outline" onclick="selectDocument('${escapeHtml(doc.filename)}')">Select</button>
        <button class="btn btn-sm btn-secondary" style="color: var(--danger);" onclick="deleteDocument('${doc.id}')">Delete</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function selectDocument(filename) {
  state.activeDocument = filename;
  updateDocumentDropdowns();
  updateStatusIndicators();
  showToast(`Active study material set to: ${filename}`, 'info');
}

async function deleteDocument(docId) {
  if (!confirm('Are you sure you want to remove this document from your knowledge base?')) return;

  try {
    const res = await fetch(`${API_BASE}/api/documents/${docId}`, { method: 'DELETE' });
    const data = await res.json();
    if (res.ok) {
      showToast(data.message || 'Document deleted', 'success');
      await fetchSystemStatus();
    } else {
      showToast(data.detail || 'Failed to delete document', 'error');
    }
  } catch (err) {
    showToast('Error connecting to server', 'error');
  }
}

function initAcademicGenerators() {
  const btnGenPlanner = document.getElementById('btn-generate-planner');
  if (btnGenPlanner) {
    btnGenPlanner.addEventListener('click', runPlannerGeneration);
  }

  const btnGenQuiz = document.getElementById('btn-generate-quiz');
  if (btnGenQuiz) {
    btnGenQuiz.addEventListener('click', runQuizGeneration);
  }

  const btnGenFlashcards = document.getElementById('btn-generate-flashcards');
  if (btnGenFlashcards) {
    btnGenFlashcards.addEventListener('click', runFlashcardGeneration);
  }
}

async function runPlannerGeneration() {
  if (state.documents.length === 0) {
    showToast('Please upload or load study materials first!', 'warning');
    openUploadModal();
    return;
  }

  const topic = document.getElementById('planner-topic-input').value.trim();
  const days = parseInt(document.getElementById('planner-days-input').value) || 7;
  const hours = parseInt(document.getElementById('planner-hours-input').value) || 3;
  const outputEl = document.getElementById('planner-output-content');

  outputEl.innerHTML = '<div class="empty-placeholder"><p>Synthesizing structured revision roadmap...</p></div>';

  try {
    const res = await fetch(`${API_BASE}/api/planner`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, days, hours_per_day: hours, filename: state.activeDocument })
    });
    const data = await res.json();
    if (res.ok && data.roadmap) {
      outputEl.innerHTML = marked.parse(data.roadmap);
      showToast('Revision roadmap generated!', 'success');
    } else {
      outputEl.innerHTML = `<p style="color: var(--danger);">${data.detail || 'Failed to generate planner.'}</p>`;
    }
  } catch (err) {
    outputEl.innerHTML = `<p style="color: var(--danger);">Server connection error.</p>`;
  }
}

async function runQuizGeneration() {
  if (state.documents.length === 0) {
    showToast('Please upload or load study materials first!', 'warning');
    openUploadModal();
    return;
  }

  const topic = document.getElementById('quiz-topic-input').value.trim();
  const outputEl = document.getElementById('quiz-content-area');

  outputEl.innerHTML = '<div class="empty-placeholder"><p>Extracting MCQs & quiz questions from textbook...</p></div>';

  try {
    const res = await fetch(`${API_BASE}/api/quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ topic, question_count: 5, filename: state.activeDocument })
    });
    const data = await res.json();
    if (res.ok && data.quiz) {
      outputEl.innerHTML = marked.parse(data.quiz);
      showToast('Practice quiz generated!', 'success');
    } else {
      outputEl.innerHTML = `<p style="color: var(--danger);">${data.detail || 'Failed to generate quiz.'}</p>`;
    }
  } catch (err) {
    outputEl.innerHTML = `<p style="color: var(--danger);">Server connection error.</p>`;
  }
}

async function runFlashcardGeneration() {
  if (state.documents.length === 0) {
    showToast('Please upload or load study materials first!', 'warning');
    openUploadModal();
    return;
  }

  const outputEl = document.getElementById('flashcards-grid');
  outputEl.innerHTML = '<div class="empty-placeholder" style="grid-column: 1 / -1;"><p>Synthesizing concept definitions & flashcard deck...</p></div>';

  try {
    const res = await fetch(`${API_BASE}/api/flashcards`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: 6, filename: state.activeDocument })
    });
    const data = await res.json();
    if (res.ok && data.flashcards) {
      outputEl.innerHTML = marked.parse(data.flashcards);
      showToast('Flashcard deck created!', 'success');
    } else {
      outputEl.innerHTML = `<p style="color: var(--danger); grid-column: 1 / -1;">${data.detail || 'Failed to extract flashcards.'}</p>`;
    }
  } catch (err) {
    outputEl.innerHTML = `<p style="color: var(--danger); grid-column: 1 / -1;">Server connection error.</p>`;
  }
}

function loadAuditMetrics() {
  const totalDocs = document.getElementById('audit-total-docs');
  const totalChunks = document.getElementById('audit-total-chunks');
  if (totalDocs) totalDocs.textContent = state.documents.length;
  if (totalChunks) {
    const total = state.documents.reduce((acc, d) => acc + (d.chunks || 0), 0);
    totalChunks.textContent = total;
  }
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

function removeElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
