# AssignHub Backend: Architecture & Technical Implementation Guide

This document provides an end-to-end technical explanation of the **AssignHub Backend** implementation. It covers the system architecture, database models, feature-specific implementation details, security controls, and deployment configurations.

---

## 1. System Overview & Architecture

AssignHub is built on a modern, decoupled, asynchronous event-driven architecture designed to support high-concurrency real-time tracking and student performance analytics.

```mermaid
graph TD
    Client[Flutter Mobile App / Client] <-->|REST APIs / WebSockets| API[FastAPI Web Service]
    API <-->|SQLAlchemy ORM| DB[(PostgreSQL Database)]
    API <-->|AWS SDK - Boto3| S3[(Amazon S3 Storage)]
    API <-->|Firebase Admin SDK| FCM[Firebase Cloud Messaging]
    API -->|APScheduler| Jobs[Background Scheduler]
    API -->|SMTP Client| SMTP[Email Services: Gmail / Brevo]
    API -->|Groq API Client| LLM[Llama-3.1-8b Natural Language Query Engine]
```

### Key Technology Stack:
*   **Web Framework:** FastAPI (Python 3.11) — utilized for high-performance, asynchronous handling of REST endpoints and WebSockets via ASGI (`uvicorn`).
*   **ORM & Database Engine:** SQLAlchemy 2.0 + PostgreSQL — configured with connection pooling (`pg8000` / `psycopg2-binary`) to manage structured transactions and complex join operations.
*   **Real-Time Communications:** FastAPI WebSockets — provides active push channels for live-updating assignment trackers without client-side polling.
*   **Task Scheduling:** APScheduler (AsyncIOScheduler + SQLAlchemyJobStore) — manages persistent, cluster-safe background jobs for close-deadlines, custom reminders, and alerts.
*   **File Storage:** AWS S3 — stores bulk-import templates, student submissions, and exported Excel sheets, accessed securely via presigned upload and download URLs.
*   **AI Integration:** Groq (Llama-3.1-8b-instant) — processes natural language queries to extract metrics and rosters dynamically.
*   **Push Notifications:** Firebase Cloud Messaging (FCM) — delivers instant system-wide notifications for new assignments, deadlines, and academic risk alerts.
*   **Email Deliverability:** SMTP Client (integrated with Gmail for Admin OTP verification, and Brevo SMTP for mentor/student onboarding invitations).

---

## 2. Database Models & Schema Design

The relational database schema is structured to ensure strict data integrity, fast join execution, and granular role permissions.

```mermaid
erDiagram
    users ||--o| admin_profiles : "has"
    users ||--o{ class_memberships : "member of"
    users ||--o{ submissions : "submits"
    users ||--o{ student_analytics : "has analytics"
    users ||--o{ notifications : "receives"
    classes ||--o{ class_memberships : "contains"
    classes ||--o{ assignments : "has"
    assignments ||--o{ submissions : "receives"
    assignments ||--o| assignment_analytics : "has analytics"
```

### Table Specifications:

1.  **`users`**: Stores core profiles.
    *   `id`: UUID (Primary Key)
    *   `role`: String (`ADMIN`, `MENTOR`, `STUDENT`) with check constraints.
    *   `email`: String (Unique, Indexed)
    *   `password_hash`: Text (hashed using Bcrypt)
    *   `registration_id`: String (Unique, null for Admin)
    *   `status`: String (`PENDING_OTP`, `ACTIVE`, `INACTIVE`, `BLOCKED`)
    *   `fcm_token`: Text (optional, for push notifications)
2.  **`otp_verifications`**: Manages Admin email activation.
    *   `email`, `otp_code`, `expires_at`, `used` (Boolean).
3.  **`admin_profiles`**: Extra metadata for the root Administrator.
4.  **`refresh_tokens`**: Manages secure 7-day session restoration. Includes token hashing and revocation flags.
5.  **`classes`**: Academic cohorts.
    *   `id`: UUID
    *   `admin_id`: UUID (Foreign Key to `users`)
    *   `class_name`: String
    *   `academic_year`: String
    *   `status`: String (`ACTIVE`, `ARCHIVED`)
