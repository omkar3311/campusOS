/**
 * CampusOS ResumeIQ - Single Page Application Engine
 * Vanilla JavaScript implementation with full reactivity and zero external bundlers
 */

const API_BASE = window.location.pathname.replace(/\/$/, "");

function getSessionQueryString() {
  const params = new URLSearchParams(window.location.search);
  const query = new URLSearchParams();
  const keys = ['role', 'name', 'username', 'user_id', 'id', 'student_id', 'prn'];

  keys.forEach(key => {
    const value = params.get(key);
    if (value) query.set(key, value);
  });

  return query.toString();
}

function buildApiUrl(path) {
  const query = getSessionQueryString();
  return query ? `${API_BASE}${path}?${query}` : `${API_BASE}${path}`;
}

// Global Application State
const state = {
  activeView: 'chat',
  activeMode: 'auto',
  activeResume: '',
  loadedResumes: [],
  jobDescription: '',
  isChatProcessing: false,
  atsData: null,
  jdMatchData: null,
  chatHistory: [],
  interview: null,
  interviewTimer: null,
  interviewSeconds: 60,
  interviewRecognition: null
};

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"})[character]);
}

function removeElement(id) {
  const element = typeof id === 'string' ? document.getElementById(id) : id;
  if (element) element.remove();
}

function showToast(message, type = 'info') {
  const stack = document.getElementById('toast-stack');
  if (!stack) return;
  const toast = document.createElement('div');
  toast.className = `toast-item ${type}`;
  toast.textContent = message;
  stack.appendChild(toast);
  setTimeout(() => toast.remove(), 4200);
}

async function loadProfileDetails() {
  if (!state.activeResume) return;
  try {
    const separator = getSessionQueryString() ? '&' : '?';
    const res = await fetch(buildApiUrl('/api/resume-details') + `${separator}filename=${encodeURIComponent(state.activeResume)}`);
    const data = await res.json();
    if (!res.ok) return;
    const preview = document.getElementById('profile-resume-preview');
    const name = document.getElementById('profile-candidate-name');
    const filenameEl = document.getElementById('profile-filename');
    const wordsEl = document.getElementById('profile-words');
    const charsEl = document.getElementById('profile-chars');
    const summaryEl = document.getElementById('profile-memory-summary');
    if (name) name.textContent = data.candidate_name || 'Candidate';
    if (filenameEl) filenameEl.textContent = data.filename || state.activeResume;
    if (wordsEl) wordsEl.textContent = `${data.word_count || 0} words`;
    if (charsEl) charsEl.textContent = `${data.char_count || 0} characters`;
    if (preview) preview.textContent = data.raw_text_preview || '';
    if (summaryEl && data.profile_summary) summaryEl.textContent = data.profile_summary;
  } catch (error) {
    console.warn('Unable to load resume profile:', error);
  }
}

function getCurrentUserChatKey() {
  const params = new URLSearchParams(window.location.search);
  const role = params.get('role') || 'student';
  const name = params.get('name') || params.get('username') || 'user';
  const userId = params.get('user_id') || params.get('id') || params.get('student_id') || 'guest';
  const path = window.location.pathname.replace(/[^a-zA-Z0-9_-]/g, '_') || 'resume_agent';
  const suffix = `${role}-${(name || 'user').replace(/\s+/g, '_')}-${userId}`;
  return `campusos_resume_chat_${path}_${suffix}`;
}

