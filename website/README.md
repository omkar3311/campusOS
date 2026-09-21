# 🌐 CampusOS Web Platform & Central Orchestrator

The **CampusOS Web Platform (`website/`)** serves as the central orchestration gateway, administrative management layer, and unified multi-agent portal of the CampusOS ecosystem. It bridges institutional governance, classroom administration, personal student analytics, and autonomous AI sub-agents into a single, high-performance web environment powered by **FastAPI**, **Supabase PostgreSQL**, **ChromaDB**, and **Groq LLMs**.

---

## 📑 Table of Contents

- [🏛️ System Architecture](#️-system-architecture)
- [🔐 Authentication & Role-Based Access Control (RBAC)](#-authentication--role-based-access-control-rbac)
- [🗄️ Dynamic Database Schema & Isolation Model](#️-dynamic-database-schema--isolation-model)
- [📊 Analytics, Forecasting & Defaulter Engine](#-analytics-forecasting--defaulter-engine)
- [🤖 Embedded RAG Intelligent Assistant](#-embedded-rag-intelligent-assistant)
- [🔗 Frictionless Link-Based Onboarding](#-frictionless-link-based-onboarding)
- [🎛️ Sub-Agent Application Mounting & Gateway](#️-sub-agent-application-mounting--gateway)
- [📁 Codebase & Template Directory Map](#-codebase--template-directory-map)

---

## 🏛️ System Architecture

The web platform acts as the core gateway of CampusOS. It handles HTTP request dispatching, security enforcement, dynamic database interactions, vector knowledge retrieval, template rendering, and seamless mounting of specialized sub-agents.

```mermaid
flowchart TD
    Client([Client Browser / Mobile / Desktop])

    subgraph PerimeterLayer["Perimeter & Security Layer"]
        AuthMiddleware["Authentication & Agent Protection Middleware\n(HttpOnly JWT Cookie / Bearer Token Inspection)"]
        RBAC["RBAC Dependency Engine\n(Role Hierarchy: HOD > Teacher > Student)"]
    end

    subgraph CoreEngine["CampusOS Web Orchestrator (FastAPI)"]
        Router["HTTP Router & View Handlers\n(main.py / utils.py)"]
        TemplateEngine["Jinja2 Template Rendering Engine\n(Dashboards, Ledgers, Onboarding Portals)"]
        ExportEngine["Streaming CSV Generator\n(StreamingResponse)"]
    end

    subgraph DataStorage["Data & Storage Infrastructure (Supabase)"]
        RelationalDB[(Supabase PostgreSQL)]
        DynamicTables["Dynamic Isolated Classroom Tables\n- students_{college}_{dept}\n- attendance_{college}_{dept}"]
        StorageBucket["Supabase Storage ('filestore')\n- Biometric Photos & Roster Avatars"]
    end

    subgraph IntelligenceLayer["Embedded CampusOS RAG Engine"]
        ChromaStore[(In-Memory ChromaDB Vector Store)]
        Embedder["SentenceTransformer\n(BAAI/bge-small-en)"]
        GroqGateway["Groq LLM Gateway\n(openai/gpt-oss-20b -> qwen/qwen3.6-27b)"]
        KnowledgeBase["Campus Knowledge Base\n(campusos.txt / summary_campusOS.txt)"]
    end

    subgraph SubAgentGateway["Mounted Autonomous Sub-Agent Workspaces"]
        StudyApp["📚 Study / Learning Agent\n(/agent/study)"]
        CareerApp["💼 Career / ResumeIQ Agent\n(/agent/career)"]
        AttendanceApp["📊 Attendance Intelligence Agent\n(/agent/attendance)"]
        HelpdeskApp["💬 Campus Inquiry AI\n(/agent/campus)"]
    end

    %% Flow Connections
    Client -->|HTTP / HTTPS Requests| AuthMiddleware
    AuthMiddleware --> RBAC
    RBAC --> Router

    Router --> TemplateEngine
    Router --> ExportEngine
    Router <--> RelationalDB
    RelationalDB <--> DynamicTables
    Router <--> StorageBucket

    Router <--> Embedder
    Embedder <--> ChromaStore
    ChromaStore <--> KnowledgeBase
    Router <--> GroqGateway

    AuthMiddleware -->|Protected Agent Proxy| SubAgentGateway
    SubAgentGateway --> StudyApp
    SubAgentGateway --> CareerApp
    SubAgentGateway --> AttendanceApp
    SubAgentGateway --> HelpdeskApp
```

---

## 🔐 Authentication & Role-Based Access Control (RBAC)

The platform enforces a strict 3-tier hierarchical Role-Based Access Control model managed via `auth.py`. 

### 1. Role Hierarchy Levels

```mermaid
graph TD
    HOD["Level 3: HOD / Principal (Super Admin)\n- Institutional Telemetry\n- College-wide Staff Directory\n- Assign Class Teachers\n- Global Classroom Oversight"]
    Teacher["Level 2: Teacher / Faculty\n- Classroom Management\n- Slot Attendance Live Editing\n- Defaulter Threshold Configuration\n- 1-Click CSV Roster Exports"]
    Student["Level 1: Enrolled Student\n- Personal Attendance Ledger\n- Slot Breakdown & Audit Logs\n- Defaulter Safe-Zone Calculator\n- Access to AI Workspaces"]
    Public["Level 0: Public Visitor\n- Landing & Story Showcase\n- 24/7 Campus Inquiry Helpdesk"]

    HOD -->|Inherits permissions of| Teacher
    Teacher -->|Inherits permissions of| Student
    Student -->|Inherits permissions of| Public
```

### 2. Security Mechanisms & Token Lifecycle

- **JWT Tokens (`HS256`)**: Signed JSON Web Tokens containing user claims (`sub`, `name`, `email`, `role`, `college_id`, optional `classroom_id` and `prn`).
- **HttpOnly Cookie Storage**: Tokens are stored in a secure cookie (`campusos_token`) with `SameSite=Lax` and 7-day expiration, mitigating XSS token theft.
- **Bcrypt Password Hashing**: Passwords for students, teachers, and HODs are encrypted using salted `bcrypt` hashes before storage.
- **Automated Protection Middleware**: Intercepts requests destined for protected sub-agents (`/agent/study`, `/agent/career`, `/agent/attendance`), ensuring unauthenticated visitors are redirected to `/login?redirect=...`.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser
    participant Middleware as Auth Middleware
    participant Auth as Auth Controller (/auth)
    participant DB as Supabase DB
    participant Dashboard as Role Dashboard

    User->>Browser: Enter credentials (Email, Password, College/Classroom ID)
    Browser->>Auth: POST /auth (role, credentials)
    Auth->>DB: Query user record & verify bcrypt hash
    
    alt Verification Failed
        DB-->>Auth: Record not found / invalid hash
        Auth-->>Browser: Render login.html with error alert
    else Verification Succeeded
        DB-->>Auth: Valid user payload (ID, Role, College, Classroom)
        Auth->>Auth: Generate signed HS256 JWT
        Auth-->>Browser: Set-Cookie: campusos_token (HttpOnly) + 303 Redirect
        
        Browser->>Middleware: GET /dashboard or /student/dashboard
        Middleware->>Middleware: Decode JWT & validate role claims
        Middleware->>Dashboard: Allow access & render role template
        Dashboard-->>Browser: Render personalized dashboard
    end
```

---

## 🗄️ Dynamic Database Schema & Isolation Model

CampusOS employs a **dynamic multi-table architecture** in Supabase PostgreSQL to ensure horizontal scalability and complete data isolation between classrooms and departments.

### 1. Isolated Table Architecture

Instead of pooling all institutional records into a monolithic table, each classroom is dynamically provisioned with:
- **Dedicated Student Table (`classroom_table`)**: Stores student records, PRNs, contact emails, hashed passwords, and biometric avatar URLs.
- **Dedicated Attendance Ledger (`attendance_table`)**: Stores date-wise slot attendance records and immutable audit histories.

```mermaid
erDiagram
    COLLEGES ||--o{ TEACHERS : employs
    COLLEGES ||--o{ CLASSROOMS : contains
    CLASSROOMS ||--|| DYNAMIC_STUDENT_TABLE : "provisions (classroom_table)"
    CLASSROOMS ||--|| DYNAMIC_ATTENDANCE_TABLE : "provisions (attendance_table)"

    COLLEGES {
        bigint id PK
        text college_name
        text creator
        text creator_email
        text password
    }

    TEACHERS {
        bigint id PK
        bigint college_id FK
        text teacher_name
        text email
        text role
        text password
        text img_url
    }

    CLASSROOMS {
        bigint id PK
        bigint college_id FK
        text classroom_name
        text classroom_table
        text attendance_table
        text classroom_faces
        text camera_input
        text slot
        int defualter
        text class_teacher
    }

    DYNAMIC_STUDENT_TABLE {
        bigint id PK
        bigint college_id
        bigint classroom_id
        text student_name
        text prn
        text email
        text password
        text img_url
    }

    DYNAMIC_ATTENDANCE_TABLE {
        bigint id PK
        bigint college_id
        bigint classroom_id
        text prn
        date attendance_date
        text slot_HH_MM_HH_MM
        text slot_HH_MM_HH_MM_teacher
        jsonb audit
    }
```

### 2. Slot Structure & Mutation Audit Trail

- **Slot Format**: Slot columns follow the naming convention `slot_<start_hour>_<start_min>_<end_hour>_<end_min>` (e.g., `slot_09_00_10_00`), paired with a corresponding teacher tracking column `slot_<start_hour>_<start_min>_<end_hour>_<end_min>_teacher`.
- **JSON Mutation Audit**: Every manual or automated attendance modification appends an entry to the `audit` JSON array:
  ```json
  [
    {
      "slot": "09:00 - 10:00",
      "teacher": "Prof. Alan Turing",
      "from": "pending",
      "to": "present"
    }
  ]
  ```
- **SQL Injection Guard**: Table names are validated through strict regex verification (`is_valid_table_name`) before executing database queries: `^[A-Za-z_][A-Za-z0-9_]*$`.

---

## 📊 Analytics, Forecasting & Defaulter Engine

The platform features an analytical engine that processes classroom ledgers into real-time metrics, risk classifications, and predictive forecasts.

```mermaid
flowchart LR
    subgraph RawData["Raw Ledger Ingestion"]
        Rows["Attendance Rows\n(slot_09_00, slot_10_00...)"]
    end

    subgraph Processor["Normalization & Aggregation"]
        Norm["process_attendance_rows()\n- Normalize Status: present / absent / pending\n- Aggregate Totals: P, A, Pe"]
        CalcPerc["Attendance Percentage:\nPercent = (Present / (Present + Absent)) * 100"]
    end

    subgraph AnalyticalModels["Intelligence & Risk Engines"]
        DefaulterCheck{"Defaulter Engine:\nPercent < Classroom Threshold?"}
        SafeSlots["Safe Slot Calculator:\nSlots Needed = ((75 - Percent) / 2) + 1"]
        Streak["Active Streak Counter:\nConsecutive 100% Present Days"]
        Predictor["Predictive Forecast:\nPredicted % = (Overall % * 0.7) + (Recent Month % * 0.3)"]
    end

    subgraph Outputs["Dashboard Insights"]
        BadgeYes["🚨 Defaulter Flag: YES\n(Risk Warning Message)"]
        BadgeNo["✅ Defaulter Flag: NO\n(Safe Zone Message)"]
        Charts["Interactive Visualizations\n- Slot-wise Bar Chart\n- Monthly Trend Line"]
    end

    Rows --> Norm --> CalcPerc
    CalcPerc --> DefaulterCheck
    CalcPerc --> SafeSlots
    CalcPerc --> Streak
    CalcPerc --> Predictor

    DefaulterCheck -- Yes --> BadgeYes
    DefaulterCheck -- No --> BadgeNo
    Predictor --> Charts
```

### Analytical Metrics Summary

| Metric | Calculation / Logic | Purpose |
| :--- | :--- | :--- |
| **Attendance %** | $\frac{\text{Present}}{\text{Present} + \text{Absent}} \times 100$ | Normalized student attendance excluding pending slots. |
| **Defaulter Status** | $\text{Attendance } \% < \text{Threshold } (\text{default } 75\%)$ | Identifies at-risk students for academic review. |
| **Safe Slots Needed** | $\lfloor \frac{75 - \text{Current } \%}{2} \rfloor + 1$ | Informs students how many consecutive classes they must attend. |
| **Predicted %** | $(\text{Overall } \% \times 0.7) + (\text{Latest Month } \% \times 0.3)$ | Forecasts final attendance based on historical and recent trends. |
| **Academic Rank** | Grade scale: $\ge 90\% \rightarrow \text{A}$, $\ge 80\% \rightarrow \text{B}$, $\ge 70\% \rightarrow \text{C}$, $< 70\% \rightarrow \text{D}$ | Categorizes student attendance tier. |

---

## 🤖 Embedded RAG Intelligent Assistant

The web platform features an embedded Retrieval-Augmented Generation (RAG) assistant (`/chat/groq`) accessible directly from dashboards.

```mermaid
flowchart TD
    UserQuery([User Question in Chat Interface]) --> EmbedQuery[Embed Query with BAAI/bge-small-en]
    
    subgraph VectorSearch["ChromaDB Vector Retrieval"]
        EmbedQuery --> CosineSim[Cosine Similarity Search against Knowledge Base]
        DocRegistry[(Session Vector Collection)] <--> CosineSim
        CosineSim --> Filter[Filter Documents: Similarity >= 0.6, Top-K = 3]
    end

    subgraph PromptBuilder["Context & Prompt Assembly"]
        Filter --> ContextString[Aggregate Context Snippets]
        ContextString --> SystemPrompt[Construct System & User Prompts with Campus Context]
    end

    subgraph LLMGatewayEngine["Groq Multi-Model LLM Gateway"]
        SystemPrompt --> GroqPrimary[Primary: openai/gpt-oss-20b]
        GroqPrimary -.->|On Failure / Rate-limit| GroqSecondary[Secondary Fallback: qwen/qwen3.6-27b]
        GroqSecondary -.->|On Final Failure| ContextQuoter[Direct Context Fallback Quotation]
    end

    GroqPrimary --> FinalAnswer([Streaming / JSON Response to User])
    GroqSecondary --> FinalAnswer
    ContextQuoter --> FinalAnswer
```

- **Dense Vector Search**: Powered by `SentenceTransformer("BAAI/bge-small-en")` generating normalized vector embeddings.
- **Dynamic Chunking**: Reads `campusos.txt` and `summary_campusOS.txt`, splitting content into 250-character chunks with a 50-character sliding overlap.
- **Session Memory Management**: In-memory collections stored in `session_collections`, with instant reset capability via `/reset`.

---

## 🔗 Frictionless Link-Based Onboarding

The platform simplifies institutional setup by replacing manual database entry with shareable onboarding links.

```mermaid
sequenceDiagram
    autonumber
    actor HOD as HOD / Administrator
    actor Teacher as Teacher Candidate
    actor Student as Student Candidate
    participant Platform as CampusOS Web Platform
    participant Storage as Supabase Storage ('filestore')
    participant DB as Supabase PostgreSQL

    Note over HOD,Platform: Teacher Onboarding Flow
    HOD->>Platform: Access /staff dashboard & copy Teacher Invite Link
    HOD-->>Teacher: Share /teacher/invite/{college_id}
    Teacher->>Platform: Submit Name, Email, Password & optional Photo
    Platform->>Storage: Store teacher photo in 'teachers/'
    Platform->>DB: Insert teacher record with role='teacher' & college_id
    Platform-->>Teacher: Create JWT session & redirect to /dashboard

    Note over HOD,Platform: Student Onboarding Flow
    Platform-->>Student: Share /student/invite/{college_id}/{classroom_id}
    Student->>Platform: Submit Name, PRN, Email, Password & Face Image
    Platform->>Storage: Upload face to classroom folder ('classroom_faces')
    Platform->>DB: Insert student into classroom's dynamic table
    Platform-->>Student: Account created confirmation -> ready for login
```

---

## 🎛️ Sub-Agent Application Mounting & Gateway

The central FastAPI application dynamically imports and mounts autonomous sub-agent applications onto unified path prefixes.

```mermaid
graph TD
    MainApp["CampusOS FastAPI Root App (Port 8000)"]

    MainApp -->|Mount: /agent/study & /agent/learning| StudyAgent["📚 Study Agent\n(study_agent/web/app.py)\n- AI Tutor & Syllabus RAG\n- Personalized Roadmaps\n- Practice Quizzes"]
    MainApp -->|Mount: /agent/career & /agent/resume| CareerAgent["💼 Career Agent / ResumeIQ\n(resume_agent/web/app.py)\n- ATS Resume Scoring\n- JD Skill-Gap Analysis\n- Mock Interview Engine"]
    MainApp -->|Mount: /agent/attendance| AttendanceAgent["📊 Attendance Intelligence Agent\n(attendance_agent/web/app.py)\n- Biometric Face Matching\n- Safe Bunk Modeling\n- Slot Telemetry"]
    MainApp -->|Mount: /agent/campus & /agent/helpdesk| HelpdeskAgent["💬 Campus Inquiry Helpdesk\n(helpdesk_agent/web/app.py)\n- Public Inquiries & Policies\n- Multi-stage RAG Guardrails"]
```

### Mounted Workspaces Summary

| Agent | Mount Paths | Access Level | Primary Specialization |
| :--- | :--- | :--- | :--- |
| **📚 Study / Learning Agent** | `/agent/study`, `/agent/learning` | 🔒 Authenticated Users | RAG syllabus tutor, step-by-step concept roadmaps, dynamic quiz generation. |
| **💼 Career Agent (ResumeIQ)** | `/agent/career`, `/agent/resume` | 🔒 Authenticated Users | ATS resume scoring, job description skill-gap analyzer, mock interview simulator. |
| **📊 Attendance Agent** | `/agent/attendance`, `/attendance-agent` | 🔒 Authenticated Users | Biometric facial recognition matching, predictive safe-bunk modeling, slot logs. |
| **💬 Campus Inquiry AI** | `/agent/campus`, `/agent/helpdesk` | 🌐 Public (No login) | 24/7 virtual helpdesk for admissions, fees, hostel rules, and college policies. |

---

## 📁 Codebase & Template Directory Map

```
website/
├── auth.py                  # JWT HS256 tokens, HttpOnly cookie helpers, RBAC middleware
├── main.py                  # Core FastAPI application, sub-agent mounting, route controller
├── utils.py                 # Supabase client, dynamic table operations, ChromaDB RAG pipeline
├── requirements.txt         # Module dependencies
├── summary.txt              # Executive SaaS overview and feature specifications
├── data/
│   ├── campusos.txt         # Primary platform knowledge base document
│   ├── summary_campusOS.txt # Architectural reference document for RAG indexing
│   └── chroma_db/           # Local persistent vector store cache
├── templates/               # Jinja2 HTML templates
│   ├── new_home2.html       # Public landing and feature showcase
│   ├── landing.html         # Interactive platform presentation and storytelling
│   ├── login.html           # Unified multi-role login & signup portal
│   ├── main_dashboard.html  # HOD and teacher institutional oversight portal
│   ├── class_dashboard.html # Classroom roster, slot editor, student enrollment, CSV export
│   ├── student.html         # Student attendance ledger, safe-zone calculators, streak trackers
│   ├── staff_dashboard.html # HOD staff management and teacher invite link generator
│   ├── teacher_invite_login.html # Frictionless teacher self-onboarding portal
│   └── student_invite_login.html # Classroom student invite and facial photo capture portal
└── static/
    ├── css/                 # Glassmorphic stylesheets (new_home2.css, landing.css, login.css)
    └── js/                  # Interactive JavaScript controllers (landing.js, login.js, new_home2.js)
```

---

## 👨‍💻 Engineering & Development

- **Platform Architecture**: Omkar Waghmare
- **Ecosystem**: CampusOS AI Agent Network
- **Design Paradigm**: Glassmorphic Cyber-Modern Dark Theme with Multi-Tenant Schema Isolation.


uvicorn main:app --host 0.0.0.0 --port 8000 --reload