6.  **`class_memberships`**: Junction table mapping Users to Classes.
    *   `member_role`: String (`MENTOR`, `STUDENT`)
    *   `status`: String (`PENDING`, `ACTIVE`, `REJECTED`)
    *   `joined_via`: String (`MANUAL`, `BULK_IMPORT`, `SIGNUP`)
    *   `is_primary_mentor`: Boolean (distinguishes classroom ownership)
7.  **`assignments`**: Assessment tasks.
    *   `status`: String (`DRAFT`, `PUBLISHED`, `CLOSED`)
    *   `content_type`: String (`PDF`, `LINK`, `RICH_TEXT`)
    *   `submission_type`: String (`FILE`, `TEXT`, `BOTH`)
    *   `deadline_at`: DateTime (timezone-aware)
    *   `auto_close`: Boolean
8.  **`submissions`**: Student work copies.
    *   `is_current`: Boolean (only the latest submission is active; previous submissions are marked inactive to maintain a full version history)
    *   `is_late`: Boolean (flagged on-write if submitted after the assignment deadline)
    *   `version`: Integer (increments on re-submission)
9.  **`student_analytics`**: Dynamic student tracking metrics.
    *   `completion_rate`: Numeric
    *   `current_streak`, `longest_streak`: Integer (consecutive on-time submissions)
    *   `consecutive_misses`: Integer (missed closed assignments in a row)
    *   `risk_level`: String (`NORMAL`, `LOW', `MEDIUM', `HIGH', `RECOVERING', `CRITICAL`)
10. **`class_analytics`** & **`assignment_analytics`**: Pre-calculated aggregations for performance dashboard visualization and bottleneck identification.

---

## 3. Core Features & Technical Implementation

### A. Multi-Role Authentication & Access Control (RBAC)
*   **JWT Implementation:** Upon successful login, the server issues a compact JSON Web Token (JWT) signed with a HS256 key. The payload includes:
    ```json
    {
      "sub": "user_uuid",
      "role": "MENTOR",
      "class_id": "class_uuid",
      "exp": 1719650000
    }
    ```
*   **Security Dependencies:** FastAPI dependencies enforce route security:
    *   `get_current_user`: Extracts, decodes, and validates the JWT signature.
    *   `require_role(roles)`: Curried function checking if the user's role matches route permissions.
    *   `verify_mentor_class_access` / `verify_admin_class_access`: Validates that a Mentor or Admin actually owns or is assigned to the classroom resources they are trying to access.
*   **Token Refresh Pipeline:** Implements a security layer where short-lived Access Tokens (e.g., 60 mins) are refreshed using cryptographically hashed Refresh Tokens. The refresh tokens are stored in the database and can be revoked instantly on logout.

### B. Class Roster & Enrollment Workflow
*   **Self-Enrollment:** Students sign up directly on the app, choosing their desired Class. This inserts a record in `class_memberships` with a `PENDING` status.
*   **Approval Pipeline:** Mentors or Admins receive an enrollment notification. Approving a student triggers the database state transition to `ACTIVE`, creates a corresponding blank `student_analytics` record, recalculates the class statistics, and shoots a push notification to the student's mobile device via Firebase.
*   **Co-Mentor Provisioning:** Admins can invite additional mentors. The backend automatically generates a secure random password, assigns a custom Mentor Registration ID, inserts their profile, and sends an invite email containing these credentials via Brevo SMTP.

### C. Assignment Lifecycle & Scheduling Engine
*   **States:** An assignment starts as a `DRAFT` and is invisible to students. Publishing updates the state to `PUBLISHED` and sets up the background automation jobs.
*   **Background Jobs (APScheduler):** When an assignment with a deadline is published, the backend registers three automated background jobs in the `SQLAlchemyJobStore`:
    1.  `send_reminder_job` (24h before deadline): Scrapes the database for active students in the class who have *not* submitted yet, records database notifications, and broadcasts a "Deadline Tomorrow" push notification.
    2.  `send_reminder_job` (2h before deadline): Sends a final push notification to remaining pending students.
    3.  `close_assignment_job` (at deadline, if `auto_close` is checked): Transition status to `CLOSED`, calculates final student analytics (recording misses for non-submitters), and broadcasts a "Missed Assignment" alert.

### D. Real-Time Submission Sync (WebSockets)
*   **Problem:** Mentors need live, second-by-second updates of submissions during classroom tests or deadlines without spamming APIs.
*   **Solution:** Built a custom WebSocket `ConnectionManager`:
    *   **Handshake & Auth:** Clients establish a WebSocket connection to `/api/v1/ws/tracker/{assignment_id}?token={jwt_token}`. The server performs connection auth by decoding the token query parameter and verifying class access before upgrading the HTTP connection.
    *   **Broadcast Mechanism:** When a student successfully submits their assignment via the `/submit` endpoint, the thread registers the database transaction, triggers an asynchronous broadcast call, and the manager pushes a structured update packet:
        ```json
        {
          "event": "submission_created",
          "assignment_id": "assignment_uuid",
          "submitted_count": 28,
          "pending_count": 2,
          "student": {
            "student_id": "student_uuid",
            "full_name": "John Doe",
            "tracker_status": "SUBMITTED",
            "submitted_at": "2026-06-29T08:30:00Z"
          }
        }
        ```
    *   **Resiliency:** The broadcast loop implements active disconnection scrubbing, instantly cleaning up stale or dropped socket descriptors.

### E. Academic Risk Detection Algorithm
Every time a student submits an assignment, or an assignment closes, the `analytics_service` performs a structured recalculation of the student's performance:
1.  **Streaks Evaluation:** Parses all closed assignments in the class from oldest to newest to compute the longest on-time submission streak, and from newest to oldest to determine the current streak.
2.  **Risk Level Classification:**
    *   **`CRITICAL`**: Student has missed **$\ge 4$ consecutive** closed assignments.
    *   **`HIGH`**: Student has missed **exactly 3 consecutive** closed assignments.
    *   **`MEDIUM`**: Student has an overall completion rate **$< 40\%$**.
    *   **`LOW`**: Student has an overall completion rate **$< 60\%$**.
    *   **`RECOVERING`**: Student was previously marked `HIGH` or `CRITICAL` but has brought their completion rate back **$\ge 60\%$**.
    *   **`NORMAL`**: Student matches none of the above risk profiles.
3.  **Alert Dispatch:** If a student's state transitions to `HIGH` or `CRITICAL`, the system triggers an immediate push notification directly to the student and adds a flag for the Mentor's dashboard.

### F. Conversational AI Query Assistant (Natural Language to SQL)
The backend hosts a sophisticated AI router (`routers/ai_query.py` + `services/ai_service.py`) that enables admins and mentors to query their class metrics conversationally.
1.  **Intent Parsing:** A system prompt asks Groq (Llama-3.1-8b) to parse the natural language query into one of 18 pre-defined system intents (e.g., `who_missed_assignment`, `streak_leaders`, `bottleneck_assignments`) and extract parameters (e.g., `student_name`, `assignment_ref`, `temporal_ref`).
2.  **Access Scoping:** The backend intercepts the parsed intent and strictly scopes the data queries. It restricts search results only to database rows belonging to classrooms the authenticated user has verified access to.
3.  **Fuzzy Reference Resolving:** Includes helper modules that clean class names and translate relative words (e.g., "today", "yesterday", "last week") into exact UTC timestamp ranges.
4.  **Data Generation:** The code maps the identified intent to dedicated database queries, formats the result, and generates UI-friendly navigation links (e.g., direct route redirects to the specific student's profile or assignment tracker).

### G. Bulk Provisioning Engine
*   **Workbook Structure:** Relies on a standard multi-sheet Excel file (.xlsx) containing three sheets: "Classes", "Mentors", and "Students".
*   **Asynchronous Processing:** To prevent network timeouts on HTTP threads when handling large rosters, the backend processes imports as background tasks:
    1.  Saves the uploaded file to a temporary directory on the server.
    2.  Spawns `BackgroundTasks` to invoke `process_bulk_import`.
    3.  Instantly returns an HTTP 202 response to the client with a `batch_id` to allow progress polling.
*   **Processing Pipeline:**
    *   Reads and validates each sheet row-by-row.
    *   Auto-creates classes, generates primary/co-mentor accounts, hashes secure passwords, and adds students to the classes.
    *   Accumulates validation errors in `bulk_import_errors` to give the Admin a descriptive report (e.g., "Row 12: Email already exists").
    *   Fires invitation credentials emails to all successfully created users.

### H. Data Exports
*   **Generation:** Mentors and Admins can export the full submission sheet of closed assignments. A background task creates an Excel spreadsheet via `openpyxl`, highlights rows based on student submission status (Green for Submitted, Yellow for Late, Red for Missed), and writes summary stats on a separate sheet.
*   **S3 Storage Lifecycle:** The generated spreadsheet is uploaded to S3. Rather than returning public links, the server returns presigned download URLs with a 5-minute expiration window to guarantee maximum security for student records.

---

## 4. Deployment, Setup & Environment Configuration

### A. Environment Configurations (`.env`)
The backend service relies on the following key environment variables:

| Variable Name | Example Value | Purpose |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql://user:pass@host:5432/db` | Database connection string |
| `JWT_SECRET_KEY` | `supersecrethexkey...` | Symmetric key for signing JWTs |
| `JWT_ALGORITHM` | `HS256` | Token encryption standard |
| `AWS_ACCESS_KEY_ID` | `AKIA...` | AWS IAM User access key |
| `AWS_SECRET_ACCESS_KEY` | `wJalrXUtnFEMI...` | AWS IAM User secret key |
| `S3_BUCKET_NAME` | `assignhub-storage` | S3 bucket for template/report storage |
| `AWS_REGION` | `us-east-1` | AWS S3 deployment region |
| `FCM_CREDENTIALS_JSON` | `{"type": "service_account", ...}` | Google Firebase Service Account credentials |
| `GMAIL_ADDRESS` | `admin@gmail.com` | Google account for SMTP alerts |
| `GMAIL_APP_PASSWORD` | `abcd efgh ijkl mnop` | Google App Password for secure SMTP |
| `BREVO_SMTP_HOST` | `smtp-relay.brevo.com` | Brevo SMTP host address |
| `BREVO_SMTP_KEY` | `xsmtpsib-...` | Brevo SMTP authorization token |
| `GROQ_API_KEY` | `gsk_...` | Groq console key for LLM inference |

### B. Startup Schema Automations (`main.py`)
To simplify deployments and migrations on ephemeral environments (like Render Free Instances), the FastAPI startup lifespan includes hook functions:
1.  **Metadata Inspection:** Calls `Base.metadata.create_all(bind=engine)` to dynamically inspect database tables and auto-create them if they do not exist.
2.  **Constraint Hardening:** Runs an alter-table statement on startup to drop and recreate the PostgreSQL check constraint `check_sa_risk` on the `student_analytics` table, ensuring the application can support the new `'CRITICAL'` risk state safely.
3.  **Scheduler Boot:** Ensures `APScheduler` starts running alongside the ASGI event loop, recovering any pending jobs persisted in the database store.

---

## 5. Typical Workflow Walkthroughs (For Interview Demos)

### 1. Student Submission & Live Dashboard Sync
1.  A student submits text or a PDF assignment from the mobile client.
2.  FastAPI executes the `/submit` endpoint:
    *   Saves submission with file URL and stamps the upload time.
    *   Determines if late (`submitted_at > deadline_at`).
    *   Recalculates student's metrics (streaks, rates).
3.  FastAPI triggers the `ConnectionManager` to push the update packet via active WebSockets.
4.  The mentor's dashboard updates in real time, shifting the student's status cell dynamically without refreshing the page.

### 2. Conversational Analytics Check
1.  The Mentor opens the chatbot in the app and types: *"Who missed the homework in Class A today?"*
2.  The backend routes this query to the LLM agent using Groq.
3.  The agent outputs: `{"intent": "who_missed_assignment", "params": {"assignment_ref": "homework", "temporal_ref": "today"}}`.
4.  The service resolves "Class A" and "today" into UUIDs and timestamps, filters the database for active students with no current submission, and returns a formatted JSON payload.
5.  The mobile client parses this structured response to display a list of the 3 students who missed the homework, along with clickable profile cards.