function loadPersistedChatHistory() {
  try {
    const raw = localStorage.getItem(getCurrentUserChatKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Unable to restore resume chat history:', error);
    return [];
  }
}

function savePersistedChatHistory() {
  try {
    localStorage.setItem(getCurrentUserChatKey(), JSON.stringify(state.chatHistory || []));
  } catch (error) {
    console.warn('Unable to save resume chat history:', error);
  }
}

function clearPersistedChatHistory() {
  try {
    localStorage.removeItem(getCurrentUserChatKey());
  } catch (error) {
    console.warn('Unable to clear resume chat history:', error);
  }
}

function restorePersistedChatHistory() {
  const history = document.getElementById('chat-history-container');
  if (!history) return;

  state.chatHistory = loadPersistedChatHistory();
  if (!state.chatHistory.length) {
    renderChatWelcome();
    return;
  }

  history.innerHTML = '';
  state.chatHistory.forEach(entry => {
    if (entry.type === 'user') {
      appendUserMessage(entry.text, { skipSave: true, time: entry.time });
    } else if (entry.type === 'assistant') {
      appendAssistantMessage(entry.text, entry.modeName || 'Career Agent', Boolean(entry.guardrail), { skipSave: true, time: entry.time });
    }
  });
  history.scrollTop = history.scrollHeight;
}

// Mode Map
const MODE_MAP = {
  'auto': { name: 'Auto-Infer Mode', id: null, icon: '' },
  '1': { name: 'Resume Review Agent', id: '1', icon: '' },
  '2': { name: 'Placement Eligibility Checker', id: '2', icon: '' },
  '3': { name: 'Skill Gap Analyzer', id: '3', icon: '' },
  '4': { name: 'Interview Preparation Agent', id: '4', icon: '' },
  '5': { name: 'Coding Practice Recommender', id: '5', icon: '' },
  '6': { name: 'Career Recommendation Agent', id: '6', icon: '' }
};

// Sample Job Descriptions for Instant Testing
const SAMPLE_JDS = {
  fullstack: `Role: Senior Full Stack Engineer
Requirements:
- 3+ years experience with Python, FastAPI / Flask, and modern JavaScript (React / Vue / Vanilla JS).
- Deep experience with PostgreSQL / MySQL, ChromaDB or vector databases, and Redis caching.
- Strong knowledge of RESTful API design, microservices architecture, and Docker containerization.
- Familiarity with LLM application development, LangChain, OpenAI/Groq APIs, and RAG pipelines.
- Experience with Git, CI/CD pipelines, unit testing, and AWS/GCP cloud deployments.
- Bachelor's in Computer Science or equivalent practical experience.`,

  ai_engineer: `Role: Generative AI & Machine Learning Engineer
Requirements:
- Proven experience building RAG (Retrieval Augmented Generation) pipelines using LangChain, LlamaIndex, or Hugging Face.
- Hands-on skills with Vector Databases: ChromaDB, Pinecone, or FAISS.
- Proficiency in Python, PyTorch, Sentence-Transformers, HuggingFace embeddings, and LLM fine-tuning.
- Experience with prompt engineering, guardrails implementation, and evaluation metrics.
- Strong foundation in Data Structures, Algorithms, Mathematics, and NLP concepts.`,

  frontend: `Role: Senior Frontend Engineer
Requirements:
- Mastery of HTML5, CSS3, Modern ES6+ JavaScript, TypeScript, and responsive layout architectures.
- Experience building high-performance SaaS dashboards, interactive SVG charts, and state-driven web apps.
- Deep understanding of UI/UX ergonomics, accessibility (WCAG), micro-interactions, and design systems.
- Familiarity with REST APIs, WebSocket real-time communication, and client-side performance optimization.`
};

// ==========================================================================
// Initialization on DOM Ready
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  setupReturnNavigation();
  initNavigation();
  initChatEvents();
  initUploadModal();
  initJDEvents();
  initInterviewStudio();
  state.chatHistory = loadPersistedChatHistory();
  fetchSystemStatus();
  restorePersistedChatHistory();
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
  const name = urlParams.get('name') || (role === 'hod' ? 'HOD Admin' : (role === 'teacher' ? 'Faculty' : 'Candidate'));
  
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
// System Status & Resumes Fetching
// ==========================================================================
async function fetchSystemStatus() {
  try {
    const res = await fetch(buildApiUrl('/api/status'));
    const data = await res.json();
    
    state.loadedResumes = data.resumes || [];
    updateResumeDropdowns();
    updateStatusIndicators(data);

    if (state.loadedResumes.length > 0 && !state.activeResume) {
      state.activeResume = state.loadedResumes[0].filename;
      updateResumeDropdowns();
    }
  } catch (err) {
    console.error('Error fetching system status:', err);
    showToast('Could not connect to backend server', 'error');
  }
}

function updateStatusIndicators(data) {
  const countEl = document.getElementById('sidebar-resume-count');
  if (countEl) {
    countEl.textContent = `${data.total_resumes} Loaded`;
  }
  const topResumeBadge = document.getElementById('top-resume-badge');
  if (topResumeBadge) {
    if (state.activeResume) {
      topResumeBadge.textContent = state.activeResume;
      topResumeBadge.style.display = 'inline-flex';
    } else {
      topResumeBadge.style.display = 'none';
    }
  }
}

function updateResumeDropdowns() {
  const selects = [
    document.getElementById('sidebar-resume-select'),
    document.getElementById('ats-resume-select'),
    document.getElementById('jd-resume-select'),
    document.getElementById('profile-resume-select')
  ];

  selects.forEach(select => {
    if (!select) return;
    select.innerHTML = '';
    
    if (state.loadedResumes.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No Resumes Loaded';
      select.appendChild(opt);
      select.disabled = true;
      return;
    }

    select.disabled = false;
    state.loadedResumes.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.filename;
      opt.textContent = `${r.candidate_name} (${r.filename})`;
      if (r.filename === state.activeResume) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });

    select.onchange = (e) => {
      state.activeResume = e.target.value;
      updateResumeDropdowns();
      handleResumeChanged();
    };
  });
}

function handleResumeChanged() {
  showToast(`Active resume switched to: ${state.activeResume}`, 'info');
  updateStatusIndicators({ total_resumes: state.loadedResumes.length });
  
  // Refresh current view data if needed
  if (state.activeView === 'ats') {
    runATSAudit();
  } else if (state.activeView === 'profile') {
    loadProfileDetails();
  }
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

  // Load sample resume quick button
  const btnLoadSample = document.getElementById('btn-load-sample');
  if (btnLoadSample) {
    btnLoadSample.addEventListener('click', loadSampleResume);
  }
}

function switchView(viewName) {
  state.activeView = viewName;

  // Update active nav class
  document.querySelectorAll('.nav-item').forEach(item => {
    if (item.getAttribute('data-view') === viewName) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });

  // Update active view container
  document.querySelectorAll('.view-container').forEach(container => {
    if (container.id === `view-${viewName}`) {
      container.classList.add('active');
    } else {
      container.classList.remove('active');
    }
  });

  // Update Topbar headline
  const titles = {
    'chat': { title: 'AI Copilot & Multi-Agent Assistant', desc: 'Ask any question, audit content, or prepare for interviews' },
    'ats': { title: 'ATS Scanner & Structural Audit', desc: 'Comprehensive ATS score breakdown, section detection & suggestions' },
    'jd': { title: 'Job Description Match & Placement Eligibility', desc: 'Real-time semantic matching, skill gap matrix & placement verdict' },
    'interview': { title: 'Interview Preparation Studio', desc: 'Generate grounded technical, project, and behavioral interview questions' },
    'coding': { title: 'Coding & DSA Practice Roadmap', desc: 'Personalized competitive programming topics grounded in candidate skills' },
    'career': { title: 'Career Trajectory & Role Advisor', desc: 'Discover optimal career roles based on verified resume credentials' },
    'compare': { title: 'Candidate Leaderboard & Comparison', desc: 'Benchmark and rank all uploaded resumes against benchmarks or JDs' },
    'profile': { title: 'Resume Memory & Extracted Knowledge', desc: 'Inspect candidate profile memory, parsed entities, and vector chunks' }
  };

  const info = titles[viewName] || { title: 'ResumeIQ SaaS', desc: 'Enterprise Resume Intelligence' };
  document.getElementById('topbar-title').textContent = info.title;
  document.getElementById('topbar-desc').textContent = info.desc;

  // Trigger view-specific loads
  if (viewName === 'ats') {
    runATSAudit();
  } else if (viewName === 'compare') {
    runResumeComparison();
  } else if (viewName === 'profile') {
    loadProfileDetails();
  }
}

