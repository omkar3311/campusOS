/**
 * CampusOS Landing Page - Content & Agent Data Configuration
 * 
 * You can easily customize the agent names, descriptions, badges, inputs, 
 * processing steps, outputs, metrics, simulations, and role perspectives here.
 */

window.CAMPUS_OS_DATA = {
  meta: {
    badge: "AUTONOMOUS MULTI-AGENT RUNTIME v3.0",
    headline: "Four Autonomous AI Agents.",
    headlineGradient: "One Living Campus Operating System.",
    subheadline: "Watch how raw campus telemetry seamlessly flows into real-time student mastery, placement acceleration, touchless attendance, and 24/7 institutional operations through a continuous multi-agent pipeline.",
    ctaPrimaryText: "Launch Campus Portal",
    ctaPrimaryLink: "/login",
    ctaSecondaryText: "Explore Public Inquiry AI",
    ctaSecondaryLink: "/agent/campus/"
  },

  problem: {
    badge: "THE SYSTEMIC BOTTLENECK",
    title: "Higher Education is Broken by Siloed Memory.",
    description: "Traditional universities operate on disconnected databases — attendance is manual, learning is one-size-fits-all, career guidance is reactive, and campus communication is slow.",
    stats: [
      { value: "73%", label: "Time Lost in Administrative Overhead", detail: "Manual roll-calls, paperwork, and fragmented portals" },
      { value: "4.2x", label: "Delay in Academic Interventions", detail: "Students struggle weeks before instructors notice gaps" },
      { value: "68%", label: "Graduates Face Skill-to-Job Mismatch", detail: "Generic curriculums miss real-time industry requirements" }
    ],
    solutionQuote: "CampusOS replaces fragmented tools with a continuous pipeline of 4 specialized AI agents that pass context to each other in real time."
  },

  // Role-Based Perspective Switcher Data
  perspectives: {
    student: {
      title: "For Students",
      tagline: "Personalized Tutoring, Touchless Attendance & Guaranteed Placement Readiness",
      metrics: [
        { label: "Attendance Precision", value: "100% Tamper-Proof" },
        { label: "Comprehension Lift", value: "+44% Average" },
        { label: "ATS Placement Match", value: "96.4% Top Tier" }
      ]
    },
    faculty: {
      title: "For Faculty",
      tagline: "Zero Administrative Roll-Call Burden & Real-Time Classroom Comprehension Telemetry",
      metrics: [
        { label: "Admin Time Saved", value: "15 mins / period" },
        { label: "Comprehension Telemetry", value: "Instant Heatmap" },
        { label: "Automated Quiz Gen", value: "< 1s per topic" }
      ]
    },
    admin: {
      title: "For HODs & Deans",
      tagline: "Instant Institutional Oversight, Accreditation Telemetry & 24/7 Operations Desk",
      metrics: [
        { label: "Weekly Hours Saved", value: "18 hrs / faculty" },
        { label: "Inquiry Auto-Resolution", value: "98.7% instant" },
        { label: "Campus Operating Cost", value: "-65% overhead" }
      ]
    }
  },

  // "Day in the Life" Chronological Journey
  dayJourney: [
    { time: "09:00 AM", agent: "AttendMate AI", title: "Touchless Class Entry", desc: "Biometric face telemetry verifies Alex in Lecture Hall B in 0.3s without roll-call interruptions." },
    { time: "11:30 AM", agent: "Synapse AI", title: "Adaptive Study Session", desc: "Synapse breaks down neural backprop calculus into visual analogies with custom PyTorch quizzes." },
    { time: "03:00 PM", agent: "Resume-IQ", title: "Career & ATS Matching", desc: "New PyTorch skill credential automatically added to resume; ATS score surges to 96.4%." },
    { time: "06:00 PM", agent: "Campus-Desk", title: "Instant Services & Vault", desc: "Alex requests an official Bonafide Certificate—cryptographically signed and issued in < 0.05s." }
  ],

  // Interactive Simulation Data for Agent Playgrounds
  simulations: {
    synapseTopics: {
      "Neural Networks": {
        analogy: "Think of Backpropagation like an archery coach pointing out your exact angle errors after each shot so you fine-tune your muscle memory with each round.",
        math: "∇L = (∂L/∂W) = a^(l-1) · (δ^l)^T",
        roadmap: ["1. Intuitive Mental Model", "2. Calculus Partial Derivatives", "3. PyTorch Custom Loss Function"],
        metric: "+44% Comprehension"
      },
      "Distributed Systems": {
        analogy: "Think of the Raft Consensus Algorithm like a parliamentary election where nodes vote for a leader and maintain a shared synchronized ledger.",
        math: "Quorum = ⌊N/2⌋ + 1 votes required",
        roadmap: ["1. Leader Election Protocol", "2. Log Replication State Machine", "3. Network Partition Handling"],
        metric: "+52% Retention"
      },
      "Database Indexing": {
        analogy: "Think of a B+ Tree Index like the table of contents and index thumb-tabs in an encyclopedia—jumping directly to the exact page without scanning every word.",
        math: "Search Complexity: O(log_B N) disk I/O ops",
        roadmap: ["1. Balanced Tree Invariants", "2. Leaf Node Pointer Traversals", "3. Concurrency Locking & Latches"],
        metric: "+48% Speed Lift"
      }
    },

    resumeATS: {
      before: {
        score: 62,
        rank: "Bottom 60%",
        bullets: [
          "Worked on Python and Machine learning projects.",
          "Made a web application for attendance tracking.",
          "Helped students understand course concepts."
        ]
      },
      after: {
        score: 96.4,
        rank: "Top 2% Elite",
        bullets: [
          "Architected real-time PyTorch neural backprop engine achieving 99.8% verification accuracy.",
          "Engineered distributed RTSP video telemetry pipeline reducing classroom latency by 73%.",
          "Automated ATS resume parsing across 500+ requisitions, boosting interview callback rate by 3.8x."
        ]
      }
    },

    campusInquiries: {
      "Bonafide Certificate": {
        answer: "Your Bonafide Certificate has been auto-generated, digitally signed, and registered in the institutional blockchain vault.",
        doc: "Bonafide_Certificate_CS-2026-892.pdf",
        time: "< 0.05s"
      },
      "Exam Guidelines": {
        answer: "Semester End Examinations commence on December 10, 2026. Hall tickets will be issued 7 days prior via student portal.",
        doc: "Semester_Exam_Schedule_2026.pdf",
        time: "0.03s"
      },
      "Hostel Policy": {
        answer: "Hostel curfew is 10:00 PM. Night out-pass requests can be auto-approved via CampusOS parent consent verification.",
        doc: "Campus_Hostel_Handbook_v3.pdf",
        time: "0.04s"
      }
    }
  },

  agents: [
    {
      id: "agent-1",
      number: "01",
      name: "AttendMate AI",
      codename: "ATTENDMATE-AI",
      category: "BIOMETRIC RECOGNITION & TELEMETRY",
      accentColor: "#38bdf8", // Sky Blue
      accentGlow: "rgba(56, 189, 248, 0.25)",
      badge: "AGENT 01 • PERCEPTION LAYER",
      tagline: "Instant zero-touch identity verification & live classroom presence.",
      description: "Captures ambient multi-modal camera feeds, performs 0.3s biometric neural verification, and creates tamper-proof attendance telemetry without interrupting lectures.",
      
      input: {
        label: "RAW INPUT STREAM",
        type: "Multi-modal Classroom Feed",
        items: [
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>', title: "Live Classroom Camera Feed", desc: "1080p RTSP Stream at 30 FPS" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>', title: "Timetable & Room Geospatial Anchor", desc: "CS-Hall B • Slot: 09:00 - 10:00 AM" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M3 15h18"/></svg>', title: "Student Roster Embeddings", desc: "128-dimensional facial vector index" }
        ],
        badge: "INPUT: MULTI-MODAL SENSOR FEED"
      },
      
      processing: {
        label: "AI PROCESSING PIPELINE",
        steps: [
          { title: "Neural Face Detection & Liveness Check", status: "Active", metric: "0.12s", detail: "Anti-spoof infrared & depth geometry verification" },
          { title: "Vector Distance Cosine Matching", status: "Verified", metric: "99.8%", detail: "Comparing embeddings against encrypted college vault" },
          { title: "Classroom Attention & Telemetry Log", status: "Generated", metric: "Live", detail: "Calculating presentee index and slot-wise timestamp" }
        ],
        hudStats: [
          { label: "Recognition Latency", value: "0.28s" },
          { label: "Verification Confidence", value: "99.8%" },
          { label: "False Positive Rate", value: "< 0.001%" }
        ]
      },

      output: {
        label: "STRUCTURED AGENT OUTPUT",
        artifactName: "Verified_Student_Context_Packet.json",
        items: [
          { key: "Student Identity", value: "Alex Vance (PRN: CS-2026-892)" },
          { key: "Session & Status", value: "CS402 Machine Learning • Present (09:02 AM)" },
          { key: "Context Handover", value: "Passed to Agent 02 (Synapse AI)" }
        ],
        payloadPreview: "{\n  \"student_id\": \"CS-2026-892\",\n  \"status\": \"VERIFIED_PRESENT\",\n  \"active_subject\": \"Neural Networks & Backprop\",\n  \"prior_mastery_level\": \"Intermediate\",\n  \"target_agent\": \"synapse_agent_v3\"\n}",
        handoverText: "Output ready → Injecting verified student presence into Agent 02 (Synapse AI)..."
      }
    },

    {
      id: "agent-2",
      number: "02",
      name: "Synapse AI",
      codename: "SYNAPSE-AI",
      category: "COGNITIVE TUTORING & ROADMAPS",
      accentColor: "#818cf8", // Indigo / Violet
      accentGlow: "rgba(129, 140, 248, 0.25)",
      badge: "AGENT 02 • COGNITIVE SYNTHESIS",
      tagline: "Hyper-personalized curriculum adapting to individual learning styles.",
      description: "Receives the student's active subject context and historical comprehension data from AttendMate AI to generate real-time visual analogies, personalized study roadmaps, and adaptive micro-quizzes.",
      
      input: {
        label: "INHERITED INPUT STREAM",
        type: "Student Telemetry + Syllabus Knowledge Graph",
        items: [
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>', title: "Handover from AttendMate AI", desc: "Verified student profile & current lecture context" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg>', title: "Class Curriculum & Lecture Notes", desc: "Unit 4: Deep Learning Optimization Algorithms" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a7 7 0 0 0-7 7c0 3 2 5 3 7h8c1-2 3-4 3-7a7 7 0 0 0-7-7z"/></svg>', title: "Student Cognitive History", desc: "Struggles with calculus gradients & vector spaces" }
        ],
        badge: "INPUT: CONTEXT PACKET FROM ATTENDMATE"
      },
      
      processing: {
        label: "COGNITIVE GENERATION PIPELINE",
        steps: [
          { title: "Cognitive Gap & Prerequisite Analysis", status: "Completed", metric: "0.4s", detail: "Pinpointing root calculus misunderstanding" },
          { title: "Adaptive Roadmap & Analogy Formulation", status: "Synthesized", metric: "Real-time", detail: "Generating step-by-step intuitive mental models" },
          { title: "Dynamic 5-Question Diagnostic Assessment", status: "Active", metric: "5 Items", detail: "Calibrated difficulty matching learner zone of proximal development" }
        ],
        hudStats: [
          { label: "Comprehension Lift", value: "+44%" },
          { label: "Roadmap Milestones", value: "3 Modules" },
          { label: "Active Retention Score", value: "94.2%" }
        ]
      },

      output: {
        label: "STRUCTURED AGENT OUTPUT",
        artifactName: "Mastery_Milestone_Dossier.json",
        items: [
          { key: "Topic Mastered", value: "Backpropagation & Gradient Descent" },
          { key: "Quiz Accuracy", value: "5/5 (100% Score)" },
          { key: "Demonstrated Skill", value: "PyTorch Tensor Operations & Optimizer Tuning" }
        ],
        payloadPreview: "{\n  \"student_id\": \"CS-2026-892\",\n  \"verified_skills\": [\"PyTorch\", \"Backprop Math\", \"Loss Functions\"],\n  \"skill_level\": \"Advanced\",\n  \"portfolio_readiness\": true,\n  \"target_agent\": \"career_agent_v3\"\n}",
        handoverText: "Output ready → Streaming verified skill mastery into Agent 03 (Resume-IQ)..."
      }
    },

    {
      id: "agent-3",
      number: "03",
      name: "Resume-IQ",
      codename: "RESUME-IQ",
      category: "ATS OPTIMIZATION & PLACEMENT ACCELERATION",
      accentColor: "#38bdf8", // Sky / Cyan
      accentGlow: "rgba(56, 189, 248, 0.25)",
      badge: "AGENT 03 • TALENT MATCHING",
      tagline: "Transforming verified academic growth into top-tier placement offers.",
      description: "Receives real-time skill certifications from Synapse AI, continually rewrites ATS-optimized resumes with quantifiable metrics, and matches students to high-fit job requisitions.",
      
      input: {
        label: "INHERITED INPUT STREAM",
        type: "Verified Skills & Live Project Artifacts",
        items: [
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>', title: "Handover from Synapse AI", desc: "Verified PyTorch & Deep Learning skill credentials" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline></svg>', title: "Current Student Resume & GitHub", desc: "Draft v2.1 • 4 Projects • 1 Internship" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 7v14M21 7v14M6 7V3h12v4M9 11h2M9 15h2M13 11h2M13 15h2"></path></svg>', title: "Live Market ATS Job Descriptors", desc: "500+ Partner hiring profiles & tech stacks" }
        ],
        badge: "INPUT: SKILL PACKET FROM SYNAPSE"
      },
      
      processing: {
        label: "ATS SCORING & GAP ANALYSIS",
        steps: [
          { title: "Semantic Resume Parsing & Keyword Vectorization", status: "Indexed", metric: "0.18s", detail: "Scoring against target ATS algorithms" },
          { title: "Quantified Impact Statement Enhancement", status: "Generated", metric: "4 Bullets", detail: "Translating course projects into production metrics" },
          { title: "Placement Opportunity Re-Ranking", status: "Matched", metric: "94.6%", detail: "Matching skill profile against tier-1 job openings" }
        ],
        hudStats: [
          { label: "ATS Score Boost", value: "96 / 100" },
          { label: "Eligible Roles", value: "14 Openings" },
          { label: "Placement Lift", value: "+38%" }
        ]
      },

      output: {
        label: "STRUCTURED AGENT OUTPUT",
        artifactName: "ATS_Optimized_Candidate_Dossier.pdf",
        items: [
          { key: "Target Role", value: "Junior ML / Backend Engineer" },
          { key: "ATS Alignment", value: "96% Verified Match (Top Decile)" },
          { key: "Action", value: "Candidate auto-shortlisted for Partner Interviews" }
        ],
        payloadPreview: "{\n  \"candidate_id\": \"CS-2026-892\",\n  \"ats_score\": 96,\n  \"top_match_company\": \"Apex Cloud Labs\",\n  \"interview_readiness\": \"HIGH\",\n  \"target_agent\": \"campus_inquiry_agent\"\n}",
        handoverText: "Output ready → Feeding institutional talent telemetry into Agent 04 (Campus-Desk)..."
      }
    },

    {
      id: "agent-4",
      number: "04",
      name: "Campus-Desk AI",
      codename: "CAMPUS-DESK",
      category: "24/7 CAMPUS INQUIRIES & INSTITUTIONAL COORDINATION",
      accentColor: "#34d399", // Emerald / Mint
      accentGlow: "rgba(52, 211, 153, 0.25)",
      badge: "AGENT 04 • INSTITUTIONAL COORDINATION",
      tagline: "Instant responses for visitors, parents, and automated campus resolutions.",
      description: "Serves as the public 24/7 conversational desk for admission, hostel, exams, and regulation queries while connecting all student workflows back into administrative dashboards.",
      
      input: {
        label: "INHERITED INPUT STREAM",
        type: "Ecosystem Telemetry + Public Query Ingestion",
        items: [
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/></svg>', title: "Handover from Agents 01-03", desc: "Real-time institutional attendance & placement statistics" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>', title: "Public Visitor / Student Inquiries", desc: "Admissions, syllabi, certifications, campus policies" },
          { icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 7v14M21 7v14M6 7V3h12v4M9 11h2M9 15h2M13 11h2M13 15h2"></path></svg>', title: "Official College Regulation Vault", desc: "Handbooks, exam schedules, and circulars" }
        ],
        badge: "INPUT: UNIFIED PIPELINE & PUBLIC CHAT"
      },
      
      processing: {
        label: "KNOWLEDGE RETRIEVAL & DISPATCH",
        steps: [
          { title: "Vector Semantic Handbook Search", status: "Indexed", metric: "< 0.05s", detail: "Instant retrieval from verified college guidelines" },
          { title: "Cross-Department Action Dispatch", status: "Automated", metric: "Instant", detail: "Auto-approving bonafide & hall-ticket requests" },
          { title: "Executive Telemetry Aggregation", status: "Live Sync", metric: "100%", detail: "Pushing analytics to HOD & Dean dashboards" }
        ],
        hudStats: [
          { label: "Query Resolution", value: "< 1s" },
          { label: "Auto-Resolution Rate", value: "98.7%" },
          { label: "Visitor Satisfaction", value: "4.9/5" }
        ]
      },

      output: {
        label: "STRUCTURED AGENT OUTPUT",
        artifactName: "Campus_Ecosystem_Resolution.json",
        items: [
          { key: "Query Status", value: "Instant Accurate Resolution Delivered" },
          { key: "Document Issued", value: "Verified Bonafide Certificate (Auto-Signed)" },
          { key: "System State", value: "Full 4-Agent Pipeline Cycle Completed" }
        ],
        payloadPreview: "{\n  \"cycle_status\": \"COMPLETE_SUCCESS\",\n  \"agents_orchestrated\": [\"ATTENDMATE\", \"SYNAPSE\", \"RESUME_IQ\", \"CAMPUS_DESK\"],\n  \"student_outcome\": \"OPTIMIZED\",\n  \"institutional_cost_reduced\": \"65%\"\n}",
        handoverText: "Pipeline Cycle Complete → All 4 Agents Synchronized into Unified CampusOS."
      }
    }
  ],

  systemOrchestration: {
    badge: "UNIFIED ECOSYSTEM MATRIX",
    title: "All Four Agents Working as One.",
    subtitle: "When these 4 autonomous agents communicate through a shared memory bus, friction disappears across the entire institution.",
    pipelineSteps: [
      { step: "01", name: "AttendMate AI", role: "Biometric Perception", color: "#38bdf8", icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>' },
      { step: "02", name: "Synapse AI", role: "Cognitive Tutoring", color: "#818cf8", icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>' },
      { step: "03", name: "Resume-IQ", role: "Career Placement", color: "#38bdf8", icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>' },
      { step: "04", name: "Campus-Desk", role: "Public Operations", color: "#34d399", icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M3 7v14M21 7v14M6 7V3h12v4M9 11h2M9 15h2M13 11h2M13 15h2"/></svg>' }
    ],
    finalOutcome: {
      title: "The Zero-Friction Intelligent Campus",
      description: "From the moment a student steps into a classroom to the day they receive a placement offer, CampusOS orchestrates every touchpoint with zero manual latency.",
      metrics: [
        { label: "Daily Autonomous Actions", value: "240,000+" },
        { label: "Average Response Time", value: "0.25s" },
        { label: "Administrative Time Saved", value: "18 hrs/wk" },
        { label: "Placement Success Lift", value: "+38%" }
      ]
    }
  },

  cta: {
    badge: "EXPERIENCE THE FUTURE OF EDUCATION",
    headline: "Transform Your Campus Into an Intelligent AI Ecosystem.",
    subheadline: "Join leading institutions leveraging CampusOS for touchless operations, personalized learning, and accelerated career placements.",
    primaryButton: "Sign In to Portal",
    primaryLink: "/login",
    secondaryButton: "Test Campus Inquiry AI",
    secondaryLink: "/agent/campus/"
  }
};
