/**
 * CampusOS Attendance AI - SaaS Web Application Logic
 * Single Page Application JavaScript Controller
 */

// Parse URL Query Parameters if accessed from CampusOS Portal
const urlParams = new URLSearchParams(window.location.search);
const qName = urlParams.get("name") || urlParams.get("student_name");
const qEmail = urlParams.get("email") || urlParams.get("student_email");
const qCollegeId = urlParams.get("college_id");
const qClassroomId = urlParams.get("classroom_id");
const qPrn = urlParams.get("prn");

const API_BASE = window.location.pathname.replace(/\/$/, "");

// Application State
const state = {
  student: {
    name: qName || "demo",
    email: qEmail || "demo@gmail.com",
    college_id: qCollegeId ? parseInt(qCollegeId) : 1,
    classroom_id: qClassroomId ? parseInt(qClassroomId) : 6,
    prn: qPrn || "1234",
  },
  classroomName: "class_a",
  classTeacher: "omkarT",
  attendanceData: null,
  analyticsData: null,
  activeView: "overview",
  chatSessionId: "web-session-" + Math.random().toString(36).substring(2, 9),
  chatHistory: [],
  isChatLoading: false,
  calendar: {
    year: 2026,
    month: 2, // 0-indexed: 2 = March
  },
  selectedDate: null,
  targetPercentage: 75.0,
  theme: "light",
};

// API Client
const api = {
  async fetchAttendance(credentials = state.student) {
    const res = await fetch(`${API_BASE}/api/attendance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        student_name: credentials.name,
        student_email: credentials.email,
        college_id: parseInt(credentials.college_id),
        classroom_id: parseInt(credentials.classroom_id),
      }),
    });
    return await res.json();
  },

  async sendChatMessage(question) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.chatSessionId,
        question: question,
        student_name: state.student.name,
        student_email: state.student.email,
        college_id: parseInt(state.student.college_id),
        classroom_id: parseInt(state.student.classroom_id),
      }),
    });
    return await res.json();
  },

  async resetChat() {
    const res = await fetch(`${API_BASE}/api/chat/reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.chatSessionId }),
    });
    return await res.json();
  },

  async fetchAnalytics() {
    const params = new URLSearchParams({
      student_name: state.student.name,
      student_email: state.student.email,
      college_id: state.student.college_id,
      classroom_id: state.student.classroom_id,
    });
    const res = await fetch(`${API_BASE}/api/analytics?${params.toString()}`);
    return await res.json();
  },

  async fetchForecast(targetPct) {
    const summary = state.attendanceData ? state.attendanceData.summary : { present: 25, absent: 7 };
    const res = await fetch(`${API_BASE}/api/forecast`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        present: summary.present,
        absent: summary.absent,
        target_percentage: parseFloat(targetPct),
      }),
    });
    return await res.json();
  },
};

// UI Initializer
document.addEventListener("DOMContentLoaded", async () => {
  setupReturnNavigation();
  setupEventListeners();
  await loadApplicationData();
  setupInitialChatWelcome();
});