// ==========================================================================
// Sample Resume Loader
// ==========================================================================
async function loadSampleResume() {
  const btn = document.getElementById('btn-load-sample');
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span>Loading Demo...</span>`;
  btn.disabled = true;

  try {
    const res = await fetch(buildApiUrl('/api/load-sample'), { method: 'POST' });
    const data = await res.json();
    
    if (res.ok && data.success) {
      showToast(data.message, 'success');
      await fetchSystemStatus();
      if (state.activeView === 'ats') runATSAudit();
    } else {
      showToast(data.detail || 'Failed to load sample resume', 'error');
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
  const btnToggleJD = document.getElementById('btn-toggle-chat-jd');
  const jdDrawer = document.getElementById('chat-jd-drawer');
  const btnResetSession = document.getElementById('btn-reset-chat');

  // Mode Pills
  const pills = document.querySelectorAll('.mode-pill');
  pills.forEach(pill => {
    pill.addEventListener('click', () => {
      pills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeMode = pill.getAttribute('data-mode');
    });
  });

  // JD Drawer Toggle
  if (btnToggleJD && jdDrawer) {
    btnToggleJD.addEventListener('click', () => {
      jdDrawer.classList.toggle('open');
      btnToggleJD.classList.toggle('active');
    });
  }

  // Sample JD helper in chat
  const chatSampleBtn = document.getElementById('btn-chat-sample-jd');
  if (chatSampleBtn) {
    chatSampleBtn.addEventListener('click', () => {
      const textarea = document.getElementById('chat-jd-textarea');
      textarea.value = SAMPLE_JDS.fullstack;
      state.jobDescription = SAMPLE_JDS.fullstack;
      showToast('Sample Fullstack JD attached', 'info');
    });
  }

  // Quick Prompt Chips
  const chips = document.querySelectorAll('.prompt-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      const prompt = chip.getAttribute('data-prompt');
      const mode = chip.getAttribute('data-mode') || 'auto';
      
      // Activate mode pill
      pills.forEach(p => {
        if (p.getAttribute('data-mode') === mode) {
          p.classList.add('active');
        } else {
          p.classList.remove('active');
        }
      });
      state.activeMode = mode;

      chatInput.value = prompt;
      sendChatMessage();
    });
  });

  // Send Message on click or Enter
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

    // Auto-grow textarea
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });
  }

  if (btnResetSession) {
    btnResetSession.addEventListener('click', async () => {
      try {
        await fetch(buildApiUrl('/api/reset-session'), { method: 'POST' });
        state.chatHistory = [];
        clearPersistedChatHistory();
        showToast('Chat session memory cleared', 'info');
        const history = document.getElementById('chat-history-container');
        history.innerHTML = '';
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

  if (state.chatHistory.length) {
    restorePersistedChatHistory();
    return;
  }

  history.innerHTML = `
    <div class="chat-welcome" id="chat-welcome-screen">
      <div class="welcome-icon-box">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
      </div>
      <h2>What would you like to analyze?</h2>
      <p>CampusOS ResumeIQ leverages 6 specialized AI sub-agents with strict guardrails and memory grounding.</p>
      
      <div class="prompt-chips-grid">
        <div class="prompt-chip" data-prompt="Give me a comprehensive professional review of my resume and identify top improvements." data-mode="1">
          <div class="chip-tag">Resume Review</div>
          <div class="chip-title">Comprehensive Resume Review</div>
          <div class="chip-desc">Detailed strengths, weaknesses, and structure check</div>
        </div>

        <div class="prompt-chip" data-prompt="Am I eligible for this role? Check my match percentage, matched skills, and missing skills." data-mode="2">
          <div class="chip-tag">Eligibility Check</div>
          <div class="chip-title">Placement Eligibility Audit</div>
          <div class="chip-desc">Evaluate criteria against Job Description</div>
        </div>

        <div class="prompt-chip" data-prompt="What are my critical skill gaps for the provided job description, and how should I prioritize learning them?" data-mode="3">
          <div class="chip-tag">Skill Gap</div>
          <div class="chip-title">Skill Gap & Learning Roadmap</div>
          <div class="chip-desc">Pinpoint missing technologies & action plan</div>
        </div>

        <div class="prompt-chip" data-prompt="Generate tailored technical and behavioral interview questions based strictly on my resume projects." data-mode="4">
          <div class="chip-tag">Interview Prep</div>
          <div class="chip-title">Tailored Interview Questions</div>
          <div class="chip-desc">Project architecture & domain deep-dives</div>
        </div>
      </div>
    </div>
  `;
  
  // Reattach click events for newly rendered chips
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
  if (state.isChatProcessing) return;

  const chatInput = document.getElementById('chat-input-textarea');
  const question = chatInput.value.trim();
  if (!question) return;

  if (state.loadedResumes.length === 0) {
    showToast('Please upload or load a sample resume first!', 'warning');
    openUploadModal();
    return;
  }

  // Remove welcome screen if present
  const welcome = document.getElementById('chat-welcome-screen');
  if (welcome) welcome.remove();

  const history = document.getElementById('chat-history-container');

  // Append User Message
  appendUserMessage(question);
  chatInput.value = '';
  chatInput.style.height = 'auto';

  // Append Thinking Indicator
  const thinkingId = 'thinking-' + Date.now();
  appendThinkingIndicator(thinkingId);
  history.scrollTop = history.scrollHeight;

  state.isChatProcessing = true;
  document.getElementById('btn-chat-send').disabled = true;

  // Retrieve JD from drawer if present
  const jdTextarea = document.getElementById('chat-jd-textarea');
  const jdContent = jdTextarea ? jdTextarea.value.trim() : '';

  try {
    const res = await fetch(buildApiUrl('/api/chat'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question,
        job_description: jdContent || null,
        mode: state.activeMode === 'auto' ? null : state.activeMode,
        filename: state.activeResume || null
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
    state.isChatProcessing = false;
    document.getElementById('btn-chat-send').disabled = false;
    history.scrollTop = history.scrollHeight;
  }
}

function appendUserMessage(text, options = {}) {
  const history = document.getElementById('chat-history-container');
  const timestamp = options.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg user';
  msgEl.innerHTML = `
    <div class="msg-avatar">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
        <circle cx="12" cy="7" r="4"></circle>
      </div>
    <div class="msg-body">
      <div class="msg-bubble">${escapeHtml(text)}</div>
      <div class="msg-meta">
        <span>You</span> • <span>${timestamp}</span>
      </div>
    </div>
  `;
  history.appendChild(msgEl);

  if (!options.skipSave) {
    state.chatHistory.push({ type: 'user', text, time: timestamp });
    savePersistedChatHistory();
  }
}

function appendAssistantMessage(rawText, modeName, isGuardrail, options = {}) {
  const history = document.getElementById('chat-history-container');
  const timestamp = options.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg assistant';

  // Render markdown with marked.js
  let parsedContent = '';
  try {
    parsedContent = typeof marked !== 'undefined' ? marked.parse(rawText) : rawText;
  } catch (e) {
    parsedContent = rawText;
  }

  const modeBadge = modeName ? `<span class="mode-badge-tag">${modeName}</span>` : '';
  const copyBtnId = 'copy-' + Date.now();

  msgEl.innerHTML = `
    <div class="msg-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
    </div>
    <div class="msg-body">
      <div class="msg-bubble markdown-body">${parsedContent}</div>
      <div class="msg-meta">
        ${modeBadge}
        <span>CampusOS Agent</span> • 
        <span>${timestamp}</span>
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

  if (!options.skipSave) {
    state.chatHistory.push({ type: 'assistant', text: rawText, modeName: modeName || 'Career Agent', guardrail: Boolean(isGuardrail), time: timestamp });
    savePersistedChatHistory();
  }

  // Attach copy handler
  document.getElementById(copyBtnId).addEventListener('click', () => {
    navigator.clipboard.writeText(rawText);
    showToast('Response copied to clipboard', 'info');
  });
}

