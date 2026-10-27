/**
 * CampusOS ResumeIQ - Single Page Application Engine
 * Vanilla JavaScript implementation with full reactivity and zero external bundlers
 */

const API_BASE = window.location.pathname.replace(/\/$/, "");

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
};

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
    const res = await fetch(`${API_BASE}/api/status`);
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
    const res = await fetch(`${API_BASE}/api/load-sample`, { method: 'POST' });
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
        await fetch(`${API_BASE}/api/reset-session`, { method: 'POST' });
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
    const res = await fetch(`${API_BASE}/api/chat`, {
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

function appendAssistantMessage(rawText, modeName, isGuardrail) {
  const history = document.getElementById('chat-history-container');
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
    const res = await fetch(`${API_BASE}/api/ats-audit`, {
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
    const res = await fetch(`${API_BASE}/api/jd-match`, {
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
function triggerStudioPrompt(mode, defaultPrompt) {
  // Switch to Chat tab, set mode, fill prompt, and execute
  switchView('chat');
  
  // Set mode pill
  document.querySelectorAll('.mode-pill').forEach(p => {
    if (p.getAttribute('data-mode') === mode) {
      p.classList.add('active');
    } else {
      p.classList.remove('active');
    }
  });
  state.activeMode = mode;

  const chatInput = document.getElementById('chat-input-textarea');
  chatInput.value = defaultPrompt;
  sendChatMessage();
}

// ==========================================================================
// VIEW 7: Multi-Resume Comparison & Leaderboard
// ==========================================================================
async function runResumeComparison() {
  const container = document.getElementById('compare-table-body');
  container.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-muted);">Benchmarking candidates across vector embeddings...</td></tr>`;

  const jdText = document.getElementById('compare-jd-input') ? document.getElementById('compare-jd-input').value.trim() : '';

  try {
    const res = await fetch(`${API_BASE}/api/compare-resumes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_description: jdText || null })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      renderLeaderboard(data.ranking, data.has_jd);
    } else {
      container.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--danger);">${data.detail || 'Failed to compare resumes'}</td></tr>`;
    }
  } catch (err) {
    console.error('Comparison error:', err);
    container.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--danger);">Error connecting to benchmark service</td></tr>`;
  }
}

function renderLeaderboard(ranking, hasJD) {
  const tbody = document.getElementById('compare-table-body');
  tbody.innerHTML = '';

  if (!ranking || ranking.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-dim);">No candidate resumes available to rank. Please upload resumes.</td></tr>`;
    return;
  }

  ranking.forEach((cand, idx) => {
    const tr = document.createElement('tr');
    let rankBadgeClass = idx === 0 ? 'gold' : idx === 1 ? 'silver' : idx === 2 ? 'bronze' : '';
    
    tr.innerHTML = `
      <td>
        <span class="rank-badge ${rankBadgeClass}">#${cand.rank}</span>
      </td>
      <td>
        <strong style="color: #fff;">${escapeHtml(cand.candidate_name)}</strong>
        <div style="font-size: 11px; color: var(--text-dim);">${escapeHtml(cand.filename)}</div>
      </td>
      <td>
        <div style="display: flex; align-items: center; gap: 8px;">
          <strong style="font-size: 15px; color: ${cand.score >= 70 ? 'var(--success)' : cand.score >= 40 ? 'var(--warning)' : 'var(--danger)'};">${cand.score}%</strong>
        </div>
      </td>
      <td>
        <span class="tag-badge detected">${cand.matched_count} ${hasJD ? 'Skills' : 'Sections'}</span>
      </td>
      <td>
        <span class="tag-badge missing">${cand.missing_count} Gaps</span>
      </td>
      <td>
        <button class="btn btn-secondary btn-sm" onclick="selectResumeAndChat('${escapeHtml(cand.filename)}')">
          Audit Profile
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function selectResumeAndChat(filename) {
  state.activeResume = filename;
  updateResumeDropdowns();
  switchView('chat');
  showToast(`Switched active candidate to: ${filename}`, 'info');
}

// ==========================================================================
// VIEW 8: Resume Data & Profile Memory
// ==========================================================================
async function loadProfileDetails() {
  if (!state.activeResume && state.loadedResumes.length > 0) {
    state.activeResume = state.loadedResumes[0].filename;
  }

  if (!state.activeResume) {
    showToast('No active resume selected', 'warning');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/api/resume-details?filename=${encodeURIComponent(state.activeResume)}`);
    const data = await res.json();

    if (res.ok && data.success) {
      document.getElementById('profile-candidate-name').textContent = data.candidate_name;
      document.getElementById('profile-filename').textContent = data.filename;
      document.getElementById('profile-words').textContent = `${data.word_count} words`;
      document.getElementById('profile-chars').textContent = `${data.char_count} characters`;

      // Profile Memory
      const summaryEl = document.getElementById('profile-memory-summary');
      summaryEl.textContent = data.profile_summary;

      // Raw Text
      const rawEl = document.getElementById('profile-raw-text');
      rawEl.textContent = data.raw_text_preview;
    }
  } catch (err) {
    console.error('Error loading profile details:', err);
  }
}

// ==========================================================================
// File Upload & Modal Handling
// ==========================================================================
function initUploadModal() {
  const modal = document.getElementById('upload-modal');
  const btnTrigger = document.getElementById('btn-open-upload');
  const btnClose = document.getElementById('btn-close-upload');
  const dropzone = document.getElementById('dropzone-input');
  const fileInput = document.getElementById('file-upload-element');
  const btnSubmit = document.getElementById('btn-submit-upload');

  let selectedFiles = [];

  if (btnTrigger) btnTrigger.addEventListener('click', openUploadModal);
  if (btnClose) btnClose.addEventListener('click', closeUploadModal);

  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeUploadModal();
  });

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
        showToast('Please select at least one PDF or DOCX file', 'warning');
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
        if (res.ok && data.success) {
          showToast(data.message, 'success');
          closeUploadModal();
          selectedFiles = [];
          updateUploadPreview([]);
          await fetchSystemStatus();
          if (state.activeView === 'ats') runATSAudit();
        } else {
          showToast(data.detail || 'Upload failed', 'error');
        }
      } catch (err) {
        console.error('Upload error:', err);
        showToast('Error uploading files', 'error');
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.innerHTML = `<span>Index Documents</span>`;
      }
    });
  }
}

function openUploadModal() {
  document.getElementById('upload-modal').classList.add('open');
}

function closeUploadModal() {
  document.getElementById('upload-modal').classList.remove('open');
}

function updateUploadPreview(files) {
  const listEl = document.getElementById('upload-file-list');
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

// ==========================================================================
// Toast Notifications
// ==========================================================================
function showToast(message, type = 'info') {
  const stack = document.getElementById('toast-stack');
  if (!stack) return;

  const toast = document.createElement('div');
  toast.className = `toast-msg ${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : type === 'warning' ? '!' : 'i';
  toast.innerHTML = `
    <span style="font-weight: bold;">${icon}</span>
    <span>${escapeHtml(message)}</span>
  `;

  stack.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ==========================================================================
// Utility Helpers
// ==========================================================================
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
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