// Dynamic Return Navigation & CampusOS Header Sync
function setupReturnNavigation() {
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

// Load Attendance & Analytics Data
async function loadApplicationData() {
  showToast("Fetching student attendance data...", "info");
  try {
    const data = await api.fetchAttendance();
    if (data.success) {
      state.attendanceData = data;
      if (data.student) {
        state.student.name = data.student.name || state.student.name;
        state.student.email = data.student.email || state.student.email;
        state.student.prn = data.student.prn || state.student.prn;
      }
      state.classroomName = data.classroom_name || state.classroomName;
      state.classTeacher = data.class_teacher || state.classTeacher;

      // Update Student Profile Pill in UI
      updateStudentUI();

      // Render Dashboard
      renderDashboard();

      // Render Calendar
      renderCalendar();

      // Render Records Table
      renderRecordsTable();

      // Fetch and Render Analytics
      try {
        const analytics = await api.fetchAnalytics();
        state.analyticsData = analytics;
        renderAnalytics();
      } catch (err) {
        console.warn("Analytics fetch note:", err);
      }

      // Initial Simulator calculation
      updateSimulator();

      showToast("Attendance data synchronized", "success");
    } else {
      showToast(data.message || "Failed to load attendance", "error");
    }
  } catch (error) {
    console.error("Data load error:", error);
    showToast("Error connecting to backend server", "error");
  }
}

// Update Student Profile details in UI
function updateStudentUI() {
  document.querySelectorAll(".student-name-display").forEach((el) => {
    el.textContent = state.student.name;
  });
  document.querySelectorAll(".student-prn-display").forEach((el) => {
    el.textContent = `PRN: ${state.student.prn || "N/A"}`;
  });
  document.querySelectorAll(".student-class-display").forEach((el) => {
    el.textContent = `Class: ${state.classroomName} (College #${state.student.college_id})`;
  });

  const summary = state.attendanceData?.summary;
  if (summary) {
    const pct = summary.attendance_percentage;
    const statusPill = document.getElementById("header-status-pill");
    const statusText = document.getElementById("header-status-text");

    if (statusPill && statusText) {
      statusPill.className = "status-pill " + (pct >= 75 ? "good" : pct >= 65 ? "warning" : "danger");
      statusText.textContent = `${pct}% Attendance`;
    }
  }
}

// Render Dashboard View
function renderDashboard() {
  if (!state.attendanceData) return;
  const summary = state.attendanceData.summary;
  const pct = summary.attendance_percentage;

  // 1. Radial Gauge
  const gaugeFill = document.getElementById("hero-gauge-fill");
  const gaugeVal = document.getElementById("hero-gauge-value");
  if (gaugeFill && gaugeVal) {
    gaugeVal.textContent = `${pct}%`;
    const circumference = 2 * Math.PI * 60; // r=60 -> ~376.99
    const offset = circumference - (pct / 100) * circumference;
    gaugeFill.style.strokeDasharray = `${circumference}`;
    gaugeFill.style.strokeDashoffset = `${offset}`;
    gaugeFill.style.stroke = pct >= 75 ? "var(--present)" : pct >= 65 ? "var(--pending)" : "var(--absent)";
  }

  // 2. KPI Cards
  const kpiPresent = document.getElementById("kpi-present-count");
  const kpiAbsent = document.getElementById("kpi-absent-count");
  const kpiTotal = document.getElementById("kpi-total-count");
  const kpiSafeBunks = document.getElementById("kpi-safe-bunks");

  if (kpiPresent) kpiPresent.textContent = summary.present;
  if (kpiAbsent) kpiAbsent.textContent = summary.absent;
  if (kpiTotal) kpiTotal.textContent = summary.marked_slots;

  // Calculate Safe Bunks for 75%
  if (kpiSafeBunks) {
    if (pct >= 75) {
      const safe = Math.floor((100 * summary.present - 75 * summary.marked_slots) / 75);
      kpiSafeBunks.textContent = `${Math.max(0, safe)} Slots`;
    } else {
      kpiSafeBunks.textContent = "0 (Shortage)";
    }
  }

  // 3. Recent 5 Days List
  const recentList = document.getElementById("recent-days-container");
  if (recentList) {
    const attendance = state.attendanceData.attendance || {};
    const dates = Object.keys(attendance).sort().reverse().slice(0, 5);

    recentList.innerHTML = dates
      .map((dateStr) => {
        const dayRecord = attendance[dateStr];
        const slots = dayRecord.slots || [];
        const allPresent = slots.length > 0 && slots.every((s) => s.status === "present");
        const hasAbsent = slots.some((s) => s.status === "absent");
        const statusColor = allPresent ? "var(--present)" : hasAbsent ? "var(--absent)" : "var(--pending)";

        const slotChips = slots
          .map(
            (s) =>
              `<span class="slot-tag ${s.status}">
                ${s.slot}: ${s.status} (${s.teacher || "T"})
              </span>`
          )
          .join("");

        return `
        <div class="recent-day-row" onclick="jumpToDateDetails('${dateStr}')">
          <div class="day-date-info">
            <span class="day-status-indicator" style="background: ${statusColor}"></span>
            <span class="day-date-text">${formatDateFriendly(dateStr)}</span>
          </div>
          <div class="day-slots-preview">
            ${slotChips}
          </div>
        </div>
      `;
      })
      .join("");
  }
}

// Render Calendar View
function renderCalendar() {
  if (!state.attendanceData) return;
  const calGrid = document.getElementById("calendar-grid-days");
  const monthTitle = document.getElementById("cal-month-title");
  if (!calGrid) return;

  const { year, month } = state.calendar;
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];

  if (monthTitle) {
    monthTitle.textContent = `${monthNames[month]} ${year}`;
  }

  // First day of month and total days
  const firstDay = new Date(year, month, 1).getDay(); // 0 = Sunday
  const totalDays = new Date(year, month + 1, 0).getDate();

  const attendance = state.attendanceData.attendance || {};

  let cellsHtml = "";

  // Blank cells before first day
  for (let i = 0; i < firstDay; i++) {
    cellsHtml += `<div class="cal-cell empty"></div>`;
  }

  // Day cells
  for (let day = 1; day <= totalDays; day++) {
    const monthStr = String(month + 1).padStart(2, "0");
    const dayStr = String(day).padStart(2, "0");
    const dateKey = `${year}-${monthStr}-${dayStr}`;

    const record = attendance[dateKey];
    let dotsHtml = "";
    let summaryText = "";
    let isSelected = state.selectedDate === dateKey;

    if (record && record.slots && record.slots.length > 0) {
      dotsHtml = record.slots
        .map((s) => `<span class="status-dot ${s.status}"></span>`)
        .join("");

      const presentCount = record.slots.filter((s) => s.status === "present").length;
      summaryText = `${presentCount}/${record.slots.length} attended`;
    }

    cellsHtml += `
      <div class="cal-cell ${record ? "has-data" : ""} ${isSelected ? "selected" : ""}" 
           onclick="handleCalendarDateClick('${dateKey}')">
        <div class="cal-cell-top">
          <span class="cal-date-number">${day}</span>
          <div class="cal-dots-container">${dotsHtml}</div>
        </div>
        <div class="cal-cell-summary">${summaryText}</div>
      </div>
    `;
  }

  calGrid.innerHTML = cellsHtml;

  // Auto-select latest or first available date if not selected
  if (!state.selectedDate) {
    const dates = Object.keys(attendance).sort().reverse();
    if (dates.length > 0) {
      handleCalendarDateClick(dates[0]);
    }
  }
}