function appendThinkingIndicator(id) {
  const history = document.getElementById('chat-history-container');
  const el = document.createElement('div');
  el.className = 'chat-msg assistant';
  el.id = id;
  el.innerHTML = `
    <div class="msg-avatar">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
      </svg>
    </div>
    <div class="msg-body">
      <div class="thinking-box">
        <div class="pulsing-dots">
          <span></span><span></span><span></span>
        </div>
        <span>Agent reasoning and retrieving resume evidence...</span>
      </div>
    </div>
  `;
  history.appendChild(el);
}

// ==========================================================================
// VIEW 2: ATS Scanner & Audit View
// ==========================================================================
async function runATSAudit() {
  if (!state.activeResume && state.loadedResumes.length > 0) {
    state.activeResume = state.loadedResumes[0].filename;
  }

  if (!state.activeResume) {
    showToast('Please upload a resume first to run ATS scan', 'warning');
    return;
  }

  const container = document.getElementById('ats-results-container');
  container.style.opacity = '0.5';

  try {
    const res = await fetch(buildApiUrl('/api/ats-audit'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: state.activeResume })
    });

    const result = await res.json();
    container.style.opacity = '1';

    if (res.ok && result.success) {
      renderATSAudit(result.data);
    } else {
      showToast(result.detail || 'ATS scan failed', 'error');
    }
  } catch (err) {
    console.error('ATS audit error:', err);
    container.style.opacity = '1';
    showToast('Failed to connect to ATS engine', 'error');
  }
}

function renderATSAudit(data) {
  state.atsData = data;

  // Animate Radial Gauge
  const score = data.ats_score || 0;
  const progressCircle = document.getElementById('ats-gauge-circle');
  const scoreValueEl = document.getElementById('ats-score-display');
  const gradePill = document.getElementById('ats-grade-pill');
  const gradeHeadline = document.getElementById('ats-grade-headline');
  const gradeDesc = document.getElementById('ats-grade-desc');

  // Gauge calculation: Circumference = 2 * PI * r = 2 * 3.14159 * 70 ≈ 440
  const maxDash = 440;
  const offset = maxDash - (score / 100) * maxDash;
  
  if (progressCircle) {
    progressCircle.style.strokeDashoffset = offset;
    // Set color based on score
    if (score >= 80) progressCircle.style.stroke = '#10b981';
    else if (score >= 60) progressCircle.style.stroke = '#06b6d4';
    else if (score >= 40) progressCircle.style.stroke = '#f59e0b';
    else progressCircle.style.stroke = '#f43f5e';
  }

  if (scoreValueEl) {
    animateScoreCounter(scoreValueEl, 0, score, 1000);
  }

  if (gradePill) {
    gradePill.className = `ats-grade-pill ${data.grade_color || 'blue'}`;
    gradePill.textContent = `Grade ${data.grade}: ${data.grade_label}`;
  }

  if (gradeHeadline) {
    gradeHeadline.textContent = `${data.filename || state.activeResume} — ATS Health Analysis`;
  }

  if (gradeDesc) {
    gradeDesc.textContent = `Scored ${score}/100 based on structural section completeness, keyword indexing, contact detection, and project density.`;
  }

  // Quick stats
  document.getElementById('stat-email').innerHTML = data.has_email 
    ? '<span class="stat-icon" style="color: var(--success);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg></span> Email Verified' 
    : '<span class="stat-icon" style="color: var(--danger);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></span> Email Missing';
    
  document.getElementById('stat-phone').innerHTML = data.has_phone 
    ? '<span class="stat-icon" style="color: var(--success);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg></span> Phone Verified' 
    : '<span class="stat-icon" style="color: var(--danger);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></span> Phone Missing';
    
  document.getElementById('stat-grad').innerHTML = data.graduation_year 
    ? `<span class="stat-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 10v6M2 10l10-5 10 5-10 5z"></path><path d="M6 12v5c3 3 9 3 12 0v-5"></path></svg></span> Grad Year: ${data.graduation_year}` 
    : '<span class="stat-icon" style="color: var(--warning);"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg></span> Grad Year Unclear';
    
  document.getElementById('stat-projects').innerHTML = `<span class="stat-icon"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path></svg></span> Projects Detected: ${data.project_count}`;

  // Detected Sections List
  const detectedList = document.getElementById('ats-detected-sections');
  detectedList.innerHTML = '';
  (data.detected_sections || []).forEach(sec => {
    const span = document.createElement('span');
    span.className = 'tag-badge detected';
    span.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline-block;vertical-align:middle;margin-right:2px;"><polyline points="20 6 9 17 4 12"></polyline></svg> ${sec.toUpperCase()}`;
    detectedList.appendChild(span);
  });

  // Missing Sections List
  const missingList = document.getElementById('ats-missing-sections');
  missingList.innerHTML = '';
  if (data.missing_sections && data.missing_sections.length > 0) {
    data.missing_sections.forEach(sec => {
      const span = document.createElement('span');
      span.className = 'tag-badge missing';
      span.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline-block;vertical-align:middle;margin-right:2px;"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg> ${sec.toUpperCase()}`;
      missingList.appendChild(span);
    });
  } else {
    missingList.innerHTML = '<span class="tag-badge detected"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="display:inline-block;vertical-align:middle;margin-right:2px;"><polyline points="20 6 9 17 4 12"></polyline></svg> All core sections present</span>';
  }

  // Suggestions List
  const suggestionsList = document.getElementById('ats-suggestions-list');
  suggestionsList.innerHTML = '';
  if (data.suggestions && data.suggestions.length > 0) {
    data.suggestions.forEach(sug => {
      const item = document.createElement('div');
      item.className = 'suggestion-item';
      item.innerHTML = `
        <div class="suggestion-bullet"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg></div>
        <div>${escapeHtml(sug)}</div>
      `;
      suggestionsList.appendChild(item);
    });
  } else {
    suggestionsList.innerHTML = `
      <div class="suggestion-item">
        <div class="suggestion-bullet" style="color: var(--success);"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg></div>
        <div>Outstanding resume format! No high-priority structural issues detected.</div>
      </div>
    `;
  }
}

// ==========================================================================
// VIEW 3: Job Description Match & Placement Checker
// ==========================================================================
function initJDEvents() {
  const btnRunMatch = document.getElementById('btn-run-jd-match');
  const jdTextarea = document.getElementById('jd-main-textarea');
  
  // Sample JD buttons
  document.querySelectorAll('.btn-sample-jd').forEach(btn => {
    btn.addEventListener('click', () => {
      const type = btn.getAttribute('data-sample');
      if (SAMPLE_JDS[type]) {
        jdTextarea.value = SAMPLE_JDS[type];
        state.jobDescription = SAMPLE_JDS[type];
        showToast(`Loaded sample ${type} Job Description`, 'info');
      }
    });
  });

  if (btnRunMatch) {
    btnRunMatch.addEventListener('click', runJDMatch);
  }
}

async function runJDMatch() {
  const jdText = document.getElementById('jd-main-textarea').value.trim();
  if (!jdText) {
    showToast('Please paste a Job Description first', 'warning');
    return;
  }

  if (!state.activeResume && state.loadedResumes.length > 0) {
    state.activeResume = state.loadedResumes[0].filename;
  }

  if (!state.activeResume) {
    showToast('Please upload a resume first', 'warning');
    return;
  }

  const btn = document.getElementById('btn-run-jd-match');
  const originalText = btn.innerHTML;
  btn.innerHTML = `<span>Calculating Semantic Match...</span>`;
  btn.disabled = true;

  try {
    const res = await fetch(buildApiUrl('/api/jd-match'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_description: jdText,
        filename: state.activeResume
      })
    });

    const result = await res.json();
    if (res.ok && result.success) {
      renderJDMatchResults(result.data);
      showToast('Match calculation complete!', 'success');
    } else {
      showToast(result.detail || 'Matching failed', 'error');
    }
  } catch (err) {
    console.error('JD Match error:', err);
    showToast('Error connecting to matching service', 'error');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

function renderJDMatchResults(data) {
  state.jdMatchData = data;
  const panel = document.getElementById('jd-results-panel');
  panel.style.display = 'flex';

  // Eligibility Badge
  const elBadge = document.getElementById('jd-eligibility-badge');
  elBadge.className = `ats-grade-pill ${data.eligibility_badge === 'success' ? 'emerald' : data.eligibility_badge === 'warning' ? 'amber' : 'rose'}`;
  elBadge.textContent = `${data.eligibility} (${data.final_match}%)`;

  document.getElementById('jd-eligibility-desc').textContent = data.eligibility_desc;

  // Metric Bars & Values
  document.getElementById('metric-final-match').textContent = `${data.final_match}%`;
  document.getElementById('bar-final-match').style.width = `${data.final_match}%`;
  document.getElementById('bar-final-match').style.background = data.final_match >= 70 ? 'var(--success)' : data.final_match >= 40 ? 'var(--warning)' : 'var(--danger)';

  document.getElementById('metric-skills-match').textContent = `${data.skills_match}%`;
  document.getElementById('bar-skills-match').style.width = `${data.skills_match}%`;
  document.getElementById('bar-skills-match').style.background = 'var(--accent-cyan)';

  document.getElementById('metric-overall-match').textContent = `${data.overall_match}%`;
  document.getElementById('bar-overall-match').style.width = `${data.overall_match}%`;
  document.getElementById('bar-overall-match').style.background = 'var(--primary)';

  // Matched Skills
  const matchedContainer = document.getElementById('jd-matched-skills-list');
  matchedContainer.innerHTML = '';
  if (data.matched_skills && data.matched_skills.length > 0) {
    data.matched_skills.forEach(skill => {
      const span = document.createElement('span');
      span.className = 'skill-pill matched';
      span.textContent = skill;
      matchedContainer.appendChild(span);
    });
  } else {
    matchedContainer.innerHTML = '<span style="color: var(--text-dim); font-size: 12px;">No direct skill keywords matched</span>';
  }

  // Missing Skills
  const missingContainer = document.getElementById('jd-missing-skills-list');
  missingContainer.innerHTML = '';
  if (data.missing_skills && data.missing_skills.length > 0) {
    data.missing_skills.forEach(skill => {
      const span = document.createElement('span');
      span.className = 'skill-pill missing';
      span.textContent = skill;
      missingContainer.appendChild(span);
    });
  } else {
    missingContainer.innerHTML = '<span class="skill-pill matched">Perfect Skill Coverage</span>';
  }

  // Feedback Text (Markdown rendered)
  const feedbackEl = document.getElementById('jd-feedback-text');
  try {
    feedbackEl.innerHTML = typeof marked !== 'undefined' ? marked.parse(data.feedback) : data.feedback;
  } catch (e) {
    feedbackEl.textContent = data.feedback;
  }
}

// ==========================================================================
// VIEW 4, 5, 6: Specialized Agent Studios (Interview, Coding, Career)
// ==========================================================================
function initInterviewStudio() {
  const startBtn = document.getElementById('interview-start-btn');
  const submitBtn = document.getElementById('interview-submit-btn');
  const answer = document.getElementById('interview-answer');
  const voiceBtn = document.getElementById('interview-voice-btn');
  const endBtn = document.getElementById('interview-end-btn');

  if (startBtn) startBtn.addEventListener('click', startInterview);
  if (submitBtn) submitBtn.addEventListener('click', submitInterviewAnswer);
  if (endBtn) endBtn.addEventListener('click', finishInterview);
  if (answer) answer.addEventListener('input', () => {
    const count = answer.value.trim() ? answer.value.trim().split(/\s+/).length : 0;
    document.getElementById('interview-word-count').textContent = `${count} words`;
  });
  if (voiceBtn) voiceBtn.addEventListener('click', toggleInterviewVoice);
}

async function startInterview() {
  if (!state.activeResume) {
    showToast('Upload or load a resume before starting the interview.', 'warning');
    openUploadModal();
    return;
  }

  const role = document.getElementById('interview-role').value.trim();
  const startBtn = document.getElementById('interview-start-btn');
  startBtn.disabled = true;
  startBtn.querySelector('span').textContent = 'Building questions...';

  try {
    const res = await fetch(buildApiUrl('/api/interview/start'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        filename: state.activeResume,
        role: role || 'target role',
        interview_type: document.getElementById('interview-type').value,
        difficulty: document.getElementById('interview-difficulty').value,
        question_count: parseInt(document.getElementById('interview-count').value, 10),
        job_description: document.getElementById('interview-jd').value.trim() || null
      })
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Could not start interview');

    state.interview = {sessionId: data.session_id, total: data.total_questions, index: 0};
    document.getElementById('interview-setup').classList.add('hidden');
    document.getElementById('interview-session').classList.remove('hidden');
    document.getElementById('interview-report').classList.add('hidden');
    document.getElementById('interview-session-title').textContent = `Interview for ${role || 'your target role'}`;
    document.getElementById('interview-active-resume').textContent = state.activeResume;
    renderInterviewQuestion(data.question, data.question_index, data.total_questions);
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    startBtn.disabled = false;
    startBtn.querySelector('span').textContent = 'Start interview';
  }
}

function renderInterviewQuestion(question, index, total) {
  clearInterval(state.interviewTimer);
  state.interview.index = index;
  document.getElementById('interview-progress-label').textContent = `Question ${index + 1} of ${total}`;
  document.getElementById('interview-progress-bar').style.width = `${((index + 1) / total) * 100}%`;
  document.getElementById('interview-question-category').textContent = question.category || 'Interview';
  document.getElementById('interview-question-focus').textContent = question.focus || 'Candidate response';
  document.getElementById('interview-question-text').textContent = question.question;
  document.getElementById('interview-answer').value = '';
  document.getElementById('interview-word-count').textContent = '0 words';
  document.getElementById('interview-answer-feedback').classList.add('hidden');
  document.getElementById('interview-submit-btn').disabled = false;

  state.interviewSeconds = question.time_seconds || 60;
  updateInterviewTimer();
  state.interviewTimer = setInterval(() => {
    state.interviewSeconds -= 1;
    updateInterviewTimer();
  }, 1000);
}

function updateInterviewTimer() {
  const seconds = Math.max(0, state.interviewSeconds);
  const minutes = Math.floor(seconds / 60);
  document.getElementById('interview-timer').textContent = `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`;
}

function toggleInterviewVoice() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast('Voice capture is not supported in this browser.', 'warning');
    return;
  }
  if (state.interviewRecognition) {
    state.interviewRecognition.stop();
    return;
  }

  const recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';
  const answer = document.getElementById('interview-answer');
  const voiceBtn = document.getElementById('interview-voice-btn');
  recognition.onstart = () => {
    state.interviewRecognition = recognition;
    voiceBtn.classList.add('recording');
    voiceBtn.querySelector('span').textContent = 'Listening...';
  };
  recognition.onresult = (event) => {
    let transcript = '';
    for (let i = event.resultIndex; i < event.results.length; i++) transcript += event.results[i][0].transcript;
    if (transcript) answer.value = (answer.value + ' ' + transcript).trim();
    answer.dispatchEvent(new Event('input'));
  };
  recognition.onend = () => {
    state.interviewRecognition = null;
    voiceBtn.classList.remove('recording');
    voiceBtn.querySelector('span').textContent = 'Use microphone';
  };
  recognition.start();
}