// Handle Calendar Date Selection
function handleCalendarDateClick(dateKey) {
  state.selectedDate = dateKey;
  renderCalendar(); // Re-render to update selected border

  const container = document.getElementById("selected-date-slots-container");
  const titleEl = document.getElementById("selected-date-title");
  if (!container) return;

  if (titleEl) {
    titleEl.textContent = `Date Breakdown: ${formatDateFriendly(dateKey)}`;
  }

  const attendance = state.attendanceData?.attendance || {};
  const record = attendance[dateKey];

  if (!record || !record.slots || record.slots.length === 0) {
    container.innerHTML = `
      <div style="padding: 20px; text-align: center; color: var(--text-muted);">
        No attendance sessions recorded for this date.
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="slots-timeline">
      ${record.slots
        .map(
          (s) => `
        <div class="slot-item-card ${s.status}">
          <div class="slot-time-header">
            <span><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline-block;vertical-align:middle;margin-right:4px;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>${s.slot}</span>
            <span class="slot-tag ${s.status}">${s.status.toUpperCase()}</span>
          </div>
          <div class="slot-teacher-info">
            <strong>Faculty:</strong> ${s.teacher || "Unassigned"}
          </div>
        </div>
      `
        )
        .join("")}
      ${
        record.audit && record.audit.length > 0
          ? `
        <div style="margin-top: 12px; font-size: 0.75rem; color: var(--text-muted);">
          <strong>Audit History:</strong> ${JSON.stringify(record.audit)}
        </div>`
          : ""
      }
    </div>
    <button class="header-action-btn primary" style="width: 100%; margin-top: 12px;" 
            onclick="askAIAboutDate('${dateKey}')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline-block;vertical-align:middle;margin-right:4px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
      <span>Ask AI about this day</span>
    </button>
  `;
}

// Calendar Month Navigation
function changeCalendarMonth(delta) {
  state.calendar.month += delta;
  if (state.calendar.month > 11) {
    state.calendar.month = 0;
    state.calendar.year += 1;
  } else if (state.calendar.month < 0) {
    state.calendar.month = 11;
    state.calendar.year -= 1;
  }
  renderCalendar();
}

// Jump to date details from Dashboard
function jumpToDateDetails(dateStr) {
  try {
    const parts = dateStr.split("-");
    state.calendar.year = parseInt(parts[0]);
    state.calendar.month = parseInt(parts[1]) - 1;
    state.selectedDate = dateStr;
    switchView("calendar");
    renderCalendar();
    handleCalendarDateClick(dateStr);
  } catch (e) {
    console.error(e);
  }
}

// Render Analytics View
function renderAnalytics() {
  if (!state.analyticsData) return;
  const { teachers, day_of_week, streaks, summary } = state.analyticsData;

  // 1. Teacher breakdown bars
  const teacherList = document.getElementById("analytics-teacher-list");
  if (teacherList && teachers) {
    teacherList.innerHTML = teachers
      .map(
        (t) => `
      <div class="teacher-item">
        <div class="teacher-item-top">
          <span class="teacher-name">Prof. ${t.teacher}</span>
          <span class="teacher-stat">${t.present}/${t.total} (${t.percentage}%)</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" style="width: ${t.percentage}%; background: ${
          t.percentage >= 75 ? "var(--present)" : "var(--pending)"
        }"></div>
        </div>
      </div>
    `
      )
      .join("");
  }

  // 2. Day of Week Chart Bars
  const chartContainer = document.getElementById("analytics-day-bars");
  if (chartContainer && day_of_week) {
    const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
    chartContainer.innerHTML = days
      .map((d) => {
        const stats = day_of_week[d] || { present: 0, absent: 0 };
        const total = stats.present + stats.absent;
        const pct = total > 0 ? Math.round((stats.present / total) * 100) : 0;
        return `
        <div class="day-bar-col">
          <span style="font-size: 0.7rem; font-weight: 700;">${pct}%</span>
          <div class="bar-visual-wrap">
            <div class="bar-fill present" style="height: ${pct}%;"></div>
          </div>
          <span class="bar-col-label">${d.substring(0, 3)}</span>
        </div>
      `;
      })
      .join("");
  }

  // 3. Streak KPI
  const streakEl = document.getElementById("analytics-streak-val");
  if (streakEl && streaks) {
    streakEl.textContent = `${streaks.current_streak_days} Days`;
  }
}

// Target Simulator & Calculator
async function updateSimulator(targetVal = state.targetPercentage) {
  state.targetPercentage = targetVal;
  const sliderEl = document.getElementById("sim-target-slider");
  const targetLabel = document.getElementById("sim-target-display");
  if (sliderEl) sliderEl.value = targetVal;
  if (targetLabel) targetLabel.textContent = `${targetVal}%`;

  try {
    const forecast = await api.fetchForecast(targetVal);

    const neededEl = document.getElementById("sim-classes-needed");
    const safeEl = document.getElementById("sim-safe-skips");
    const statusEl = document.getElementById("sim-status-grade");
    const milestoneTable = document.getElementById("sim-milestones-body");

    if (neededEl) {
      if (forecast.classes_needed_to_reach_target === 0) {
        neededEl.textContent = "0 (Target Reached)";
      } else if (forecast.classes_needed_to_reach_target === -1) {
        neededEl.textContent = "Impossible (Already missed classes)";
      } else {
        neededEl.textContent = `${forecast.classes_needed_to_reach_target} Classes`;
      }
    }

    if (safeEl) {
      safeEl.textContent = `${forecast.safe_skips_allowed} Classes`;
    }

    if (statusEl) {
      statusEl.textContent = forecast.status_grade;
    }

    if (milestoneTable && forecast.milestones) {
      milestoneTable.innerHTML = forecast.milestones
        .map(
          (m) => `
        <tr>
          <td><strong>${m.target}%</strong></td>
          <td><span class="brand-badge">${m.status}</span></td>
          <td>${m.classes_needed > 0 ? `${m.classes_needed} more` : "Achieved"}</td>
          <td>${m.safe_skips > 0 ? `${m.safe_skips} skips` : "0"}</td>
        </tr>
      `
        )
        .join("");
    }
  } catch (err) {
    console.error("Forecast error:", err);
  }
}

// Complete Records Table & Search
function renderRecordsTable(query = "") {
  if (!state.attendanceData) return;
  const tbody = document.getElementById("records-table-body");
  if (!tbody) return;

  const attendance = state.attendanceData.attendance || {};
  const rows = [];

  Object.keys(attendance)
    .sort()
    .reverse()
    .forEach((dateStr) => {
      const dayRecord = attendance[dateStr];
      (dayRecord.slots || []).forEach((slot) => {
        rows.push({
          date: dateStr,
          slot: slot.slot,
          teacher: slot.teacher || "Unassigned",
          status: slot.status,
        });
      });
    });

  const filtered = rows.filter((r) => {
    if (!query) return true;
    const q = query.toLowerCase();
    return (
      r.date.toLowerCase().includes(q) ||
      r.slot.toLowerCase().includes(q) ||
      r.teacher.toLowerCase().includes(q) ||
      r.status.toLowerCase().includes(q)
    );
  });

  tbody.innerHTML = filtered
    .map(
      (r) => `
    <tr>
      <td><strong>${r.date}</strong></td>
      <td>${r.slot}</td>
      <td>Prof. ${r.teacher}</td>
      <td><span class="slot-tag ${r.status}">${r.status.toUpperCase()}</span></td>
      <td>
        <button class="header-action-btn" style="padding: 4px 8px; font-size: 0.72rem;" 
                onclick="sendChatQuery('Was I present on ${r.date} for slot ${r.slot}?')">
          Ask AI
        </button>
      </td>
    </tr>
  `
    )
    .join("");
}

// Export Records to CSV
function exportRecordsCSV() {
  if (!state.attendanceData) return;
  const attendance = state.attendanceData.attendance || {};
  let csv = "Date,Slot,Teacher,Status\n";

  Object.keys(attendance)
    .sort()
    .reverse()
    .forEach((dateStr) => {
      const slots = attendance[dateStr].slots || [];
      slots.forEach((s) => {
        csv += `"${dateStr}","${s.slot}","${s.teacher || ""}","${s.status}"\n`;
      });
    });

  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", `Attendance_${state.student.name}_${new Date().toISOString().slice(0, 10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast("Attendance CSV exported", "success");
}

// ==========================================================================
// AI Chat Interface Engine
// ==========================================================================

function setupInitialChatWelcome() {
  if (state.chatHistory.length === 0) {
    appendChatMessage(
      "assistant",
      `Hello **${state.student.name}**! I am your **CampusOS Attendance AI Assistant**.\n\n` +
        `I have direct access to your verified attendance records for **${state.classroomName}**. You can ask me:\n` +
        `- What is my overall attendance percentage?\n` +
        `- Was I present or absent on a specific date?\n` +
        `- Who taught the class at a particular time slot?\n` +
        `- What is my attendance breakdown for this month?`
    );
  }
}

async function handleChatSubmit(e) {
  if (e) e.preventDefault();
  const inputEl = document.getElementById("chat-input-field");
  if (!inputEl) return;

  const question = inputEl.value.trim();
  if (!question || state.isChatLoading) return;

  inputEl.value = "";
  await sendChatQuery(question);
}

async function sendChatQuery(question) {
  // Switch to chat view if not already
  if (state.activeView !== "chat") {
    switchView("chat");
  }

  appendChatMessage("user", question);

  // Show typing indicator
  state.isChatLoading = true;
  showChatTyping();

  try {
    const response = await api.sendChatMessage(question);
    removeChatTyping();

    if (response.success) {
      appendChatMessage("assistant", response.answer);
    } else {
      appendChatMessage(
        "assistant",
        response.answer || "Sorry, I could not process your query. Please try again."
      );
    }
  } catch (error) {
    removeChatTyping();
    console.error("Chat error:", error);
    appendChatMessage(
      "assistant",
      "Network error: Unable to reach the AI attendance service."
    );
  } finally {
    state.isChatLoading = false;
  }
}

function appendChatMessage(role, content) {
  state.chatHistory.push({ role, content });
  const container = document.getElementById("chat-messages-scroll");
  if (!container) return;

  const bubble = document.createElement("div");
  bubble.className = `message-bubble ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "You" : "AI";

  const msgContent = document.createElement("div");
  msgContent.className = "msg-content";
  msgContent.innerHTML = formatMarkdown(content);

  bubble.appendChild(avatar);
  bubble.appendChild(msgContent);

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

function showChatTyping() {
  const container = document.getElementById("chat-messages-scroll");
  if (!container) return;

  const typingBubble = document.createElement("div");
  typingBubble.id = "chat-typing-indicator";
  typingBubble.className = "message-bubble assistant";
  typingBubble.innerHTML = `
    <div class="msg-avatar">AI</div>
    <div class="msg-content">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>
  `;
  container.appendChild(typingBubble);
  container.scrollTop = container.scrollHeight;
}

function removeChatTyping() {
  const typing = document.getElementById("chat-typing-indicator");
  if (typing) typing.remove();
}

async function handleResetChat() {
  try {
    await api.resetChat();
    state.chatSessionId = "web-session-" + Math.random().toString(36).substring(2, 9);
    state.chatHistory = [];
    const container = document.getElementById("chat-messages-scroll");
    if (container) container.innerHTML = "";
    setupInitialChatWelcome();
    showToast("Chat memory reset", "info");
  } catch (err) {
    showToast("Failed to reset session", "error");
  }
}

function askAIAboutDate(dateStr) {
  switchView("chat");
  sendChatQuery(`What was my attendance status and slots on ${dateStr}?`);
}

function handleDateSidebarQuery() {
  const dateInput = document.getElementById("chat-date-picker-input");
  if (dateInput && dateInput.value) {
    sendChatQuery(`What is my attendance on ${dateInput.value}?`);
  }
}

// Markdown Formatter (Converts bold, lists, code, tables into HTML)
function formatMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Bold **text**
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic *text*
  html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Bullet points
  html = html.replace(/^\s*-\s+(.*)$/gm, "<li>$1</li>");
  // Wrap li in ul
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  // Code `code`
  html = html.replace(/`(.*?)`/g, "<code style='background:rgba(255,255,255,0.1);padding:2px 5px;border-radius:4px;'>$1</code>");
  // Line breaks
  html = html.replace(/\n\n/g, "</p><p>").replace(/\n/g, "<br/>");

  return `<p>${html}</p>`;
}

// Helper: Date format
function formatDateFriendly(dateStr) {
  try {
    const [year, month, day] = dateStr.split("-");
    const d = new Date(year, month - 1, day);
    return d.toLocaleDateString("en-US", {
      weekday: "short",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch (e) {
    return dateStr;
  }
}

// ==========================================================================
// View Switcher & Navigation
// ==========================================================================

function switchView(viewName) {
  state.activeView = viewName;

  // Update Nav links
  document.querySelectorAll(".nav-link").forEach((link) => {
    if (link.getAttribute("data-view") === viewName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Update View Sections
  document.querySelectorAll(".view-section").forEach((sec) => {
    if (sec.id === `view-${viewName}`) {
      sec.classList.add("active");
    } else {
      sec.classList.remove("active");
    }
  });

  // Update Top Header Heading
  const headingMap = {
    overview: "Attendance Overview & Analytics",
    chat: "CampusOS AI Attendance Agent",
    calendar: "Attendance Matrix & Slot Calendar",
    analytics: "Faculty & Subject Insights",
    simulator: "Attendance Target Simulator & Planner",
    records: "Full Attendance Records & Audit Log",
  };

  const headerTitle = document.getElementById("view-header-title");
  if (headerTitle) {
    headerTitle.textContent = headingMap[viewName] || "Attendance AI";
  }

  // Close mobile sidebar if open
  const sidebar = document.querySelector(".sidebar");
  if (sidebar) sidebar.classList.remove("mobile-open");
}

// ==========================================================================
// Student Profile (Read-Only Display)
// ==========================================================================

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "!" : "i"}</span><span>${message}</span>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Setup Event Listeners
function setupEventListeners() {
  // Nav Links
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.addEventListener("click", () => {
      const view = link.getAttribute("data-view");
      if (view) switchView(view);
    });
  });

  // Mobile Menu Toggle
  const toggleBtn = document.getElementById("mobile-menu-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", () => {
      document.querySelector(".sidebar")?.classList.toggle("mobile-open");
    });
  }

  // Chat Form Submit
  const chatForm = document.getElementById("chat-input-form");
  if (chatForm) {
    chatForm.addEventListener("submit", handleChatSubmit);
  }

  // Simulator Slider
  const simSlider = document.getElementById("sim-target-slider");
  if (simSlider) {
    simSlider.addEventListener("input", (e) => {
      updateSimulator(e.target.value);
    });
  }

  // Records Search Input
  const searchInput = document.getElementById("records-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      renderRecordsTable(e.target.value);
    });
  }

  // Keyboard Shortcuts
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      switchView("chat");
      document.getElementById("chat-input-field")?.focus();
    }
  });
}