async function submitInterviewAnswer() {
  if (!state.interview) return;
  const answer = document.getElementById('interview-answer').value.trim();
  if (!answer) {
    showToast('Add an answer before submitting.', 'warning');
    document.getElementById('interview-answer').focus();
    return;
  }

  const submitBtn = document.getElementById('interview-submit-btn');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Evaluating...';

  try {
    const res = await fetch(buildApiUrl('/api/interview/answer'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: state.interview.sessionId, answer})
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Answer evaluation failed');

    renderAnswerFeedback(data.evaluation);
    clearInterval(state.interviewTimer);
    setTimeout(() => {
      if (data.has_next) renderInterviewQuestion(data.question, data.question_index, data.total_questions);
      else finishInterview();
    }, 1800);
  } catch (error) {
    showToast(error.message, 'error');
  } finally {
    submitBtn.innerHTML = 'Submit answer <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  }
}

function renderAnswerFeedback(evaluation) {
  const container = document.getElementById('interview-answer-feedback');
  const strengths = (evaluation.strengths || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
  const improvements = (evaluation.improvements || []).map(item => `<li>${escapeHtml(item)}</li>`).join('');
  container.innerHTML = `<div class="feedback-score"><strong>${evaluation.score || 0}</strong><span>/100</span></div><div class="feedback-copy"><strong>${escapeHtml(evaluation.summary || 'Answer evaluated.')}</strong><div class="feedback-columns"><div><span>Strengths</span><ul>${strengths}</ul></div><div><span>Improve next</span><ul>${improvements}</ul></div></div></div>`;
  container.classList.remove('hidden');
}

async function finishInterview() {
  if (!state.interview) return;
  clearInterval(state.interviewTimer);
  if (state.interviewRecognition) state.interviewRecognition.stop();

  try {
    const res = await fetch(buildApiUrl('/api/interview/finish'), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({session_id: state.interview.sessionId})
    });
    const data = await res.json();
    if (!res.ok || !data.success) throw new Error(data.detail || 'Could not generate report');
    renderInterviewReport(data);
  } catch (error) {
    showToast(error.message, 'error');
  }
}

function renderInterviewReport(data) {
  document.getElementById('interview-session').classList.add('hidden');
  const report = document.getElementById('interview-report');
  const verdict = data.overall_score >= 80 ? 'Strong Hire Potential' : data.overall_score >= 60 ? 'Promising — Polish Required' : 'More Practice Recommended';
  const categories = Object.entries(data.category_scores || {}).map(([name, score]) => `<div class="report-category"><div><span>${escapeHtml(name)}</span><strong>${score}%</strong></div><div class="report-bar"><span style="width:${score}%"></span></div></div>`).join('');
  report.innerHTML = `<div class="report-header"><div><span>INTERVIEW REPORT</span><h2>${escapeHtml(data.candidate_name)} · ${escapeHtml(data.role)}</h2></div><button id="interview-restart-btn" class="interview-start-btn"><span>Practice again</span></button></div><div class="report-grid"><div class="report-score-card"><div class="report-ring" style="--score:${data.overall_score * 3.6}deg"><strong>${data.overall_score}</strong><span>/100</span></div><div><span>Overall performance</span><h3>${verdict}</h3><p>${data.answered} of ${data.total_questions} questions answered</p></div></div><div class="report-categories"><h3>Competency breakdown</h3>${categories}</div></div><div class="report-answers"><h3>Response review</h3>${data.responses.map((item, index) => `<article><div class="response-index">${index + 1}</div><div><span>${escapeHtml(item.question.category || 'Interview')}</span><h4>${escapeHtml(item.question.question)}</h4><p>${escapeHtml(item.answer)}</p><strong>${item.evaluation.score}/100 · ${escapeHtml(item.evaluation.summary || '')}</strong></div></article>`).join('')}</div>`;
  report.classList.remove('hidden');
  document.getElementById('interview-restart-btn').addEventListener('click', () => {
    report.classList.add('hidden');
    document.getElementById('interview-setup').classList.remove('hidden');
  });
}

// ==========================================================================
// VIEW 7: Multi-Candidate Leaderboard & Comparison
// ==========================================================================
async function runResumeComparison() {
  const tbody = document.getElementById('compare-table-body');
  if (!tbody) return;

  if (state.loadedResumes.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">No resumes uploaded yet. Upload resumes to benchmark candidates.</td></tr>`;
    return;
  }

  tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">Analyzing and comparing candidates...</td></tr>`;

  try {
    const jdText = document.getElementById('jd-textarea')?.value?.trim() || state.jobDescription || '';
    const res = await fetch(buildApiUrl('/api/compare-resumes'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_description: jdText })
    });
    const data = await res.json();
    if (!res.ok || !data.success) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: #f43f5e;">${escapeHtml(data.detail || 'Failed to compare resumes')}</td></tr>`;
      return;
    }

    if (!data.ranking || data.ranking.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">No candidates to compare.</td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    data.ranking.forEach(c => {
      const tr = document.createElement('tr');
      const isSelected = c.filename === state.activeResume;
      const matchedChips = (c.matched_sample || []).map(s => `<span class="skill-pill matched" style="font-size:10px; padding:2px 6px;">${escapeHtml(s)}</span>`).join(' ') || '<span style="color:var(--text-dim); font-size:11px;">None</span>';
      const missingChips = (c.missing_sample || []).map(s => `<span class="skill-pill missing" style="font-size:10px; padding:2px 6px;">${escapeHtml(s)}</span>`).join(' ') || '<span style="color:var(--text-dim); font-size:11px;">None</span>';

      tr.innerHTML = `
        <td><strong style="color:var(--primary); font-size:14px;">#${c.rank}</strong></td>
        <td>
          <div style="font-weight:600; color:var(--text-main);">${escapeHtml(c.candidate_name)}</div>
          <div style="font-size:11px; color:var(--text-dim);">${escapeHtml(c.filename)}</div>
        </td>
        <td>
          <span class="tag-badge detected" style="font-size:12px; font-weight:700;">${c.score}%</span>
          <span style="font-size:11px; color:var(--text-dim); margin-left:4px;">${escapeHtml(c.verdict || '')}</span>
        </td>
        <td><div style="display:flex; flex-wrap:wrap; gap:4px; max-width:220px;">${matchedChips}</div></td>
        <td><div style="display:flex; flex-wrap:wrap; gap:4px; max-width:220px;">${missingChips}</div></td>
        <td>
          <button class="btn ${isSelected ? 'btn-primary' : 'btn-secondary'} btn-sm select-candidate-btn" data-filename="${escapeHtml(c.filename)}">
            ${isSelected ? 'Active' : 'Select'}
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.select-candidate-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const fn = e.currentTarget.getAttribute('data-filename');
        if (fn) {
          state.activeResume = fn;
          updateResumeDropdowns();
          handleResumeChanged();
          runResumeComparison();
        }
      });
    });

  } catch (err) {
    console.error('Compare error:', err);
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: #f43f5e;">Error connecting to comparison service.</td></tr>`;
  }
}

// Upload Modal Helper: Format file size
function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

// Upload Modal Helper: Render selected files in preview list
function renderSelectedFiles(files) {
  const container = document.getElementById('upload-file-list');
  if (!container) return;
  container.innerHTML = '';
  if (!files || files.length === 0) return;

  Array.from(files).forEach(file => {
    const ext = file.name.split('.').pop().toLowerCase();
    const isSupported = ext === 'pdf' || ext === 'docx';
    const item = document.createElement('div');
    item.className = 'file-preview-item';
    item.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:16px;">${ext === 'pdf' ? '📕' : '📄'}</span>
        <div>
          <strong style="color:var(--text-main); font-size:12px;">${escapeHtml(file.name)}</strong>
          <span style="color:var(--text-dim); font-size:11px; margin-left:6px;">(${formatFileSize(file.size)})</span>
        </div>
      </div>
      <span class="tag-badge" style="${isSupported ? 'background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid rgba(34,197,94,0.3);' : 'background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3);'}">
        ${isSupported ? 'Ready' : 'Unsupported'}
      </span>
    `;
    container.appendChild(item);
  });
}

// Upload Modal Initialization and Handling
function initUploadModal() {
  const modal = document.getElementById('upload-modal');
  const openBtn = document.getElementById('btn-open-upload');
  const closeBtn = document.getElementById('btn-close-upload');
  const dropzone = document.getElementById('dropzone-input');
  const fileInput = document.getElementById('file-upload-element');
  const submitBtn = document.getElementById('btn-submit-upload');

  window.openUploadModal = () => {
    if (modal) {
      modal.classList.add('open');
      const progressPanel = document.getElementById('upload-progress-panel');
      if (progressPanel) progressPanel.style.display = 'none';
      const fileList = document.getElementById('upload-file-list');
      if (fileList) fileList.innerHTML = '';
      if (fileInput) fileInput.value = '';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Index Documents';
      }
    }
  };

  window.closeUploadModal = () => {
    if (modal) {
      modal.classList.remove('open');
      const progressPanel = document.getElementById('upload-progress-panel');
      if (progressPanel) progressPanel.style.display = 'none';
      const fileList = document.getElementById('upload-file-list');
      if (fileList) fileList.innerHTML = '';
      if (fileInput) fileInput.value = '';
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Index Documents';
      }
    }
  };

  if (openBtn) openBtn.addEventListener('click', window.openUploadModal);
  if (closeBtn) closeBtn.addEventListener('click', window.closeUploadModal);

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        fileInput.files = e.dataTransfer.files;
        renderSelectedFiles(fileInput.files);
      }
    });

    fileInput.addEventListener('change', () => {
      renderSelectedFiles(fileInput.files);
    });
  }

  if (submitBtn) submitBtn.addEventListener('click', uploadSelectedResumes);
}

async function uploadSelectedResumes() {
  const fileInput = document.getElementById('file-upload-element');
  if (!fileInput || !fileInput.files.length) {
    showToast('Select at least one PDF or DOCX resume.', 'warning');
    return;
  }

  for (const file of fileInput.files) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx') {
      showToast(`File "${file.name}" is not supported. Please upload PDF or DOCX only.`, 'warning');
      return;
    }
  }

  const formData = new FormData();
  Array.from(fileInput.files).forEach(file => formData.append('files', file));
  const submitBtn = document.getElementById('btn-submit-upload');
  submitBtn.disabled = true;
  submitBtn.textContent = 'Uploading & Indexing...';

  const progressPanel = document.getElementById('upload-progress-panel');
  const progressLabel = document.getElementById('upload-progress-label');
  const progressPercent = document.getElementById('upload-progress-percent');
  const progressFill = document.getElementById('upload-progress-fill');

  if (progressPanel) {
    progressPanel.style.display = 'block';
    if (progressLabel) progressLabel.textContent = 'Uploading document(s)...';
    if (progressPercent) progressPercent.textContent = '35%';
    if (progressFill) progressFill.style.width = '35%';
  }

  try {
    const res = await fetch(buildApiUrl('/api/upload'), {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (progressFill) progressFill.style.width = '85%';
    if (progressLabel) progressLabel.textContent = 'Indexing in vector store...';
    if (progressPercent) progressPercent.textContent = '85%';

    if (res.ok && data.success) {
      if (progressFill) progressFill.style.width = '100%';
      if (progressPercent) progressPercent.textContent = '100%';
      if (progressLabel) progressLabel.textContent = 'Completed!';

      showToast(data.message || 'Resumes uploaded and indexed successfully!', 'success');

      // Refresh system status & reload resumes
      await fetchSystemStatus();

      if (data.loaded_files && data.loaded_files.length > 0) {
        state.activeResume = data.loaded_files[data.loaded_files.length - 1];
      } else if (data.resumes && data.resumes.length > 0) {
        state.loadedResumes = data.resumes;
        state.activeResume = data.resumes[data.resumes.length - 1].filename;
      }

      updateResumeDropdowns();
      updateStatusIndicators({ total_resumes: state.loadedResumes.length });

      if (state.activeView === 'ats') {
        runATSAudit();
      } else if (state.activeView === 'profile') {
        loadProfileDetails();
      } else if (state.activeView === 'compare') {
        runResumeComparison();
      }

      setTimeout(() => closeUploadModal(), 400);
    } else {
      showToast(data.detail || data.message || 'Upload failed', 'error');
    }
  } catch (err) {
    console.error('Upload error:', err);
    showToast('Error connecting to upload service', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = 'Index Documents';
  }
}

function animateScoreCounter(element, start, end, duration) {
  let startTime = null;
  const step = (timestamp) => {
    if (!startTime) startTime = timestamp;
    const progress = Math.min((timestamp - startTime) / duration, 1);
    element.textContent = Math.floor(progress * (end - start) + start);
    if (progress < 1) {
      window.requestAnimationFrame(step);
    } else {
      element.textContent = end;
    }
  };
  window.requestAnimationFrame(step);
}
