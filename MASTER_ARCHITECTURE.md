# AssignHub — Master Architecture Document
**Version:** 2.0 — Final (Evaluation-Corrected)  
**Hackathon:** DevFusion 3.0 | Problem Statement #26ENAH1  
**Stack:** Flutter (Android APK) · FastAPI · PostgreSQL · AWS S3 · FCM · Brevo SMTP · Gmail SMTP · Render  
**Roles:** Admin · Mentor · Student  
**Rule:** Zero mock data. Zero hardcoded values. Every frontend value comes from a live API call.

---

## Table of Contents
1. System Overview & Module Map
2. Folder Structure
3. Database Schema (All 18 Tables)
4. Authentication & Authorization
5. API Endpoint Contract (Full Specification)
6. Feature Data Flows (Step-by-Step)
7. WebSocket Design
8. S3 File Upload Flow
9. Notification & Email Flow
10. Analytics Layer (Per Role)
11. Risk Engine Logic
12. Bulk Import Architecture
13. AI Query Assistant
14. Frontend Screen Map & UI Behavior
15. Frontend ↔ Backend Field Contract
16. Deployment Architecture
17. No-Mismatch Contract

---

## 1. System Overview & Module Map

AssignHub is a role-based assignment management platform. Admin is the only self-registering role. Mentors and students are provisioned by admin and receive login credentials via email.

### 1.1 Core Rules (Binding for all implementation)
- Admin self-registers with email + password + OTP verification
- Mentor and Student never self-register — admin creates them
- Mentor/Student login requires: `email` + `password` + `registration_id`
- Student login is blocked until `class_memberships.status = ACTIVE` (approved by mentor/admin)
- Every student belongs to exactly one class
- Every class has one primary mentor; admin can add co-mentors later
- Students see only their own class data
- Mentors see only their assigned class(es)
- Admin sees all classes; can drill into any class
- Zero hardcoded data — everything rendered from live DB queries
- `class_memberships.status` controls class-level access (PENDING → ACTIVE → INACTIVE/REJECTED)
- `users.status` controls account-level validity (PENDING_OTP → ACTIVE → INACTIVE/BLOCKED)

### 1.2 Module Interaction Map

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Flutter App (APK)                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │  Auth    │  │ Admin    │  │ Mentor   │  │ Student            │ │
│  │  Module  │  │ Module   │  │ Module   │  │ Module             │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬───────────┘ │
│       │              │              │                  │             │
│       └──────────────┴──────────────┴──────────────────┘            │
│                              │ Dio HTTP + WSS                        │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
               ┌───────────────▼──────────────────┐
               │     FastAPI Backend (Render)      │
               │  ┌──────────┐  ┌──────────────┐  │
               │  │ Routers  │  │  Services    │  │
               │  │ auth     │  │  analytics   │  │
               │  │ classes  │  │  risk_engine │  │
               │  │ assign   │  │  email       │  │
               │  │ submit   │  │  fcm         │  │
               │  │ analytics│  │  s3          │  │
               │  │ ai_query │  │  ai_service  │  │
               │  │ exports  │  │  export      │  │
               │  │ notifs   │  │  scheduler   │  │
               │  └──────────┘  └──────────────┘  │
               │         │              │           │
               └─────────┼──────────────┼───────────┘
                         │              │
            ┌────────────▼──┐   ┌───────▼──────────┐
            │  PostgreSQL   │   │  External Services│
            │  (Render DB)  │   │  ┌─────────────┐  │
            └───────────────┘   │  │ AWS S3      │  │
                                │  │ FCM         │  │
                                │  │ Brevo SMTP  │  │
                                │  │ Gmail SMTP  │  │
                                │  │ Gemini/Groq │  │
                                │  └─────────────┘  │
                                └───────────────────┘

APScheduler (in-process, PostgreSQL jobstore):
  └── deadline_close_job(assignment_id)
  └── deadline_reminder_24h(assignment_id)
  └── deadline_reminder_2h(assignment_id)
```

---

## 2. Folder Structure

```
AssignHub/
├── Frontend/                          ← Flutter developer works here only
│   ├── pubspec.yaml
│   ├── pubspec.lock
│   ├── android/
│   ├── ios/
│   ├── assets/
│   │   └── images/
│   └── lib/
│       ├── main.dart                  # App entry, GoRouter init, theme
│       ├── core/
│       │   ├── api_client.dart        # Dio instance, base URL, interceptors
│       │   ├── auth_storage.dart      # flutter_secure_storage wrapper
│       │   ├── ws_client.dart         # WebSocket connection manager
│       │   ├── router.dart            # GoRouter routes + role guards
│       │   ├── constants.dart         # API base URL, enum strings
│       │   └── exceptions.dart        # AppException, ApiException types
│       ├── models/
│       │   ├── user_model.dart
│       │   ├── class_model.dart
│       │   ├── assignment_model.dart
│       │   ├── submission_model.dart
│       │   ├── analytics_model.dart
│       │   ├── notification_model.dart
│       │   └── ai_response_model.dart
│       ├── providers/                 # Riverpod StateNotifiers
│       │   ├── auth_provider.dart
│       │   ├── class_provider.dart
│       │   ├── assignment_provider.dart
│       │   ├── submission_provider.dart
│       │   ├── analytics_provider.dart
│       │   ├── notification_provider.dart
│       │   └── ai_provider.dart
│       ├── services/
│       │   ├── auth_service.dart      # Calls /auth/* endpoints
│       │   ├── class_service.dart     # Calls /classes/* endpoints
│       │   ├── assignment_service.dart
│       │   ├── submission_service.dart
│       │   ├── analytics_service.dart
│       │   ├── storage_service.dart   # Presigned upload calls
│       │   ├── notification_service.dart
│       │   ├── export_service.dart
│       │   └── ai_service.dart
│       ├── screens/
│       │   ├── auth/
│       │   │   ├── splash_screen.dart
│       │   │   ├── login_screen.dart
│       │   │   ├── admin_signup_screen.dart
│       │   │   └── otp_verify_screen.dart
│       │   ├── admin/
│       │   │   ├── admin_dashboard_screen.dart
│       │   │   ├── class_list_screen.dart
│       │   │   ├── create_class_screen.dart
│       │   │   ├── class_detail_screen.dart
│       │   │   ├── class_students_screen.dart
│       │   │   ├── approvals_screen.dart
│       │   │   ├── student_profile_screen.dart
│       │   │   ├── bulk_import_screen.dart
│       │   │   ├── add_co_mentor_screen.dart
│       │   │   ├── analytics_overview_screen.dart
│       │   │   ├── class_analytics_drill_screen.dart
│       │   │   └── ai_query_screen.dart
│       │   ├── mentor/
│       │   │   ├── mentor_dashboard_screen.dart
│       │   │   ├── student_list_screen.dart
│       │   │   ├── student_profile_screen.dart
│       │   │   ├── approvals_screen.dart
│       │   │   ├── assignment_list_screen.dart
│       │   │   ├── create_assignment_screen.dart
│       │   │   ├── assignment_tracker_screen.dart
│       │   │   ├── submission_detail_screen.dart
│       │   │   ├── analytics_screen.dart
│       │   │   ├── risk_list_screen.dart
│       │   │   ├── export_screen.dart
│       │   │   └── ai_query_screen.dart
│       │   └── student/
│       │       ├── student_dashboard_screen.dart
│       │       ├── assignment_list_screen.dart
│       │       ├── assignment_detail_screen.dart
│       │       ├── submit_assignment_screen.dart
│       │       ├── submission_history_screen.dart
│       │       ├── my_analytics_screen.dart
│       │       └── notifications_screen.dart
│       └── widgets/
│           ├── risk_badge_widget.dart
│           ├── tracker_card_widget.dart
│           ├── analytics_chart_widget.dart
│           ├── assignment_card_widget.dart
│           ├── notification_tile_widget.dart
│           ├── loading_widget.dart
│           ├── error_widget.dart
│           └── server_wakeup_widget.dart  # Cold start handler
│
└── Backend/                           ← Backend developer works here only
    ├── .env                           # All secrets (never commit)
    ├── .env.example                   # Template with key names only
    ├── requirements.txt
    ├── alembic.ini                    # DB migrations
    ├── alembic/
    │   └── versions/
    │       └── 001_initial_schema.py
    ├── main.py                        # FastAPI app, router registration, CORS, lifespan
    ├── database.py                    # SQLAlchemy engine, session factory
    ├── models/                        # SQLAlchemy ORM models
    │   ├── __init__.py
    │   ├── user.py
    │   ├── class_.py
    │   ├── assignment.py
    │   ├── submission.py
    │   ├── analytics.py
    │   ├── notification.py
    │   ├── bulk_import.py
    │   └── export.py
    ├── schemas/                       # Pydantic request/response models
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── class_.py
    │   ├── assignment.py
    │   ├── submission.py
    │   ├── analytics.py
    │   ├── notification.py
    │   ├── provision.py
    │   ├── export.py
    │   └── ai_query.py
    ├── routers/
    │   ├── __init__.py
    │   ├── auth.py
    │   ├── classes.py
    │   ├── provisioning.py
    │   ├── assignments.py
    │   ├── submissions.py
    │   ├── storage.py
    │   ├── analytics.py
    │   ├── notifications.py
    │   ├── exports.py
    │   └── ai_query.py
    ├── services/
    │   ├── __init__.py
    │   ├── auth_service.py            # JWT + bcrypt helpers
    │   ├── email_service.py           # Gmail SMTP + Brevo SMTP
    │   ├── fcm_service.py             # Firebase Cloud Messaging
    │   ├── s3_service.py              # Presigned URL generation
    │   ├── analytics_service.py       # recompute_student_analytics(), recompute_class_analytics()
    │   ├── export_service.py          # openpyxl XLSX generation
    │   └── ai_service.py             # LLM call + intent dispatch
    ├── websocket/
    │   └── tracker_ws.py             # WebSocket connection manager + broadcast
    ├── scheduler/
    │   └── jobs.py                   # APScheduler setup with PostgreSQL jobstore
    └── utils/
        ├── id_generator.py           # registration_id generator
        ├── security.py               # password hashing, token creation
        └── dependencies.py           # FastAPI Depends() helpers (get_current_user, require_role)
```

---

## 3. Database Schema

### Schema Rules
- All primary keys: `UUID` using `gen_random_uuid()`
- All timestamps: `TIMESTAMPTZ` (timezone-aware)
- All enum-like values: `VARCHAR` with `CHECK` constraints, uppercase strings
- All foreign keys: `ON DELETE CASCADE` unless noted
- Field naming: `snake_case` throughout

---

### 3.1 `users`

```sql
CREATE TABLE users (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  role              VARCHAR(10) NOT NULL CHECK (role IN ('ADMIN','MENTOR','STUDENT')),
  full_name         VARCHAR(120) NOT NULL,
  email             VARCHAR(255) UNIQUE NOT NULL,
  password_hash     TEXT        NOT NULL,
  registration_id   VARCHAR(50) UNIQUE,
  -- NULL for admin. Generated by backend for mentor (MENTOR-<shortUUID>).
  -- Supplied by admin for student (matches institution roll number).
  phone             VARCHAR(20),
  status            VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('PENDING_OTP','ACTIVE','INACTIVE','BLOCKED')),
  -- Admin starts as PENDING_OTP, becomes ACTIVE after OTP.
  -- Mentor and Student are created as ACTIVE (account is valid).
  -- Class membership status (PENDING/ACTIVE) controls class access separately.
  fcm_token         TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

---

### 3.2 `otp_verifications`

```sql
CREATE TABLE otp_verifications (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  email       VARCHAR(255) NOT NULL,
  otp_code    VARCHAR(6)  NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  used        BOOLEAN     NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_otp_email ON otp_verifications(email);
```

---

### 3.3 `admin_profiles`

```sql
CREATE TABLE admin_profiles (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_name VARCHAR(150),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.4 `refresh_tokens`

```sql
CREATE TABLE refresh_tokens (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT        NOT NULL,
  expires_at  TIMESTAMPTZ NOT NULL,
  revoked     BOOLEAN     NOT NULL DEFAULT false,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);
```

---

### 3.5 `classes`

```sql
CREATE TABLE classes (
  id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  class_name     VARCHAR(150) NOT NULL,
  description    TEXT,
  academic_year  VARCHAR(20),
  status         VARCHAR(10) NOT NULL DEFAULT 'ACTIVE'
                 CHECK (status IN ('ACTIVE','ARCHIVED')),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_classes_admin ON classes(admin_id);
```

---

### 3.6 `class_memberships`

```sql
CREATE TABLE class_memberships (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id          UUID        NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  member_role       VARCHAR(10) NOT NULL CHECK (member_role IN ('MENTOR','STUDENT')),
  is_primary_mentor BOOLEAN     NOT NULL DEFAULT false,
  joined_via        VARCHAR(15) NOT NULL CHECK (joined_via IN ('MANUAL','BULK_IMPORT')),
  status            VARCHAR(10) NOT NULL DEFAULT 'PENDING'
                    CHECK (status IN ('ACTIVE','INACTIVE','PENDING','REJECTED')),
  -- PENDING: created but not yet approved by mentor/admin
  -- ACTIVE:  approved, can log in and access class
  -- REJECTED: denied access
  -- INACTIVE: was active, deactivated later
  rejection_reason  TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(class_id, user_id)
);
CREATE INDEX idx_cm_class ON class_memberships(class_id);
CREATE INDEX idx_cm_user ON class_memberships(user_id);
CREATE INDEX idx_cm_status ON class_memberships(status);
```

**Important:** Mentors are created with `status = ACTIVE` (they don't need approval). Students are created with `status = PENDING` (must be approved by mentor or admin before login succeeds).

---

### 3.7 `assignments`

```sql
CREATE TABLE assignments (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id         UUID        NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  created_by       UUID        NOT NULL REFERENCES users(id),
  title            VARCHAR(200) NOT NULL,
  description      TEXT,
  content_type     VARCHAR(10) NOT NULL CHECK (content_type IN ('PDF','LINK','RICH_TEXT')),
  content_url      TEXT,
  -- S3 URL if content_type=PDF, external URL if content_type=LINK, NULL if RICH_TEXT
  rich_text_body   TEXT,
  -- Populated only if content_type=RICH_TEXT
  submission_type  VARCHAR(5)  NOT NULL CHECK (submission_type IN ('FILE','TEXT','BOTH')),
  deadline_at      TIMESTAMPTZ,
  -- NULL means mentor closes manually. Non-null triggers APScheduler job on publish.
  auto_close       BOOLEAN     NOT NULL DEFAULT false,
  -- true if deadline_at is set at publish time
  status           VARCHAR(10) NOT NULL DEFAULT 'DRAFT'
                   CHECK (status IN ('DRAFT','PUBLISHED','CLOSED')),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_assignments_class ON assignments(class_id);
CREATE INDEX idx_assignments_status ON assignments(status);
```

---

### 3.8 `submissions`

```sql
CREATE TABLE submissions (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id    UUID        NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  student_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  submission_type  VARCHAR(5)  NOT NULL CHECK (submission_type IN ('FILE','TEXT')),
  file_url         TEXT,
  -- S3 URL. NULL if submission_type=TEXT.
  text_answer      TEXT,
  -- NULL if submission_type=FILE.
  is_late          BOOLEAN     NOT NULL DEFAULT false,
  version          INT         NOT NULL DEFAULT 1,
  is_current       BOOLEAN     NOT NULL DEFAULT true,
  -- Only the latest submission per student per assignment has is_current=true.
  submitted_at     TIMESTAMPTZ NOT NULL,
  -- Set explicitly by backend to datetime.utcnow() at request time. Not DEFAULT now().
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(assignment_id, student_id, version)
);
CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_submissions_current ON submissions(is_current);
```

---

### 3.9 `student_analytics`

```sql
CREATE TABLE student_analytics (
  id                        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  student_id                UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  class_id                  UUID         NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  total_assigned            INT          NOT NULL DEFAULT 0,
  total_submitted           INT          NOT NULL DEFAULT 0,
  total_missed              INT          NOT NULL DEFAULT 0,
  total_late                INT          NOT NULL DEFAULT 0,
  completion_rate           NUMERIC(5,2) NOT NULL DEFAULT 0,
  current_streak            INT          NOT NULL DEFAULT 0,
  longest_streak            INT          NOT NULL DEFAULT 0,
  avg_submission_delay_hours NUMERIC(6,2),
  -- Average hours between submission and deadline. Positive = submitted early. Negative = submitted late.
  -- NULL if no submissions yet.
  risk_level                VARCHAR(12)  NOT NULL DEFAULT 'NORMAL'
                            CHECK (risk_level IN ('NORMAL','LOW','MEDIUM','HIGH','RECOVERING')),
  consecutive_misses        INT          NOT NULL DEFAULT 0,
  last_computed_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),
  UNIQUE(student_id, class_id)
);
CREATE INDEX idx_sa_student ON student_analytics(student_id);
CREATE INDEX idx_sa_class ON student_analytics(class_id);
CREATE INDEX idx_sa_risk ON student_analytics(risk_level);
```

**Note:** Row is inserted with all-zero defaults when a student's membership is approved (status set to ACTIVE). This guarantees the row always exists — Flutter never crashes on null.

---

### 3.10 `class_analytics`

```sql
CREATE TABLE class_analytics (
  id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id         UUID         UNIQUE NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  total_students   INT          NOT NULL DEFAULT 0,
  total_assignments INT         NOT NULL DEFAULT 0,
  avg_completion   NUMERIC(5,2) NOT NULL DEFAULT 0,
  avg_miss_rate    NUMERIC(5,2) NOT NULL DEFAULT 0,
  avg_late_rate    NUMERIC(5,2) NOT NULL DEFAULT 0,
  high_risk_count  INT          NOT NULL DEFAULT 0,
  last_computed_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

**Note:** Row is inserted when class is created (all zeros). Recomputed after every assignment close.

---

### 3.11 `assignment_analytics`

```sql
CREATE TABLE assignment_analytics (
  id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id    UUID         UNIQUE NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  total_targets    INT          NOT NULL DEFAULT 0,
  submitted_count  INT          NOT NULL DEFAULT 0,
  missed_count     INT          NOT NULL DEFAULT 0,
  late_count       INT          NOT NULL DEFAULT 0,
  completion_rate  NUMERIC(5,2) NOT NULL DEFAULT 0,
  is_bottleneck    BOOLEAN      NOT NULL DEFAULT false,
  -- true if completion_rate < 50% after close
  last_computed_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

**Note:** Row is inserted with `total_targets = active student count` when assignment is published.

---

### 3.12 `notifications`

```sql
CREATE TABLE notifications (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  notification_type VARCHAR(30) NOT NULL CHECK (notification_type IN (
                    'STUDENT_APPROVED',
                    'STUDENT_REJECTED',
                    'ASSIGNMENT_PUBLISHED',
                    'DEADLINE_REMINDER',
                    'SUBMISSION_RECEIPT',
                    'MISSED_DEADLINE',
                    'RISK_ALERT',
                    'CO_MENTOR_ADDED',
                    'CLASS_ARCHIVED'
                    )),
  title             VARCHAR(200) NOT NULL,
  body              TEXT        NOT NULL,
  payload           JSONB,
  -- { "assignment_id": "uuid", "class_id": "uuid", "student_id": "uuid" } — only relevant keys included
  is_read           BOOLEAN     NOT NULL DEFAULT false,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notif_user ON notifications(user_id);
CREATE INDEX idx_notif_read ON notifications(is_read);
```

---

### 3.13 `reminder_jobs`

```sql
CREATE TABLE reminder_jobs (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  assignment_id UUID        NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  remind_at     TIMESTAMPTZ NOT NULL,
  status        VARCHAR(12) NOT NULL DEFAULT 'SCHEDULED'
                CHECK (status IN ('SCHEDULED','TRIGGERED','CANCELLED')),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.14 `bulk_import_batches`

```sql
CREATE TABLE bulk_import_batches (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  admin_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  file_name     VARCHAR(255),
  status        VARCHAR(20) NOT NULL DEFAULT 'UPLOADED'
                CHECK (status IN ('UPLOADED','VALIDATING','PARTIAL','COMPLETED','FAILED')),
  total_rows    INT         NOT NULL DEFAULT 0,
  success_rows  INT         NOT NULL DEFAULT 0,
  failed_rows   INT         NOT NULL DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.15 `bulk_import_errors`

```sql
CREATE TABLE bulk_import_errors (
  id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  batch_id      UUID        NOT NULL REFERENCES bulk_import_batches(id) ON DELETE CASCADE,
  sheet_name    VARCHAR(20) NOT NULL,
  row_number    INT         NOT NULL,
  field_name    VARCHAR(100),
  error_message TEXT        NOT NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.16 `export_jobs`

```sql
CREATE TABLE export_jobs (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  requested_by     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  assignment_id    UUID        REFERENCES assignments(id) ON DELETE CASCADE,
  export_type      VARCHAR(30) NOT NULL CHECK (export_type IN ('ASSIGNMENT_TRACKER')),
  format           VARCHAR(5)  NOT NULL DEFAULT 'XLSX',
  status           VARCHAR(10) NOT NULL DEFAULT 'PENDING'
                   CHECK (status IN ('PENDING','DONE','FAILED')),
  file_url         TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.17 `ai_query_logs`

```sql
CREATE TABLE ai_query_logs (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  requested_by     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  class_id         UUID        REFERENCES classes(id) ON DELETE SET NULL,
  query_text       TEXT        NOT NULL,
  detected_intent  VARCHAR(50),
  filters          JSONB,
  response_payload JSONB,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

### 3.18 `scheduler_jobs` (APScheduler PostgreSQL jobstore — auto-managed)

This table is created and managed automatically by APScheduler when configured with `SQLAlchemyJobStore`. Do not manually create or alter it.

---

### 3.19 Table Relationships

```
users ──(1:1)──► admin_profiles
users ──(1:N)──► class_memberships ──(N:1)──► classes
users ──(1:N)──► submissions       ──(N:1)──► assignments ──(N:1)──► classes
users ──(1:N)──► student_analytics ──(N:1)──► classes
classes ──(1:1)──► class_analytics
assignments ──(1:1)──► assignment_analytics
assignments ──(1:N)──► submissions
assignments ──(1:N)──► reminder_jobs
```

---

## 4. Authentication & Authorization

### 4.1 JWT Token Design

**Access Token payload:**
```json
{
  "sub": "user_uuid_string",
  "role": "ADMIN | MENTOR | STUDENT",
  "class_id": "uuid_string_or_null",
  "exp": 1234567890
}
```

- `class_id` is `null` for ADMIN (admin has no single class)
- `class_id` is the student's/mentor's class UUID for MENTOR and STUDENT
- For mentors assigned to multiple classes, `class_id` = primary class. Co-mentor classes fetched separately via `/classes/my-classes`

| Token | Expiry | Flutter Storage |
|---|---|---|
| access_token | 60 minutes | `flutter_secure_storage` key: `access_token` |
| refresh_token | 7 days | `flutter_secure_storage` key: `refresh_token` |

**Flutter Dio interceptor behavior:**
- Every request: add `Authorization: Bearer <access_token>` header
- On 401 response: call `POST /auth/refresh` with stored refresh_token
- On refresh success: store new access_token, retry original request
- On refresh failure (token expired/revoked): clear storage, redirect to `/login`

---

### 4.2 Admin Signup Flow

```
Step 1: Flutter → POST /api/v1/auth/admin/signup
  Request body: { "full_name": "string", "email": "string", "password": "string" }
  
  Backend:
    1. SELECT COUNT(*) FROM users WHERE email = :email → if > 0, return 409
    2. bcrypt.hash(password, rounds=12) → password_hash
    3. INSERT INTO users (role='ADMIN', full_name, email, password_hash, status='PENDING_OTP')
    4. Generate OTP: str(random.randint(100000, 999999))
    5. INSERT INTO otp_verifications (email, otp_code, expires_at=now()+10min)
    6. Send OTP via Gmail SMTP to admin email
    7. Return 201: { "message": "OTP sent to your email" }

Step 2: Flutter → POST /api/v1/auth/admin/verify-otp
  Request body: { "email": "string", "otp": "string" }
  
  Backend:
    1. SELECT * FROM otp_verifications WHERE email = :email AND used = false ORDER BY created_at DESC LIMIT 1
    2. If not found → 400 "No pending OTP"
    3. If otp_verifications.expires_at < now() → 410 "OTP expired"
    4. If otp_verifications.otp_code != :otp → 400 "Invalid OTP"
    5. UPDATE otp_verifications SET used = true WHERE id = :otp_id
    6. UPDATE users SET status = 'ACTIVE' WHERE email = :email
    7. INSERT INTO admin_profiles (user_id) VALUES (:user_id)
    8. INSERT INTO class_analytics is NOT done here (class not created yet)
    9. Generate access_token + refresh_token (sign with JWT_SECRET_KEY)
    10. INSERT INTO refresh_tokens (user_id, token_hash=bcrypt(refresh_token), expires_at)
    11. Return 200: { "access_token", "refresh_token", "user": { "id", "full_name", "role": "ADMIN" } }
```

---

### 4.3 Mentor and Student Login Flow

```
Flutter → POST /api/v1/auth/login
  Request body: {
    "email": "string",
    "password": "string",
    "registration_id": "string",
    "fcm_token": "string"       ← optional, can be empty string
  }
  
  Backend:
    1. SELECT * FROM users WHERE email = :email
       → if not found: 401 "Invalid credentials" (do not reveal reason)
    2. bcrypt.verify(:password, users.password_hash)
       → if false: 401 "Invalid credentials"
    3. If users.role IN ('MENTOR','STUDENT'):
         Check users.registration_id == :registration_id
         → if mismatch: 401 "Invalid credentials"
    4. If users.role == 'ADMIN':
         Skip registration_id check
    5. Check users.status == 'ACTIVE'
       → if PENDING_OTP: 403 "Account not verified"
       → if BLOCKED: 403 "Account blocked"
       → if INACTIVE: 403 "Account inactive"
    6. If role == 'STUDENT':
         SELECT * FROM class_memberships WHERE user_id = :user_id AND status = 'ACTIVE'
         → if not found: 403 "Account pending approval. Please wait for your mentor to approve your access."
    7. If role == 'MENTOR':
         SELECT * FROM class_memberships WHERE user_id = :user_id AND status = 'ACTIVE' LIMIT 1
         → if not found: 403 "No active class assignment found"
    8. If fcm_token is non-empty: UPDATE users SET fcm_token = :fcm_token WHERE id = :user_id
    9. Get class_id:
         ADMIN: class_id = null
         MENTOR/STUDENT: class_id = class_memberships.class_id (primary/only class)
    10. Get class_name:
         JOIN classes WHERE classes.id = class_id
    11. Generate access_token (sub=user_id, role, class_id, exp=now+60min)
    12. Generate refresh_token (random UUID)
    13. INSERT INTO refresh_tokens (user_id, token_hash=bcrypt(refresh_token), expires_at=now+7days)
    14. Return 200: {
          "access_token": "string",
          "refresh_token": "string",
          "user": {
            "id": "uuid",
            "full_name": "string",
            "email": "string",
            "role": "ADMIN|MENTOR|STUDENT",
            "class_id": "uuid or null",
            "class_name": "string or null",
            "registration_id": "string or null"
          }
        }
```

---

### 4.4 Token Refresh

```
Flutter → POST /api/v1/auth/refresh
  Request body: { "refresh_token": "string" }
  
  Backend:
    1. SELECT * FROM refresh_tokens WHERE revoked = false AND expires_at > now()
    2. For each row: bcrypt.verify(:refresh_token, token_hash)
       → find matching row
    3. If not found or expired: 401 "Invalid refresh token"
    4. Get user from refresh_tokens.user_id
    5. Re-fetch class_id from class_memberships (in case it changed)
    6. Generate new access_token
    7. Return 200: { "access_token": "string" }
```

---

### 4.5 Logout

```
Flutter → POST /api/v1/auth/logout
  Headers: Authorization: Bearer <access_token>
  Request body: { "refresh_token": "string" }
  
  Backend:
    1. Find refresh_token row by hash match
    2. UPDATE refresh_tokens SET revoked = true WHERE id = :token_id
    3. Return 200: { "message": "Logged out" }
  
  Flutter (on any logout response):
    1. Delete access_token from SecureStorage
    2. Delete refresh_token from SecureStorage
    3. Navigate to /login, replace stack
```

---

### 4.6 Route Authorization (Backend Enforcement)

All protected routes use `Depends(get_current_user)` from `utils/dependencies.py`.

`get_current_user` decodes JWT, fetches user from DB, returns user object.

Role checks use `Depends(require_role(['ADMIN']))` etc.

**Class ownership check** (used on every class-scoped endpoint for MENTOR):
```python
# In utils/dependencies.py
def verify_mentor_class_access(class_id: UUID, current_user: User, db: Session):
    membership = db.query(ClassMembership).filter(
        ClassMembership.user_id == current_user.id,
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'MENTOR',
        ClassMembership.status == 'ACTIVE'
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized for this class")
    return membership
```

**Admin class ownership check:**
```python
def verify_admin_class_access(class_id: UUID, current_user: User, db: Session):
    class_ = db.query(Class).filter(
        Class.id == class_id,
        Class.admin_id == current_user.id
    ).first()
    if not class_:
        raise HTTPException(status_code=403, detail="Class not found or not yours")
    return class_
```

**Student self-access check** (analytics/submissions):
```python
# Student can only access their own student_id
# Backend: if current_user.role == 'STUDENT' and student_id != current_user.id → 403
```

---

### 4.7 Role Permissions Table

| Endpoint | ADMIN | MENTOR | STUDENT |
|---|---|---|---|
| POST /auth/admin/signup | ✅ | ❌ | ❌ |
| POST /auth/login | ✅ | ✅ | ✅ |
| POST /classes | ✅ | ❌ | ❌ |
| GET /classes | ✅ | ❌ (use /classes/my-classes) | ❌ |
| GET /classes/{id} | ✅ (own) | ✅ (own) | ❌ |
| GET /classes/{id}/approvals | ✅ (own) | ✅ (own) | ❌ |
| PATCH /classes/{id}/students/{sid}/approve | ✅ | ✅ (own class) | ❌ |
| PATCH /classes/{id}/students/{sid}/reject | ✅ | ✅ (own class) | ❌ |
| POST /classes/{id}/co-mentors | ✅ (own) | ❌ | ❌ |
| POST /provision/manual/mentor | ✅ | ❌ | ❌ |
| POST /provision/manual/student | ✅ | ✅ (own class) | ❌ |
| POST /provision/bulk-import | ✅ | ❌ | ❌ |
| POST /assignments | ✅ | ✅ (own class) | ❌ |
| GET /assignments | ✅ | ✅ (own class) | ✅ (PUBLISHED only, own class) |
| POST /assignments/{id}/publish | ✅ | ✅ (own class) | ❌ |
| POST /assignments/{id}/close | ✅ | ✅ (own class) | ❌ |
| GET /assignments/{id}/tracker | ✅ | ✅ (own class) | ❌ |
| POST /assignments/{id}/submit | ❌ | ❌ | ✅ (ACTIVE, own class) |
| GET /submissions/my | ❌ | ❌ | ✅ |
| GET /analytics/admin/overview | ✅ | ❌ | ❌ |
| GET /analytics/classes/{id} | ✅ (own) | ✅ (own) | ❌ |
| GET /analytics/students/{id} | ✅ | ✅ (own class) | ✅ (own only) |
| POST /ai/query | ✅ | ✅ | ❌ |
| POST /exports/assignment-tracker | ✅ | ✅ (own class) | ❌ |

---

## 5. API Endpoint Contract

**Base URL:** `https://assignhub-api.onrender.com/api/v1`  
**Auth header:** `Authorization: Bearer <access_token>` (all protected routes)  
**Content-Type:** `application/json` (all JSON routes)

---

### 5.1 Health

#### GET `/health`
**Auth:** None  
**Purpose:** Flutter calls on app launch to wake Render server  
**Response 200:**
```json
{ "status": "ok", "timestamp": "2026-06-25T10:00:00Z" }
```

---

### 5.2 Auth Router `/auth`

#### POST `/auth/admin/signup`
**Auth:** None  
**Request:**
```json
{ "full_name": "string", "email": "string", "password": "string" }
```
**Response 201:**
```json
{ "message": "OTP sent to your email" }
```
**Errors:** `409` email already exists

---

#### POST `/auth/admin/verify-otp`
**Auth:** None  
**Request:**
```json
{ "email": "string", "otp": "string" }
```
**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": { "id": "uuid", "full_name": "string", "role": "ADMIN" }
}
```
**Errors:** `400` invalid OTP, `410` OTP expired

---

#### POST `/auth/login`
**Auth:** None  
**Request:**
```json
{
  "email": "string",
  "password": "string",
  "registration_id": "string",
  "fcm_token": "string"
}
```
**Note:** Admin sends `registration_id` as empty string `""`. Backend skips check if role=ADMIN.

**Response 200:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": {
    "id": "uuid",
    "full_name": "string",
    "email": "string",
    "role": "ADMIN | MENTOR | STUDENT",
    "class_id": "uuid | null",
    "class_name": "string | null",
    "registration_id": "string | null"
  }
}
```
**Errors:** `401` invalid credentials, `403` pending approval / blocked / inactive

---

#### POST `/auth/refresh`
**Auth:** None  
**Request:** `{ "refresh_token": "string" }`  
**Response 200:** `{ "access_token": "string" }`  
**Errors:** `401` invalid or expired refresh token

---

#### POST `/auth/logout`
**Auth:** Bearer  
**Request:** `{ "refresh_token": "string" }`  
**Response 200:** `{ "message": "Logged out" }`

---

#### GET `/auth/me`
**Auth:** Bearer  
**Backend query:**
```sql
SELECT u.id, u.full_name, u.email, u.role, u.registration_id, u.status,
       cm.class_id, c.class_name
FROM users u
LEFT JOIN class_memberships cm ON cm.user_id = u.id AND cm.status = 'ACTIVE'
LEFT JOIN classes c ON c.id = cm.class_id
WHERE u.id = :user_id
```
**Response 200:**
```json
{
  "id": "uuid",
  "full_name": "string",
  "email": "string",
  "role": "string",
  "registration_id": "string | null",
  "class_id": "uuid | null",
  "class_name": "string | null",
  "status": "string"
}
```

---

### 5.3 Class Router `/classes`

#### POST `/classes`
**Auth:** Admin  
**Request:**
```json
{
  "class_name": "string",
  "description": "string | null",
  "academic_year": "string | null"
}
```
**Backend side effects:**
1. INSERT INTO classes (admin_id from JWT)
2. INSERT INTO class_analytics (class_id, all zeros)

**Response 201:**
```json
{
  "id": "uuid",
  "class_name": "string",
  "description": "string | null",
  "academic_year": "string | null",
  "status": "ACTIVE",
  "created_at": "timestamp"
}
```

---

#### GET `/classes`
**Auth:** Admin  
**Backend query:**
```sql
SELECT c.id, c.class_name, c.description, c.academic_year, c.status,
       COUNT(DISTINCT CASE WHEN cm.member_role='STUDENT' AND cm.status='ACTIVE' THEN cm.user_id END) as student_count,
       COUNT(DISTINCT CASE WHEN cm.member_role='MENTOR' AND cm.status='ACTIVE' THEN cm.user_id END) as mentor_count
FROM classes c
LEFT JOIN class_memberships cm ON cm.class_id = c.id
WHERE c.admin_id = :admin_id
GROUP BY c.id
ORDER BY c.created_at DESC
```
**Response 200:**
```json
{
  "classes": [
    {
      "id": "uuid",
      "class_name": "string",
      "description": "string | null",
      "academic_year": "string | null",
      "status": "ACTIVE | ARCHIVED",
      "student_count": 0,
      "mentor_count": 0,
      "created_at": "timestamp"
    }
  ]
}
```

---

#### GET `/classes/my-classes`
**Auth:** Mentor  
**Backend query:**
```sql
SELECT c.id, c.class_name, c.status, cm.is_primary_mentor
FROM classes c
JOIN class_memberships cm ON cm.class_id = c.id
WHERE cm.user_id = :user_id AND cm.member_role = 'MENTOR' AND cm.status = 'ACTIVE'
```
**Response 200:**
```json
{
  "classes": [
    {
      "id": "uuid",
      "class_name": "string",
      "status": "string",
      "is_primary_mentor": true
    }
  ]
}
```

---

#### GET `/classes/{class_id}`
**Auth:** Admin (own) or Mentor (own)  
**Backend query:**
```sql
SELECT c.*,
  primary_mentor.id as pm_id, primary_mentor.full_name as pm_name, primary_mentor.email as pm_email,
  COALESCE(
    json_agg(CASE WHEN cm_co.is_primary_mentor = false 
      THEN json_build_object('id', co.id, 'full_name', co.full_name, 'email', co.email) 
      END) FILTER (WHERE cm_co.is_primary_mentor = false), '[]'
  ) as co_mentors,
  COUNT(DISTINCT CASE WHEN cm_s.member_role='STUDENT' THEN cm_s.user_id END) as student_count,
  COUNT(DISTINCT a.id) as assignment_count
FROM classes c
LEFT JOIN class_memberships cm_pm ON cm_pm.class_id = c.id AND cm_pm.is_primary_mentor = true AND cm_pm.status = 'ACTIVE'
LEFT JOIN users primary_mentor ON primary_mentor.id = cm_pm.user_id
LEFT JOIN class_memberships cm_co ON cm_co.class_id = c.id AND cm_co.member_role = 'MENTOR' AND cm_co.status = 'ACTIVE'
LEFT JOIN users co ON co.id = cm_co.user_id
LEFT JOIN class_memberships cm_s ON cm_s.class_id = c.id AND cm_s.member_role = 'STUDENT'
LEFT JOIN assignments a ON a.class_id = c.id
WHERE c.id = :class_id
GROUP BY c.id, primary_mentor.id, pm_name, pm_email
```
**Response 200:**
```json
{
  "id": "uuid",
  "class_name": "string",
  "description": "string | null",
  "academic_year": "string | null",
  "status": "string",
  "primary_mentor": { "id": "uuid", "full_name": "string", "email": "string" } ,
  "co_mentors": [ { "id": "uuid", "full_name": "string", "email": "string" } ],
  "student_count": 0,
  "assignment_count": 0
}
```
**Note:** `primary_mentor` will be `null` if no mentor assigned yet.

---

#### PATCH `/classes/{class_id}`
**Auth:** Admin (own)  
**Request:** `{ "class_name": "string | null", "description": "string | null", "status": "ARCHIVED | null" }`  
**Response 200:** Same shape as GET `/classes/{class_id}`

---

#### GET `/classes/{class_id}/students`
**Auth:** Admin (own) or Mentor (own)  
**Backend query:**
```sql
SELECT u.id, u.full_name, u.email, u.registration_id, cm.status as membership_status,
       cm.joined_via, cm.created_at as joined_at,
       COALESCE(sa.risk_level, 'NORMAL') as risk_level,
       COALESCE(sa.completion_rate, 0) as completion_rate
FROM users u
JOIN class_memberships cm ON cm.user_id = u.id AND cm.class_id = :class_id AND cm.member_role = 'STUDENT'
LEFT JOIN student_analytics sa ON sa.student_id = u.id AND sa.class_id = :class_id
ORDER BY u.full_name ASC
```
**Response 200:**
```json
{
  "students": [
    {
      "id": "uuid",
      "full_name": "string",
      "email": "string",
      "registration_id": "string",
      "membership_status": "PENDING | ACTIVE | REJECTED | INACTIVE",
      "risk_level": "NORMAL | LOW | MEDIUM | HIGH | RECOVERING",
      "completion_rate": 0.0,
      "joined_via": "MANUAL | BULK_IMPORT",
      "joined_at": "timestamp"
    }
  ]
}
```

---

#### GET `/classes/{class_id}/approvals`
**Auth:** Admin (own) or Mentor (own)  
**Backend query:**
```sql
SELECT u.id, u.full_name, u.email, u.registration_id, cm.created_at as requested_at, cm.joined_via
FROM users u
JOIN class_memberships cm ON cm.user_id = u.id AND cm.class_id = :class_id AND cm.status = 'PENDING'
WHERE cm.member_role = 'STUDENT'
ORDER BY cm.created_at ASC
```
**Response 200:**
```json
{
  "pending_count": 0,
  "pending": [
    {
      "student_id": "uuid",
      "full_name": "string",
      "email": "string",
      "registration_id": "string",
      "requested_at": "timestamp",
      "joined_via": "MANUAL | BULK_IMPORT"
    }
  ]
}
```

---

#### PATCH `/classes/{class_id}/students/{student_id}/approve`
**Auth:** Admin (own) or Mentor (own)  
**Request:** `{}`  
**Backend:**
1. Verify student's class_membership is PENDING for this class
2. `UPDATE class_memberships SET status = 'ACTIVE', updated_at = now() WHERE class_id = :class_id AND user_id = :student_id`
3. `INSERT INTO student_analytics (student_id, class_id, all zeros)`  ← only here, not on account creation
4. `INSERT INTO notifications (user_id=student_id, notification_type='STUDENT_APPROVED', title='Access Granted', body='You can now log in to [class_name]', payload={class_id})`
5. Fetch student.fcm_token, if non-null → send FCM push: title="Access Granted", body="You can now access [class_name]"
6. Return 200: `{ "message": "Student approved", "student_id": "uuid" }`

---

#### PATCH `/classes/{class_id}/students/{student_id}/reject`
**Auth:** Admin (own) or Mentor (own)  
**Request:** `{ "reason": "string | null" }`  
**Backend:**
1. Verify student's class_membership is PENDING for this class
2. `UPDATE class_memberships SET status = 'REJECTED', rejection_reason = :reason, updated_at = now()`
3. `INSERT INTO notifications (notification_type='STUDENT_REJECTED', title='Access Denied', body='Your request to join [class_name] was not approved.', payload={class_id})`
4. Return 200: `{ "message": "Student rejected" }`

---

#### POST `/classes/{class_id}/co-mentors`
**Auth:** Admin (own)  
**Request:** `{ "full_name": "string", "email": "string" }`  
**Backend:**
1. Check email not in users table → 409 if exists
2. Generate temporary password: random 8-char alphanumeric
3. Generate registration_id: `"MENTOR-" + shortuuid()`
4. `INSERT INTO users (role='MENTOR', full_name, email, password_hash=bcrypt(temp_password), registration_id, status='ACTIVE')`
5. `INSERT INTO class_memberships (class_id, user_id, member_role='MENTOR', is_primary_mentor=false, joined_via='MANUAL', status='ACTIVE')`
6. Send invitation email via Brevo SMTP with credentials
7. Return 201: `{ "id": "uuid", "full_name": "string", "email": "string", "registration_id": "string", "message": "Invitation email sent" }`

---

### 5.4 Provisioning Router `/provision`

#### GET `/provision/bulk-import/template`
**Auth:** Admin  
**Response:** Binary download — Excel file (.xlsx) with 3 sheets  
**Content-Type:** `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`  
**Content-Disposition:** `attachment; filename="AssignHub_Import_Template.xlsx"`

Template is generated dynamically by `export_service.generate_import_template()` — not a static file. See Section 12 for sheet structure.

---

#### POST `/provision/bulk-import`
**Auth:** Admin  
**Content-Type:** `multipart/form-data`  
**Fields:** `file` (Excel .xlsx binary)  
**Backend:**
1. Save file temporarily
2. INSERT INTO bulk_import_batches (admin_id, file_name, status='UPLOADED')
3. Launch background task: `process_bulk_import(batch_id, file_path, admin_id)`
4. Return 202: `{ "batch_id": "uuid", "status": "UPLOADED", "message": "Processing started" }`

---

#### GET `/provision/bulk-import/{batch_id}`
**Auth:** Admin  
**Response 200:**
```json
{
  "batch_id": "uuid",
  "status": "UPLOADED | VALIDATING | PARTIAL | COMPLETED | FAILED",
  "total_rows": 0,
  "success_rows": 0,
  "failed_rows": 0,
  "errors": [
    {
      "sheet_name": "Students",
      "row_number": 4,
      "field_name": "email",
      "error_message": "Email already exists — skipped"
    }
  ]
}
```

---

#### POST `/provision/manual/mentor`
**Auth:** Admin  
**Request:**
```json
{
  "class_id": "uuid",
  "full_name": "string",
  "email": "string",
  "password": "string",
  "is_primary_mentor": false
}
```
**Backend:**
1. Verify class belongs to admin (JWT sub must be class.admin_id)
2. Check email not in users → 409 if exists
3. Generate registration_id: `"MENTOR-" + shortuuid()`
4. Hash password
5. INSERT INTO users (role='MENTOR', status='ACTIVE')
6. INSERT INTO class_memberships (status='ACTIVE', joined_via='MANUAL')
7. Send invitation email via Brevo
8. Return 201: `{ "id": "uuid", "registration_id": "string", "message": "Invitation sent" }`

---

#### POST `/provision/manual/student`
**Auth:** Admin or Mentor (own class)  
**Request:**
```json
{
  "class_id": "uuid",
  "full_name": "string",
  "email": "string",
  "password": "string",
  "registration_id": "string"
}
```
**Backend:**
1. If Mentor: verify class_id matches mentor's active class
2. Check email not in users → 409 if exists
3. Check registration_id not in users → 409 if duplicate
4. Hash password
5. INSERT INTO users (role='STUDENT', status='ACTIVE')
6. INSERT INTO class_memberships (status='PENDING', joined_via='MANUAL') ← PENDING, not ACTIVE
7. Send invitation email via Brevo
8. Return 201: `{ "id": "uuid", "message": "Student created. Awaiting approval." }`

---

### 5.5 Assignment Router `/assignments`

#### POST `/assignments`
**Auth:** Admin or Mentor  
**Request:**
```json
{
  "class_id": "uuid",
  "title": "string",
  "description": "string | null",
  "content_type": "PDF | LINK | RICH_TEXT",
  "content_url": "string | null",
  "rich_text_body": "string | null",
  "submission_type": "FILE | TEXT | BOTH",
  "deadline_at": "ISO8601 timestamp | null",
  "auto_close": true
}
```
**Validation:**
- If content_type=PDF: content_url must be non-null S3 URL
- If content_type=LINK: content_url must be non-null
- If content_type=RICH_TEXT: rich_text_body must be non-null
- If auto_close=true: deadline_at must be non-null and in the future
- Mentor: backend verifies class_id is in mentor's active memberships

**Backend:**
1. Verify class ownership (Admin or Mentor)
2. INSERT INTO assignments (status='DRAFT')
3. Return 201: `{ "id": "uuid", "title": "string", "status": "DRAFT", "deadline_at": "timestamp|null", "created_at": "timestamp" }`

---

#### GET `/assignments`
**Auth:** Admin, Mentor, Student  
**Query params:** `class_id=uuid` (required)  
**Backend:**
- ADMIN/MENTOR: return all statuses (DRAFT, PUBLISHED, CLOSED) for that class
- STUDENT: return only PUBLISHED assignments; verify student has ACTIVE membership in that class

**Response 200:**
```json
{
  "assignments": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string | null",
      "content_type": "PDF | LINK | RICH_TEXT",
      "content_url": "string | null",
      "submission_type": "FILE | TEXT | BOTH",
      "deadline_at": "timestamp | null",
      "status": "DRAFT | PUBLISHED | CLOSED",
      "created_by_name": "string",
      "created_at": "timestamp"
    }
  ]
}
```

---

#### GET `/assignments/{assignment_id}`
**Auth:** Admin, Mentor, Student  
**Backend:** Student access: verify assignment is PUBLISHED and student has ACTIVE membership  
**Response 200:**
```json
{
  "id": "uuid",
  "title": "string",
  "description": "string | null",
  "content_type": "string",
  "content_url": "string | null",
  "rich_text_body": "string | null",
  "submission_type": "string",
  "deadline_at": "timestamp | null",
  "status": "string",
  "class_id": "uuid",
  "created_by_name": "string",
  "student_submission": {
    "submitted": false,
    "submission_id": "uuid | null",
    "submitted_at": "timestamp | null",
    "is_late": false,
    "version": 0
  }
}
```
**Note:** `student_submission` key is always present but has `submitted: false` and null fields when no submission exists. Key is present for all roles but populated only when role=STUDENT.

---

#### POST `/assignments/{assignment_id}/publish`
**Auth:** Admin (own class) or Mentor (own class)  
**Request:** `{}`  
**Backend:**
1. Verify assignment.status == 'DRAFT' → 409 if already published
2. Verify caller owns the assignment's class
3. `UPDATE assignments SET status = 'PUBLISHED', updated_at = now()`
4. Count active students in class → N
5. `INSERT INTO assignment_analytics (assignment_id, total_targets=N, all other zeros)`
6. Fetch all student FCM tokens in class:
   ```sql
   SELECT u.fcm_token FROM users u
   JOIN class_memberships cm ON cm.user_id = u.id
   WHERE cm.class_id = :class_id AND cm.member_role = 'STUDENT' AND cm.status = 'ACTIVE'
   AND u.fcm_token IS NOT NULL
   ```
7. Batch FCM push: title="New Assignment", body="[title] — due [deadline or 'No deadline']"
8. Bulk INSERT INTO notifications (one row per student)
9. If deadline_at is set:
   - APScheduler: `add_job(close_assignment_job, 'date', run_date=deadline_at, args=[assignment_id])`
   - APScheduler: `add_job(send_reminder_job, 'date', run_date=deadline_at - timedelta(hours=24), args=[assignment_id, '24h'])`
   - APScheduler: `add_job(send_reminder_job, 'date', run_date=deadline_at - timedelta(hours=2), args=[assignment_id, '2h'])`
10. Return 200: `{ "status": "PUBLISHED", "message": "Assignment published and students notified" }`

---

#### POST `/assignments/{assignment_id}/close`
**Auth:** Admin (own class) or Mentor (own class)  
**Request:** `{}`  
**Backend:**
1. `UPDATE assignments SET status = 'CLOSED', updated_at = now()`
2. Call `analytics_service.recompute_all_after_close(assignment_id)` — see Section 11
3. Return 200: `{ "status": "CLOSED" }`

---

#### GET `/assignments/{assignment_id}/tracker`
**Auth:** Admin (own class) or Mentor (own class)  
**Backend query:**
```sql
-- Get all active students in class
-- For each: LEFT JOIN to submissions WHERE is_current=true
-- Derive tracker_status:
--   Has submission + is_late=false → SUBMITTED
--   Has submission + is_late=true  → LATE
--   No submission + deadline_at > now() + assignment PUBLISHED → PENDING
--   No submission + (deadline passed OR assignment CLOSED) → MISSED
SELECT
  u.id as student_id, u.full_name, u.registration_id,
  s.id as submission_id, s.submitted_at, s.is_late,
  CASE
    WHEN s.id IS NOT NULL AND s.is_late = false THEN 'SUBMITTED'
    WHEN s.id IS NOT NULL AND s.is_late = true THEN 'LATE'
    WHEN s.id IS NULL AND (a.deadline_at IS NULL OR a.deadline_at > now()) AND a.status = 'PUBLISHED' THEN 'PENDING'
    ELSE 'MISSED'
  END as tracker_status
FROM users u
JOIN class_memberships cm ON cm.user_id = u.id AND cm.class_id = a.class_id AND cm.member_role = 'STUDENT' AND cm.status = 'ACTIVE'
JOIN assignments a ON a.id = :assignment_id
LEFT JOIN submissions s ON s.student_id = u.id AND s.assignment_id = :assignment_id AND s.is_current = true
ORDER BY u.full_name ASC
```
**Response 200:**
```json
{
  "assignment_id": "uuid",
  "title": "string",
  "deadline_at": "timestamp | null",
  "status": "PUBLISHED | CLOSED",
  "submitted_count": 0,
  "pending_count": 0,
  "missed_count": 0,
  "late_count": 0,
  "students": [
    {
      "student_id": "uuid",
      "full_name": "string",
      "registration_id": "string",
      "tracker_status": "SUBMITTED | PENDING | MISSED | LATE",
      "submitted_at": "timestamp | null",
      "is_late": false,
      "submission_id": "uuid | null"
    }
  ]
}
```

---

### 5.6 Submission Router `/submissions`

#### POST `/assignments/{assignment_id}/submit`
**Auth:** Student  
**Content-Type:** `application/json`  
**Request:**
```json
{
  "submission_type": "FILE | TEXT",
  "file_url": "string | null",
  "text_answer": "string | null"
}
```
**Validation:**
- submission_type=FILE: file_url must be non-null (S3 URL from presigned upload)
- submission_type=TEXT: text_answer must be non-null
- assignment.submission_type=FILE: only FILE accepted
- assignment.submission_type=TEXT: only TEXT accepted
- assignment.submission_type=BOTH: either accepted

**Backend:**
1. Fetch assignment → verify status=PUBLISHED, verify student's class matches
2. Determine is_late:
   - If assignment.deadline_at IS NULL: is_late = false
   - If deadline_at < now(): is_late = true
   - Else: is_late = false
3. Find existing current submission:
   ```sql
   SELECT * FROM submissions WHERE assignment_id=:aid AND student_id=:sid AND is_current=true
   ```
4. If exists: `UPDATE submissions SET is_current=false WHERE id = :existing_id`
5. `INSERT INTO submissions (assignment_id, student_id, submission_type, file_url, text_answer, is_late, version=old_version+1, is_current=true, submitted_at=utcnow())`
6. Call `analytics_service.recompute_student_analytics(student_id, class_id)`
7. `UPDATE assignment_analytics SET submitted_count = (SELECT COUNT(*) FROM submissions WHERE assignment_id=:aid AND is_current=true), ...`
8. `INSERT INTO notifications (user_id=student_id, notification_type='SUBMISSION_RECEIPT', title='Submitted', body='Assignment [title] submitted at [time]')`
   ← In-app notification only. No FCM for submission receipt.
9. Broadcast WebSocket event to tracker channel for this assignment
10. Return 201:
```json
{
  "submission_id": "uuid",
  "submitted_at": "ISO8601 timestamp",
  "is_late": false,
  "version": 1,
  "receipt": "Submitted successfully at 10:45 AM on 25 Jun 2026"
}
```

---

#### GET `/assignments/{assignment_id}/submissions`
**Auth:** Admin (own class) or Mentor (own class)  
**Response 200:**
```json
{
  "submissions": [
    {
      "submission_id": "uuid",
      "student_id": "uuid",
      "student_name": "string",
      "submission_type": "FILE | TEXT",
      "file_url": "string | null",
      "text_answer": "string | null",
      "submitted_at": "timestamp",
      "is_late": false,
      "version": 1
    }
  ]
}
```
**Note:** Only returns `is_current=true` rows.

---

#### GET `/submissions/my`
**Auth:** Student  
**Backend query:**
```sql
SELECT s.id as submission_id, s.assignment_id, a.title as assignment_title,
       s.submission_type, s.submitted_at, s.is_late, s.version
FROM submissions s
JOIN assignments a ON a.id = s.assignment_id
WHERE s.student_id = :user_id AND s.is_current = true
ORDER BY s.submitted_at DESC
```
**Response 200:**
```json
{
  "submissions": [
    {
      "submission_id": "uuid",
      "assignment_id": "uuid",
      "assignment_title": "string",
      "submission_type": "FILE | TEXT",
      "submitted_at": "timestamp",
      "is_late": false,
      "version": 1
    }
  ]
}
```

---

### 5.7 Storage Router `/storage`

#### POST `/storage/presigned-upload`
**Auth:** Admin, Mentor, or Student  
**Request:**
```json
{
  "file_name": "string",
  "file_type": "application/pdf | image/jpeg | image/png | ...",
  "upload_purpose": "ASSIGNMENT | SUBMISSION"
}
```
**Backend:**
```python
import uuid, boto3
s3_key = f"{upload_purpose.lower()}s/{current_user.id}/{uuid.uuid4()}/{file_name}"
presigned_url = s3_client.generate_presigned_url(
    'put_object',
    Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key, 'ContentType': file_type},
    ExpiresIn=300
)
file_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
```
**Response 200:**
```json
{
  "upload_url": "https://s3.amazonaws.com/...?presigned_params",
  "file_url": "https://assignhub-files.s3.ap-south-1.amazonaws.com/submissions/user_id/uuid/filename.pdf",
  "expires_in": 300
}
```
**Flutter action after receiving this:**
1. HTTP PUT to `upload_url` with file bytes + `Content-Type` header
2. On S3 PUT returning 200: use `file_url` in assignment create or submission body
3. On S3 PUT failure: show error, do NOT call submit endpoint

#### POST `/storage/presigned-download`
**Auth:** Any authenticated role  
**Request:** `{ "file_url": "string" }` ← full S3 URL  
**Backend:** Generate presigned GET URL for download  
**Response 200:** `{ "download_url": "string", "expires_in": 300 }`

---

### 5.8 Analytics Router `/analytics`

#### GET `/analytics/admin/overview`
**Auth:** Admin  
**Backend query:**
```sql
SELECT
  c.id as class_id, c.class_name, c.status,
  u.full_name as primary_mentor_name,
  COALESCE(ca.avg_completion, 0) as avg_completion,
  COALESCE(ca.avg_miss_rate, 0) as avg_miss_rate,
  COALESCE(ca.avg_late_rate, 0) as avg_late_rate,
  COALESCE(ca.high_risk_count, 0) as high_risk_count,
  COALESCE(ca.total_students, 0) as student_count
FROM classes c
LEFT JOIN class_analytics ca ON ca.class_id = c.id
LEFT JOIN class_memberships cm ON cm.class_id = c.id AND cm.is_primary_mentor = true AND cm.status = 'ACTIVE'
LEFT JOIN users u ON u.id = cm.user_id
WHERE c.admin_id = :admin_id
ORDER BY c.created_at DESC
```
**Response 200:**
```json
{
  "total_classes": 0,
  "total_mentors": 0,
  "total_students": 0,
  "total_assignments": 0,
  "classes": [
    {
      "class_id": "uuid",
      "class_name": "string",
      "status": "ACTIVE | ARCHIVED",
      "primary_mentor_name": "string | null",
      "student_count": 0,
      "avg_completion": 0.0,
      "avg_miss_rate": 0.0,
      "avg_late_rate": 0.0,
      "high_risk_count": 0
    }
  ]
}
```

---

#### GET `/analytics/classes/{class_id}`
**Auth:** Admin (own) or Mentor (own)  
**Response 200:**
```json
{
  "class_id": "uuid",
  "class_name": "string",
  "total_students": 0,
  "total_assignments": 0,
  "avg_completion": 0.0,
  "avg_miss_rate": 0.0,
  "avg_late_rate": 0.0,
  "high_risk_count": 0,
  "bottleneck_assignments": [
    { "assignment_id": "uuid", "title": "string", "completion_rate": 0.0 }
  ],
  "risk_distribution": {
    "NORMAL": 0, "LOW": 0, "MEDIUM": 0, "HIGH": 0, "RECOVERING": 0
  }
}
```

---

#### GET `/analytics/classes/{class_id}/students`
**Auth:** Admin (own) or Mentor (own)  
**Response 200:**
```json
{
  "students": [
    {
      "student_id": "uuid",
      "full_name": "string",
      "registration_id": "string",
      "completion_rate": 0.0,
      "total_submitted": 0,
      "total_missed": 0,
      "total_late": 0,
      "current_streak": 0,
      "risk_level": "NORMAL | LOW | MEDIUM | HIGH | RECOVERING",
      "consecutive_misses": 0
    }
  ]
}
```

---

#### GET `/analytics/students/{student_id}`
**Auth:** Admin (own class), Mentor (own class), Student (own only)  
**Backend:** If Student role: enforce student_id == JWT sub  
**Backend query:**
```sql
-- Base analytics from student_analytics
SELECT sa.*, c.class_name,
  (SELECT COALESCE(AVG(sa2.completion_rate), 0) FROM student_analytics sa2 WHERE sa2.class_id = sa.class_id) as class_avg_completion
FROM student_analytics sa
JOIN classes c ON c.id = sa.class_id
WHERE sa.student_id = :student_id
```
Assignment history:
```sql
SELECT a.id as assignment_id, a.title, a.deadline_at,
  CASE
    WHEN s.id IS NOT NULL AND s.is_late = false THEN 'SUBMITTED'
    WHEN s.id IS NOT NULL AND s.is_late = true THEN 'LATE'
    WHEN s.id IS NULL AND a.status = 'CLOSED' THEN 'MISSED'
    ELSE 'PENDING'
  END as tracker_status,
  s.submitted_at, s.is_late
FROM assignments a
LEFT JOIN submissions s ON s.assignment_id = a.id AND s.student_id = :student_id AND s.is_current = true
WHERE a.class_id = sa.class_id
ORDER BY a.created_at DESC
```
**Response 200:**
```json
{
  "student_id": "uuid",
  "full_name": "string",
  "class_name": "string",
  "total_assigned": 0,
  "total_submitted": 0,
  "total_missed": 0,
  "total_late": 0,
  "completion_rate": 0.0,
  "current_streak": 0,
  "longest_streak": 0,
  "avg_submission_delay_hours": 0.0,
  "risk_level": "NORMAL | LOW | MEDIUM | HIGH | RECOVERING",
  "consecutive_misses": 0,
  "class_avg_completion": 0.0,
  "assignment_history": [
    {
      "assignment_id": "uuid",
      "title": "string",
      "deadline_at": "timestamp | null",
      "tracker_status": "SUBMITTED | MISSED | LATE | PENDING",
      "submitted_at": "timestamp | null",
      "is_late": false
    }
  ]
}
```

---

#### GET `/analytics/assignments/{assignment_id}`
**Auth:** Admin or Mentor (own class)  
**Response 200:**
```json
{
  "assignment_id": "uuid",
  "title": "string",
  "total_targets": 0,
  "submitted_count": 0,
  "missed_count": 0,
  "late_count": 0,
  "completion_rate": 0.0,
  "is_bottleneck": false
}
```

---

#### GET `/analytics/risk/students`
**Auth:** Admin or Mentor  
**Query params:** `class_id=uuid`  
**Backend query:**
```sql
SELECT sa.student_id, u.full_name, sa.risk_level, sa.consecutive_misses, sa.completion_rate
FROM student_analytics sa
JOIN users u ON u.id = sa.student_id
WHERE sa.class_id = :class_id AND sa.risk_level IN ('HIGH','MEDIUM')
ORDER BY sa.risk_level DESC, sa.consecutive_misses DESC
```
**Response 200:**
```json
{
  "at_risk_students": [
    {
      "student_id": "uuid",
      "full_name": "string",
      "risk_level": "HIGH | MEDIUM",
      "consecutive_misses": 0,
      "completion_rate": 0.0
    }
  ]
}
```

---

### 5.9 Notification Router `/notifications`

#### GET `/notifications`
**Auth:** Any role  
**Backend:** Filter by user_id from JWT  
**Response 200:**
```json
{
  "notifications": [
    {
      "id": "uuid",
      "notification_type": "string",
      "title": "string",
      "body": "string",
      "payload": { "assignment_id": "uuid | null", "class_id": "uuid | null" },
      "is_read": false,
      "created_at": "timestamp"
    }
  ],
  "unread_count": 0
}
```

---

#### PATCH `/notifications/{notification_id}/read`
**Auth:** Any role  
**Backend:** Verify notification.user_id == JWT sub → 403 otherwise  
**Response 200:** `{ "is_read": true }`

---

#### PATCH `/notifications/read-all`
**Auth:** Any role  
**Backend:** `UPDATE notifications SET is_read=true WHERE user_id=:user_id`  
**Response 200:** `{ "message": "All notifications marked as read" }`

---

#### POST `/notifications/reminder`
**Auth:** Student  
**Request:** `{ "assignment_id": "uuid", "remind_at": "ISO8601 timestamp" }`  
**Backend:**
1. Verify assignment is PUBLISHED and student belongs to class
2. Verify remind_at is in the future
3. `INSERT INTO reminder_jobs (user_id, assignment_id, remind_at, status='SCHEDULED')`
4. APScheduler: `add_job(send_student_reminder_job, 'date', run_date=remind_at, args=[reminder_job_id])`
5. Return 201: `{ "reminder_id": "uuid", "remind_at": "timestamp" }`

---

### 5.10 Export Router `/exports`

#### POST `/exports/assignment-tracker`
**Auth:** Admin (own class) or Mentor (own class)  
**Request:** `{ "assignment_id": "uuid" }`  
**Backend:**
1. Verify assignment.status == 'CLOSED' → 409 if not closed
2. Verify caller owns assignment's class
3. `INSERT INTO export_jobs (requested_by, assignment_id, export_type='ASSIGNMENT_TRACKER', status='PENDING')`
4. Launch background task: `generate_export(export_job_id)`
5. Return 202: `{ "export_job_id": "uuid", "status": "PENDING" }`

---

#### GET `/exports/{export_job_id}`
**Auth:** Admin or Mentor (must be original requester)  
**Response 200:**
```json
{
  "export_job_id": "uuid",
  "status": "PENDING | DONE | FAILED",
  "file_url": "string | null"
}
```
**Note:** `file_url` is null until status=DONE. Flutter polls this every 3 seconds while status=PENDING.

---

### 5.11 AI Query Router `/ai`

#### POST `/ai/query`
**Auth:** Admin or Mentor  
**Request:**
```json
{
  "class_id": "uuid | null",
  "query_text": "string"
}
```
**Response 200:**
```json
{
  "intent": "string",
  "query_text": "string",
  "result": {
    "type": "student_list | class_summary | student_profile | risk_list | count | no_data",
    "data": [ ],
    "message": "string"
  },
  "action_links": [
    { "label": "View profile", "route": "/analytics/students/uuid" }
  ]
}
```
See Section 13 for full AI flow.

---

### 5.12 WebSocket `/ws`

#### WSS `/ws/tracker/{assignment_id}`
**Auth:** JWT passed as query param: `?token=<access_token>`  
**Backend:** Validate token on connect. Verify caller is ADMIN or MENTOR with class access.  
See Section 7 for full WebSocket design.

---

## 6. Feature Data Flows

### 6.1 Admin Creates Class Manually
```
1. Flutter Admin → Create Class screen (class_name, description, academic_year)
2. POST /classes
3. Backend:
   a. INSERT INTO classes (admin_id from JWT)
   b. INSERT INTO class_analytics (class_id, all zeros)
4. Flutter: add class card to class list (using returned object — not refetch)
5. Flutter: Navigate to Class Detail screen
```

### 6.2 Admin Uploads Bulk Excel
```
1. Flutter Admin → Bulk Import screen
2. GET /provision/bulk-import/template → download Excel file
3. Admin fills template offline
4. Flutter: file picker → POST /provision/bulk-import (multipart)
5. Backend: return batch_id immediately (202)
6. Flutter: poll GET /provision/bulk-import/{batch_id} every 3s
7. Backend (background):
   a. Parse Sheet 1 (Classes): INSERT classes + class_analytics
   b. Parse Sheet 2 (Mentors): INSERT users(ACTIVE) + class_memberships(ACTIVE) + email queue
   c. Parse Sheet 3 (Students): INSERT users(ACTIVE) + class_memberships(PENDING) + email queue
   d. Send all queued Brevo emails
   e. UPDATE bulk_import_batches status
8. Flutter: when status = COMPLETED/PARTIAL → show results + error list
```

### 6.3 Student Receives Invitation and Logs In
```
1. Student receives Brevo email: email, password, registration_id
2. Student opens Flutter app → Login screen
3. Enters email + password + registration_id
4. POST /auth/login
5. Backend:
   a. Verify credentials
   b. Check class_memberships.status = 'ACTIVE' (must be approved first)
   c. If PENDING: return 403 "Account pending approval"
6. If 403: Flutter shows "Your account is pending approval by your mentor. Please wait."
7. After approval (see flow 6.4), student retries login → success
8. Flutter stores tokens → routes to Student Dashboard
```

### 6.4 Mentor Approves Student
```
1. Flutter Mentor → Approvals screen
2. GET /classes/{class_id}/approvals
3. Mentor sees pending student cards with Approve / Reject buttons
4. Mentor taps "Approve"
5. PATCH /classes/{class_id}/students/{student_id}/approve
6. Backend:
   a. UPDATE class_memberships SET status = 'ACTIVE'
   b. INSERT INTO student_analytics (student_id, class_id, all zeros)
   c. INSERT INTO notifications (STUDENT_APPROVED)
   d. FCM push to student: "Access Granted"
7. Flutter: remove student card from pending list (optimistic update)
8. Student's next login attempt succeeds
```

### 6.5 Mentor Creates and Publishes Assignment
```
1. Flutter Mentor → Create Assignment screen
2. If PDF content:
   a. Flutter: file picker → POST /storage/presigned-upload (purpose=ASSIGNMENT)
   b. Backend: return upload_url + file_url
   c. Flutter: HTTP PUT to upload_url with file bytes
   d. On S3 200: store file_url in form state
3. POST /assignments (with all fields including file_url if applicable)
4. Backend: INSERT assignments (status=DRAFT) → return assignment_id
5. Flutter: Navigate to assignment detail, show "Publish" button
6. POST /assignments/{assignment_id}/publish
7. Backend:
   a. UPDATE assignments status=PUBLISHED
   b. INSERT assignment_analytics (total_targets = active student count)
   c. FCM batch push to all students
   d. INSERT notifications for each student
   e. If deadline_at: register APScheduler jobs (close, 24h reminder, 2h reminder)
8. Flutter: show "Published" badge, navigate to tracker screen
```

### 6.6 Student Submits Assignment
```
1. Flutter Student → Assignment Detail screen
2. If FILE submission:
   a. POST /storage/presigned-upload (purpose=SUBMISSION)
   b. HTTP PUT to upload_url with file bytes
   c. On S3 200: store file_url
3. POST /assignments/{assignment_id}/submit
   body: { submission_type, file_url | text_answer }
4. Backend:
   a. Check is_late
   b. Invalidate previous submission (is_current=false) if exists
   c. INSERT new submission (version++)
   d. recompute_student_analytics()
   e. UPDATE assignment_analytics submitted_count
   f. INSERT SUBMISSION_RECEIPT notification (in-app only, no FCM)
   g. Broadcast WebSocket event to tracker channel
5. Flutter: show receipt card with timestamp + is_late badge if applicable
6. Tracker screen (if mentor is viewing): WebSocket event updates student row in real time
```

### 6.7 Deadline Auto-Close (APScheduler)
```
At deadline_at, APScheduler fires close_assignment_job(assignment_id):
  1. UPDATE assignments SET status = 'CLOSED'
  2. Call analytics_service.recompute_all_after_close(assignment_id):
     a. For every active student in class:
        - recompute_student_analytics(student_id, class_id)
     b. recompute_assignment_analytics(assignment_id)
     c. recompute_class_analytics(class_id)
  3. Fetch non-submitters (students in class with no is_current=true submission)
  4. FCM push to non-submitters: "Missed Deadline — [title]"
  5. INSERT MISSED_DEADLINE notifications for non-submitters
  6. Broadcast WebSocket tracker_refresh event
```

---

## 7. WebSocket Design

### 7.1 Connection Protocol

Flutter opens WebSocket when mentor or admin navigates to Assignment Tracker screen:
```
WSS https://assignhub-api.onrender.com/api/v1/ws/tracker/{assignment_id}?token=<access_token>
```

Backend on connect:
1. Extract token from query param
2. Decode JWT → verify signature and expiry
3. Verify caller is ADMIN or MENTOR with active membership in assignment's class
4. Add connection to in-memory channel map: `channels[assignment_id].add(websocket)`
5. Send initial ping: `{ "event": "connected", "assignment_id": "uuid" }`

On disconnect: remove from channel map.

### 7.2 Server → Client Events

**`submission_created`** — sent when a student submits:
```json
{
  "event": "submission_created",
  "assignment_id": "uuid",
  "submitted_count": 18,
  "pending_count": 5,
  "missed_count": 2,
  "late_count": 1,
  "student": {
    "student_id": "uuid",
    "full_name": "string",
    "tracker_status": "SUBMITTED | LATE",
    "submitted_at": "ISO8601 timestamp",
    "is_late": false
  }
}
```

**`tracker_refresh`** — sent after assignment close:
```json
{
  "event": "tracker_refresh",
  "assignment_id": "uuid",
  "status": "CLOSED",
  "submitted_count": 18,
  "pending_count": 0,
  "missed_count": 7,
  "late_count": 1
}
```

### 7.3 Flutter WebSocket Behavior

```dart
// ws_client.dart
onOpen:
  - Load initial tracker data: GET /assignments/{id}/tracker (REST call)
  - Render full student list from REST response
  
onMessage (submission_created):
  - Find student row in list by student_id
  - Update tracker_status, submitted_at, is_late
  - Update summary count badges
  - No REST refetch needed

onMessage (tracker_refresh):
  - Update summary counts from payload
  - Refetch full student list: GET /assignments/{id}/tracker
  - Show "Assignment closed" banner

onClose:
  - Show "Live updates paused" banner with "Reconnect" button
  
onError:
  - Retry connection with exponential backoff: 2s, 4s, 8s (max 3 attempts)
  - After 3 failures: show "Could not connect for live updates" message
  - Tracker still works via manual refresh button (REST call)
```

### 7.4 Backend WebSocket Manager

```python
# websocket/tracker_ws.py
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, assignment_id: str, websocket: WebSocket):
        await websocket.accept()
        if assignment_id not in self.active_connections:
            self.active_connections[assignment_id] = []
        self.active_connections[assignment_id].append(websocket)
    
    def disconnect(self, assignment_id: str, websocket: WebSocket):
        if assignment_id in self.active_connections:
            self.active_connections[assignment_id].remove(websocket)
    
    async def broadcast(self, assignment_id: str, message: dict):
        if assignment_id in self.active_connections:
            dead = []
            for ws in self.active_connections[assignment_id]:
                try:
                    await ws.send_json(message)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.active_connections[assignment_id].remove(ws)

manager = ConnectionManager()
```

---

## 8. S3 File Upload Flow

### 8.1 Why Presigned URL (not multipart through FastAPI)
- File bytes never pass through FastAPI — no memory pressure on Render free tier
- S3 enforces ContentType and file size directly
- Presigned URL expires in 5 minutes — limits abuse window
- Flutter handles progress bar natively via HTTP PUT byte stream

### 8.2 Complete Flow

```
Flutter side:
  1. User selects file (file_picker package)
  2. POST /storage/presigned-upload
     body: { file_name, file_type, upload_purpose }
  3. Receive: { upload_url, file_url, expires_in: 300 }
  4. HTTP PUT upload_url
     headers: { 'Content-Type': file_type }
     body: file bytes
  5. If PUT returns 200: proceed with file_url
  6. If PUT returns non-200: show "Upload failed, try again" — DO NOT call submit

Backend presigned URL generation:
  s3_key = f"{upload_purpose.lower()}s/{user_id}/{uuid4()}/{sanitize(file_name)}"
  upload_url = s3.generate_presigned_url(
      'put_object',
      Params={'Bucket': BUCKET, 'Key': s3_key, 'ContentType': file_type},
      ExpiresIn=300
  )
  file_url = f"https://{BUCKET}.s3.{REGION}.amazonaws.com/{s3_key}"

S3 bucket policy: all objects PRIVATE.
For download: call POST /storage/presigned-download with file_url → get temporary GET URL.
Never expose permanent public S3 URLs.
```

---

## 9. Notification & Email Flow

### 9.1 Invitation Email via Brevo SMTP

Triggered by: bulk import (for both mentor and student), manual provision, co-mentor add.

```python
# email_service.py — send_invitation_email()
smtp_host = BREVO_SMTP_HOST       # smtp-relay.brevo.com
smtp_port = BREVO_SMTP_PORT       # 587
smtp_user = BREVO_SMTP_USER
smtp_key  = BREVO_SMTP_KEY

Subject: "Welcome to AssignHub — Your Login Details"

Body:
  Hello [full_name],

  You have been added to [class_name] on AssignHub.

  Your login credentials:
    Email: [email]
    Password: [plain_text_password]   ← sent only in this email
    Registration ID: [registration_id]

  Log in at: [app download link or "using the AssignHub app"]

  Keep these credentials safe.
```

**Security note:** Plain-text password is sent only once in this invitation email. Backend stores only the bcrypt hash. If lost, admin must manually reset (out of scope for hackathon — note in README).

### 9.2 Admin OTP Email via Gmail SMTP

```python
# email_service.py — send_otp_email()
smtp_host = "smtp.gmail.com"
smtp_port = 587
smtp_user = GMAIL_ADDRESS
smtp_password = GMAIL_APP_PASSWORD

Subject: "Your AssignHub OTP"

Body:
  Your OTP to verify your AssignHub admin account: [6-digit OTP]
  This OTP is valid for 10 minutes.
  Do not share this OTP with anyone.
```

### 9.3 FCM Push Notifications

| Event | Trigger point | Recipients | title | body |
|---|---|---|---|---|
| Assignment published | POST /assignments/{id}/publish | All ACTIVE students in class | "New Assignment" | "[title] — due [deadline or 'No deadline']" |
| Deadline 24h reminder | APScheduler job | PENDING (non-submitting) students | "Reminder" | "[title] due tomorrow" |
| Deadline 2h reminder | APScheduler job | PENDING students | "Final Reminder" | "[title] due in 2 hours" |
| Missed deadline | APScheduler close job | Non-submitting students | "Missed Deadline" | "You missed [title]" |
| Student approved | PATCH .../approve | Approved student | "Access Granted" | "You can now log in to [class_name]" |
| Risk alert | recompute_student_analytics (when risk changes to HIGH) | Student | "Action Needed" | "You've missed 3+ assignments. Contact your mentor." |
| Co-mentor added | POST /classes/{id}/co-mentors | New co-mentor | "Class Access Granted" | "You now have access to [class_name]" |

**FCM batch send** (for class-wide notifications):
```python
# fcm_service.py
from firebase_admin import messaging

def send_batch_fcm(tokens: list[str], title: str, body: str, data: dict = {}):
    messages = [
        messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data,
            token=token
        )
        for token in tokens if token
    ]
    if messages:
        response = messaging.send_each(messages)
        # Handle failed tokens: set fcm_token=NULL for unregistered tokens
```

### 9.4 In-App Notification Only (no FCM)
- SUBMISSION_RECEIPT — student submitted an assignment

---

## 10. Analytics Layer

### 10.1 Student Dashboard — Full Specification

**Screen:** `student_dashboard_screen.dart`  
**API called on load:** `GET /analytics/students/{student_id}` (student_id from JWT sub)  
**No mock data. Every value rendered from API response.**

| Widget | Field | Type | Tap behavior |
|---|---|---|---|
| Completion ring | `completion_rate` | NUMERIC → double | Opens assignment_history list filtered to all |
| Submitted count card | `total_submitted` | INT | Opens filtered list: tracker_status=SUBMITTED, shows title + submitted_at |
| Missed count card | `total_missed` | INT | Opens filtered list: tracker_status=MISSED, shows title + deadline_at |
| Late count card | `total_late` | INT | Opens filtered list: tracker_status=LATE, shows title + submitted_at |
| Streak badge | `current_streak` | INT | No tap — shows "X assignments on streak" |
| Longest streak | `longest_streak` | INT | No tap |
| Risk badge | `risk_level` | String | Shows bottom sheet with explanation: what risk means + advice |
| Class average line | `class_avg_completion` | NUMERIC → double | No tap |
| Assignment history list | `assignment_history[]` | Array | Each row tappable → opens Assignment Detail screen |

**Assignment history row color coding:**
- SUBMITTED: green
- LATE: orange
- MISSED: red
- PENDING: grey

**Empty state:** If `total_assigned == 0`, show "No assignments yet in your class."

---

### 10.2 Mentor Dashboard — Full Specification

**Screen:** `mentor_dashboard_screen.dart`  
**APIs called on load (parallel):**
- `GET /analytics/classes/{class_id}` — class summary
- `GET /analytics/classes/{class_id}/students` — student list with risk badges
- `GET /analytics/risk/students?class_id={class_id}` — risk list

| Widget | Field/Source | Tap behavior |
|---|---|---|
| Completion rate card | `avg_completion` from class analytics | No tap |
| Miss rate card | `avg_miss_rate` | Tap → student list filtered to has_misses |
| Late rate card | `avg_late_rate` | Tap → student list filtered to has_lates |
| Total students | `total_students` | Tap → full student list |
| At-risk count | `high_risk_count` | Tap → risk list screen |
| Risk distribution donut chart | `risk_distribution` object | No tap — render 5-segment donut |
| Bottleneck assignments list | `bottleneck_assignments[]` | Tap row → Assignment Tracker screen |
| Student list | from `GET /analytics/classes/{id}/students` | Tap row → Student Profile screen |

**Student row in list shows:**
- `full_name`
- `registration_id`
- `risk_level` → RiskBadge widget (color coded)
- `completion_rate` → horizontal progress bar
- `total_submitted` / `total_assigned` → "5/8"

**Empty state:** If `total_students == 0`, show "No approved students in this class yet."

---

### 10.3 Admin Dashboard — Full Specification

**Screen:** `admin_dashboard_screen.dart`  
**API called on load:** `GET /analytics/admin/overview`

**Top row summary tiles:**
- Total classes (from `total_classes`)
- Total mentors (from `total_mentors`)
- Total students (from `total_students`)
- Total assignments (from `total_assignments`)

**Class cards list:** One card per class in `classes[]`  
Each card shows:
- `class_name`
- `primary_mentor_name` (null → "No mentor assigned")
- `avg_completion` %
- `high_risk_count` students at risk
- `student_count`

Tap card → navigate to `class_analytics_drill_screen.dart`  
On drill: call `GET /analytics/classes/{class_id}` — renders same view as Mentor Dashboard but read-only.  
Further tap on student row → `GET /analytics/students/{student_id}` → Student Profile.

**Empty state:** If no classes: show "Create your first class to get started" with CTA button.

---

## 11. Risk Engine Logic

### 11.1 Trigger Points
- After every successful `POST /assignments/{id}/submit`
- After every assignment close (manual or APScheduler)
- After every student approval (initialises row with zeros)

### 11.2 `recompute_student_analytics(student_id, class_id, db)`

```python
# analytics_service.py

def recompute_student_analytics(student_id: UUID, class_id: UUID, db: Session):
    # Step 1: Fetch all CLOSED assignments for this class
    closed_assignments = db.query(Assignment).filter(
        Assignment.class_id == class_id,
        Assignment.status == 'CLOSED'
    ).order_by(Assignment.deadline_at.asc()).all()
    
    total_assigned = len(closed_assignments)
    
    if total_assigned == 0:
        # No closed assignments yet — write zeros
        upsert_student_analytics(student_id, class_id, db, all_zeros=True)
        return
    
    # Step 2: Fetch all current submissions by this student for these assignments
    assignment_ids = [a.id for a in closed_assignments]
    submissions = db.query(Submission).filter(
        Submission.student_id == student_id,
        Submission.assignment_id.in_(assignment_ids),
        Submission.is_current == True
    ).all()
    
    submitted_ids = {s.assignment_id: s for s in submissions}
    
    # Step 3: Compute counts
    total_submitted = len(submitted_ids)
    total_missed    = total_assigned - total_submitted
    total_late      = sum(1 for s in submissions if s.is_late)
    completion_rate = round((total_submitted / total_assigned) * 100, 2) if total_assigned > 0 else 0.0
    
    # Step 4: Streak calculation (iterate assignments newest-first)
    sorted_assignments = sorted(closed_assignments, key=lambda a: a.deadline_at or datetime.min, reverse=True)
    
    current_streak = 0
    for a in sorted_assignments:
        if a.id in submitted_ids:
            current_streak += 1
        else:
            break
    
    longest_streak = 0
    current_run = 0
    for a in sorted(closed_assignments, key=lambda a: a.deadline_at or datetime.min):
        if a.id in submitted_ids:
            current_run += 1
            longest_streak = max(longest_streak, current_run)
        else:
            current_run = 0
    
    # Step 5: Consecutive misses (from most recent backwards)
    consecutive_misses = 0
    for a in sorted_assignments:
        if a.id not in submitted_ids:
            consecutive_misses += 1
        else:
            break
    
    # Step 6: Average submission delay in hours
    delays = []
    for a in closed_assignments:
        if a.id in submitted_ids and a.deadline_at:
            s = submitted_ids[a.id]
            delay_hours = (a.deadline_at - s.submitted_at).total_seconds() / 3600
            delays.append(delay_hours)
    avg_delay = round(sum(delays) / len(delays), 2) if delays else None
    
    # Step 7: Risk level computation
    # Fetch current risk to check for RECOVERING transition
    existing = db.query(StudentAnalytics).filter_by(student_id=student_id, class_id=class_id).first()
    prev_risk = existing.risk_level if existing else 'NORMAL'
    
    if consecutive_misses >= 3:
        risk_level = 'HIGH'
    elif completion_rate < 40:
        risk_level = 'MEDIUM'
    elif completion_rate < 60:
        risk_level = 'LOW'
    elif prev_risk == 'HIGH' and completion_rate >= 60:
        risk_level = 'RECOVERING'
    else:
        risk_level = 'NORMAL'
    
    # Step 8: UPSERT student_analytics
    # Step 9: If risk changed to HIGH, send RISK_ALERT FCM + in-app notification
    if risk_level == 'HIGH' and prev_risk != 'HIGH':
        send_risk_alert(student_id, db)
```

### 11.3 `recompute_assignment_analytics(assignment_id, db)`

```python
def recompute_assignment_analytics(assignment_id: UUID, db: Session):
    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    
    # Count active students in class at time of close
    total_targets = db.query(ClassMembership).filter(
        ClassMembership.class_id == assignment.class_id,
        ClassMembership.member_role == 'STUDENT',
        ClassMembership.status == 'ACTIVE'
    ).count()
    
    submitted_count = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.is_current == True
    ).count()
    
    late_count = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.is_current == True,
        Submission.is_late == True
    ).count()
    
    missed_count = total_targets - submitted_count
    completion_rate = round((submitted_count / total_targets) * 100, 2) if total_targets > 0 else 0.0
    is_bottleneck = completion_rate < 50
    
    # UPSERT assignment_analytics
```

### 11.4 `recompute_class_analytics(class_id, db)`

```python
def recompute_class_analytics(class_id: UUID, db: Session):
    student_analytics_rows = db.query(StudentAnalytics).filter_by(class_id=class_id).all()
    
    if not student_analytics_rows:
        return
    
    avg_completion = round(sum(s.completion_rate for s in student_analytics_rows) / len(student_analytics_rows), 2)
    
    total_assigned_sum = sum(s.total_assigned for s in student_analytics_rows)
    avg_miss_rate = round(
        (sum(s.total_missed for s in student_analytics_rows) / total_assigned_sum * 100), 2
    ) if total_assigned_sum > 0 else 0.0
    
    avg_late_rate = round(
        (sum(s.total_late for s in student_analytics_rows) / total_assigned_sum * 100), 2
    ) if total_assigned_sum > 0 else 0.0
    
    high_risk_count = sum(1 for s in student_analytics_rows if s.risk_level in ('HIGH','MEDIUM'))
    
    # UPSERT class_analytics
```

### 11.5 `recompute_all_after_close(assignment_id, db)` — Called by close endpoint and APScheduler

```python
def recompute_all_after_close(assignment_id: UUID, db: Session):
    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    class_id = assignment.class_id
    
    active_students = db.query(ClassMembership).filter(
        ClassMembership.class_id == class_id,
        ClassMembership.member_role == 'STUDENT',
        ClassMembership.status == 'ACTIVE'
    ).all()
    
    for membership in active_students:
        recompute_student_analytics(membership.user_id, class_id, db)
    
    recompute_assignment_analytics(assignment_id, db)
    recompute_class_analytics(class_id, db)
```

---

## 12. Bulk Import Architecture

### 12.1 Excel Template Structure

**Sheet 1: Classes**
| Column | Type | Required | Notes |
|---|---|---|---|
| class_name | String | Yes | Max 150 chars |
| description | String | No | Can be blank |
| academic_year | String | No | e.g. "2026" |

**Sheet 2: Mentors**
| Column | Type | Required | Notes |
|---|---|---|---|
| class_name | String | Yes | Must match a row in Sheet 1 OR an existing class in DB |
| mentor_name | String | Yes | Max 120 chars |
| mentor_email | String | Yes | Must be valid email format |
| mentor_password | String | Yes | Min 8 chars |
| is_primary_mentor | Boolean | Yes | TRUE or FALSE |

**Sheet 3: Students**
| Column | Type | Required | Notes |
|---|---|---|---|
| class_name | String | Yes | Must match Sheet 1 or existing DB class |
| student_name | String | Yes | Max 120 chars |
| student_email | String | Yes | Must be valid email |
| student_password | String | Yes | Min 8 chars |
| registration_id | String | Yes | Unique across all users. Institution roll number. |
| roll_no | String | No | Display only, not stored separately |

### 12.2 Import Processing Logic

```python
# Background task in provisioning router

async def process_bulk_import(batch_id: UUID, file_path: str, admin_id: UUID, db: Session):
    UPDATE bulk_import_batches SET status='VALIDATING'
    
    wb = openpyxl.load_workbook(file_path)
    
    # ── SHEET 1: CLASSES ──
    class_name_to_id = {}  # maps class_name → uuid (for this batch + existing)
    
    # Pre-load existing classes for this admin
    existing_classes = db.query(Class).filter_by(admin_id=admin_id).all()
    for c in existing_classes:
        class_name_to_id[c.class_name] = c.id
    
    for row_idx, row in enumerate(wb['Classes'].iter_rows(min_row=2, values_only=True), start=2):
        class_name, description, academic_year = row[0], row[1], row[2]
        if not class_name:
            continue
        if class_name in class_name_to_id:
            # Already exists (from this batch or DB): skip, use existing ID
            continue
        new_class = Class(admin_id=admin_id, class_name=class_name, description=description, academic_year=academic_year)
        db.add(new_class)
        db.flush()  # get the ID
        db.add(ClassAnalytics(class_id=new_class.id))  # initialise analytics
        class_name_to_id[class_name] = new_class.id
    
    # ── SHEET 2: MENTORS ──
    for row_idx, row in enumerate(wb['Mentors'].iter_rows(min_row=2, values_only=True), start=2):
        class_name, mentor_name, mentor_email, mentor_password, is_primary = row
        
        if not class_name or not mentor_email:
            log_error(batch_id, 'Mentors', row_idx, 'class_name or mentor_email', 'Required field missing')
            continue
        
        if class_name not in class_name_to_id:
            log_error(batch_id, 'Mentors', row_idx, 'class_name', f'Class "{class_name}" not found in Sheet 1 or DB')
            continue
        
        existing = db.query(User).filter_by(email=mentor_email).first()
        if existing:
            log_error(batch_id, 'Mentors', row_idx, 'mentor_email', f'Email {mentor_email} already exists — skipped')
            continue
        
        reg_id = f"MENTOR-{shortuuid.uuid()[:8].upper()}"
        new_user = User(role='MENTOR', full_name=mentor_name, email=mentor_email,
                        password_hash=bcrypt.hash(mentor_password),
                        registration_id=reg_id, status='ACTIVE')
        db.add(new_user)
        db.flush()
        
        db.add(ClassMembership(
            class_id=class_name_to_id[class_name], user_id=new_user.id,
            member_role='MENTOR', is_primary_mentor=bool(is_primary),
            joined_via='BULK_IMPORT', status='ACTIVE'
        ))
        
        queue_invitation_email(new_user.full_name, mentor_email, mentor_password, reg_id, class_name)
        success_count += 1
    
    # ── SHEET 3: STUDENTS ──
    for row_idx, row in enumerate(wb['Students'].iter_rows(min_row=2, values_only=True), start=2):
        class_name, student_name, student_email, student_password, registration_id, roll_no = row
        
        if not class_name or not student_email or not registration_id:
            log_error(batch_id, 'Students', row_idx, None, 'Required field missing')
            continue
        
        if class_name not in class_name_to_id:
            log_error(batch_id, 'Students', row_idx, 'class_name', f'Class not found')
            continue
        
        if db.query(User).filter_by(email=student_email).first():
            log_error(batch_id, 'Students', row_idx, 'student_email', f'Email already exists — skipped')
            continue
        
        if db.query(User).filter_by(registration_id=str(registration_id)).first():
            log_error(batch_id, 'Students', row_idx, 'registration_id', f'Registration ID already exists — skipped')
            continue
        
        new_user = User(role='STUDENT', full_name=student_name, email=student_email,
                        password_hash=bcrypt.hash(student_password),
                        registration_id=str(registration_id), status='ACTIVE')
        db.add(new_user)
        db.flush()
        
        # Status = PENDING: student must be approved before login works
        db.add(ClassMembership(
            class_id=class_name_to_id[class_name], user_id=new_user.id,
            member_role='STUDENT', is_primary_mentor=False,
            joined_via='BULK_IMPORT', status='PENDING'   # ← PENDING, not ACTIVE
        ))
        
        queue_invitation_email(new_user.full_name, student_email, student_password, str(registration_id), class_name)
        success_count += 1
    
    db.commit()
    send_all_queued_emails()
    UPDATE bulk_import_batches SET status='COMPLETED' or 'PARTIAL', success_rows, failed_rows
```

### 12.3 Re-upload Behaviour
- New upload creates a new `bulk_import_batches` row
- Existing classes (same class_name for same admin) are reused by class_name match — not overwritten
- Duplicate emails/registration_ids are skipped and logged as warnings
- New classes from new upload are added as additional classes, not replacing existing ones

---

## 13. AI Query Assistant

### 13.1 Security Contract
- Only `query_text` (raw string, no DB data) is sent to the LLM API
- All data fetching happens on the backend against PostgreSQL
- Student PII (names, emails, grades) never leaves the backend
- LLM's only job: extract intent + parameters from a natural language string

### 13.2 Supported Intents

| Intent key | Example queries | Extracted params |
|---|---|---|
| `who_missed_assignment` | "Who hasn't submitted Assignment 2?" / "Non-submitters for the Python quiz" | `assignment_ref` (title substring or number) |
| `student_completion_rate` | "What is Ravi's completion rate?" / "Show Priya's progress" | `student_name` |
| `class_summary` | "How is the class doing?" / "Give me a summary" | none (uses JWT class_id) |
| `risk_students` | "Who are the at-risk students?" / "Show me students in danger" | none |
| `student_profile` | "Show Arjun's full profile" / "Full details for Meera" | `student_name` |
| `general_count` | "How many classes do I have?" / "How many students are there?" | none |

Catch-all for unrecognised intent:
```json
{
  "type": "no_data",
  "message": "I can answer questions about submissions, completion rates, at-risk students, and class summaries. Try: 'Who missed Assignment 1?' or 'What is Ravi's completion rate?'"
}
```

### 13.3 Flow

```python
# ai_service.py

async def process_ai_query(class_id: UUID | None, query_text: str, user_id: UUID, db: Session) -> dict:
    
    # Step 1: Extract intent from LLM (only query_text goes to LLM)
    llm_response = await call_llm_api(
        system_prompt="""You are an intent extractor for an educational admin tool.
Extract intent and params from the user query. Return only valid JSON, no explanation.
Format: {"intent": "string", "params": {"student_name": "string or null", "assignment_ref": "string or null"}}
Valid intents: who_missed_assignment, student_completion_rate, class_summary, 
               risk_students, student_profile, general_count, unknown""",
        user_message=query_text
    )
    
    parsed = json.loads(llm_response)  # strip any markdown fences first
    intent = parsed.get("intent", "unknown")
    params = parsed.get("params", {})
    
    # Step 2: Execute DB query based on intent
    result = {}
    action_links = []
    
    if intent == "who_missed_assignment":
        assignment_ref = params.get("assignment_ref")
        # Fuzzy match assignment title
        assignments = db.query(Assignment).filter(
            Assignment.class_id == class_id,
            Assignment.title.ilike(f"%{assignment_ref}%")
        ).all()
        if not assignments:
            return no_data_response()
        assignment = assignments[0]  # take first match
        
        non_submitters = db.execute("""
            SELECT u.id, u.full_name, u.registration_id
            FROM users u
            JOIN class_memberships cm ON cm.user_id = u.id AND cm.class_id = :class_id AND cm.member_role = 'STUDENT' AND cm.status = 'ACTIVE'
            LEFT JOIN submissions s ON s.student_id = u.id AND s.assignment_id = :assignment_id AND s.is_current = true
            WHERE s.id IS NULL
        """, {"class_id": class_id, "assignment_id": assignment.id}).fetchall()
        
        result = {
            "type": "student_list",
            "data": [{"student_id": str(r.id), "full_name": r.full_name, "registration_id": r.registration_id} for r in non_submitters],
            "message": f"{len(non_submitters)} student(s) have not submitted '{assignment.title}'"
        }
        action_links = [{"label": f"View {r['full_name']}'s profile", "route": f"/analytics/students/{r['student_id']}"} for r in result["data"][:3]]
    
    elif intent == "student_completion_rate":
        student_name = params.get("student_name")
        student = db.query(User).join(ClassMembership).filter(
            ClassMembership.class_id == class_id,
            ClassMembership.member_role == 'STUDENT',
            User.full_name.ilike(f"%{student_name}%")
        ).first()
        if not student:
            return no_data_response(f"No student named '{student_name}' found in this class.")
        
        sa = db.query(StudentAnalytics).filter_by(student_id=student.id, class_id=class_id).first()
        result = {
            "type": "student_profile",
            "data": [{"full_name": student.full_name, "completion_rate": float(sa.completion_rate) if sa else 0, "risk_level": sa.risk_level if sa else "NORMAL"}],
            "message": f"{student.full_name}'s completion rate is {sa.completion_rate if sa else 0}%"
        }
        action_links = [{"label": f"View {student.full_name}'s full profile", "route": f"/analytics/students/{student.id}"}]
    
    elif intent == "class_summary":
        ca = db.query(ClassAnalytics).filter_by(class_id=class_id).first()
        if not ca:
            return no_data_response("No analytics data available yet for this class.")
        result = {
            "type": "class_summary",
            "data": [{"avg_completion": float(ca.avg_completion), "avg_miss_rate": float(ca.avg_miss_rate), "high_risk_count": ca.high_risk_count, "total_students": ca.total_students}],
            "message": f"Class completion rate: {ca.avg_completion}% | At-risk students: {ca.high_risk_count}"
        }
    
    elif intent == "risk_students":
        risk_rows = db.query(StudentAnalytics, User).join(User, User.id == StudentAnalytics.student_id).filter(
            StudentAnalytics.class_id == class_id,
            StudentAnalytics.risk_level.in_(['HIGH','MEDIUM'])
        ).all()
        result = {
            "type": "risk_list",
            "data": [{"student_id": str(sa.student_id), "full_name": u.full_name, "risk_level": sa.risk_level, "consecutive_misses": sa.consecutive_misses} for sa, u in risk_rows],
            "message": f"{len(risk_rows)} student(s) are at risk"
        }
        action_links = [{"label": f"View {r['full_name']}", "route": f"/analytics/students/{r['student_id']}"} for r in result["data"][:3]]
    
    elif intent == "student_profile":
        # Same as student_completion_rate but returns full analytics row
        pass  # similar pattern
    
    elif intent == "general_count":
        # For admin: count their classes/students
        # For mentor: class student count
        pass
    
    else:
        return {
            "intent": "unknown",
            "query_text": query_text,
            "result": {"type": "no_data", "data": [], "message": "I can answer questions about submissions, completion rates, at-risk students, and class summaries."},
            "action_links": []
        }
    
    # Log query
    db.add(AiQueryLog(requested_by=user_id, class_id=class_id, query_text=query_text, detected_intent=intent, response_payload=result))
    db.commit()
    
    return {"intent": intent, "query_text": query_text, "result": result, "action_links": action_links}
```

### 13.4 Flutter AI Panel Behavior

- Free-form text input field (TextEditingController)
- Send button → POST /ai/query
- Loading state: show CircularProgressIndicator
- Response rendered as result card:
  - `message` as headline
  - `data` as a mini-table or list of chips
  - `action_links` as tappable ElevatedButton widgets → navigate to that route
- If `type == "no_data"`: show grey info card with suggestion text
- If 0 classes/students exist and admin asks "how many classes?": returns `general_count` intent → "You have 0 classes" — correct, not an error

---

## 14. Frontend Screen Map & UI Behavior

### 14.1 Splash Screen (`splash_screen.dart`)

**On load:**
1. Call `GET /health` (to wake Render server)
2. While waiting: show AssignHub logo + "Connecting..." text
3. If health takes > 5s: show "Server is starting up, please wait..." (Render cold start)
4. Check SecureStorage for `access_token`
5. If found: call `GET /auth/me`
   - On success: route to correct dashboard based on `role`
   - On 401: try refresh → if ok route, if fail → `/login`
6. If not found: route to `/login`

---

### 14.2 Login Screen (`login_screen.dart`)

**Fields:** Email (TextFormField), Password (TextFormField, obscure), Registration ID (TextFormField, hint: "Leave blank if admin")

**"Login" button:**
- Validates: email non-empty + valid format, password non-empty
- Calls `POST /auth/login`
- Loading: disable button, show spinner
- On 200: save tokens → route to role dashboard (from response `user.role`)
- On 401: show "Invalid email, password, or registration ID"
- On 403 (pending): show "Your account is pending approval by your mentor"
- On 403 (blocked): show "Your account has been blocked. Contact admin."

**"Register as Admin" text button:** → navigates to `/admin/signup`

---

### 14.3 Admin Signup Screen (`admin_signup_screen.dart`)

**Fields:** Full Name, Email, Password, Confirm Password  

**"Sign Up" button:**
- Validate: all non-empty, password == confirm, password ≥ 8 chars
- Calls `POST /auth/admin/signup`
- On 201: navigate to OTP screen, pass email
- On 409: "An account with this email already exists"

---

### 14.4 OTP Verify Screen (`otp_verify_screen.dart`)

**Fields:** 6-digit OTP (auto-focus, numeric keyboard)  

**"Verify" button:**
- Calls `POST /auth/admin/verify-otp`
- On 200: save tokens → route to Admin Dashboard
- On 400: "Incorrect OTP. Please try again."
- On 410: "OTP has expired. Go back and sign up again."

**Resend OTP:** Not in MVP scope. Note in README.

---

### 14.5 Admin Dashboard Screen (`admin_dashboard_screen.dart`)

**On load:** `GET /analytics/admin/overview`  
**Top section:** 4 summary tiles (total_classes, total_mentors, total_students, total_assignments)  
**Bottom section:** ListView of class cards  

**Class card:**
- Shows: class_name, primary_mentor_name ("No mentor" if null), avg_completion%, high_risk_count, student_count
- Tap → `class_analytics_drill_screen.dart`

**FAB "+" button:** → `create_class_screen.dart`  
**Drawer/bottom nav:** Classes | Analytics | Bulk Import | AI Query | Notifications

---

### 14.6 Create Class Screen (`create_class_screen.dart`)

**Fields:** Class Name (required), Description (optional), Academic Year (optional)  

**"Create" button:**
- POST /classes
- On 201: pop screen, update class list (add returned class object — no refetch)

---

### 14.7 Class Detail Screen (`class_detail_screen.dart`)

**On load:** `GET /classes/{class_id}`  
**Shows:** class_name, description, primary mentor name + email, co-mentors list, student_count, assignment_count  

**Buttons:**
- "Pending Approvals (N)" → `approvals_screen.dart` — N from `GET /classes/{id}/approvals` unread count
- "Students" → `class_students_screen.dart`
- "Add Co-Mentor" → `add_co_mentor_screen.dart`
- "Edit Class" → PATCH /classes/{id} inline form
- "Archive Class" → PATCH /classes/{id} with status=ARCHIVED (confirm dialog first)

---

### 14.8 Approvals Screen (`approvals_screen.dart`) — Admin and Mentor

**On load:** `GET /classes/{class_id}/approvals`  

**Each pending student card shows:**
- full_name, email, registration_id, requested_at

**"Approve" button:**
- PATCH /classes/{id}/students/{sid}/approve
- On 200: remove card from list (optimistic update)
- Show success snackbar: "Approved"

**"Reject" button:**
- Show dialog: "Reason for rejection (optional)" text field
- PATCH /classes/{id}/students/{sid}/reject
- On 200: remove card from list

**Empty state:** "No pending approvals"

---

### 14.9 Assignment Tracker Screen (`assignment_tracker_screen.dart`)

**On load:**
1. `GET /assignments/{assignment_id}/tracker` — full initial state
2. Open WebSocket: `WSS /ws/tracker/{assignment_id}?token=<access_token>`

**Header section:**
- Assignment title, deadline_at, status badge
- 4 count badges: Submitted / Pending / Missed / Late (from tracker response)

**Student list:**
- Each row: full_name, registration_id, tracker_status badge (color coded), submitted_at (if submitted)
- SUBMITTED: green badge
- LATE: orange badge
- MISSED: red badge
- PENDING: grey badge

**WebSocket update (submission_created):**
- Find student row by student_id
- Update tracker_status badge and submitted_at
- Increment relevant count badge
- No full reload needed

**WebSocket update (tracker_refresh):**
- Reload full student list: `GET /assignments/{assignment_id}/tracker`
- Show "Assignment Closed" banner

**"Close Assignment" button (PUBLISHED only):**
- Confirm dialog: "Close assignment? Late submissions will be marked as missed."
- POST /assignments/{assignment_id}/close
- On 200: update status badge, disable button

**"Export" button (CLOSED only):**
- POST /exports/assignment-tracker
- Poll GET /exports/{job_id} every 3s
- On DONE: open download URL (POST /storage/presigned-download then open URL)

---

### 14.10 Submit Assignment Screen (`submit_assignment_screen.dart`)

**On load:** assignment data from parent screen state (already fetched)  

**File submission UI (if submission_type=FILE or BOTH):**
- "Select File" button → file_picker
- Show selected filename + size
- "Upload" button:
  1. POST /storage/presigned-upload
  2. HTTP PUT to upload_url
  3. On success: show "File ready to submit" with green check

**Text submission UI (if submission_type=TEXT or BOTH):**
- Multi-line text field

**"Submit Assignment" button:**
- Disabled until: file uploaded (if FILE) OR text non-empty (if TEXT)
- POST /assignments/{id}/submit
- On 201: show receipt card: "Submitted at [submitted_at]" + is_late badge if late
- On error: show "Submission failed. Please try again."

---

### 14.11 Student Dashboard Screen (`student_dashboard_screen.dart`)

**On load:** `GET /analytics/students/{student_id}` (student_id from JWT)  

**Tappable metric cards — on tap, show bottom sheet with filtered assignment_history list:**
- total_submitted card → filter: tracker_status=SUBMITTED, show title + submitted_at
- total_missed card → filter: tracker_status=MISSED, show title + deadline_at
- total_late card → filter: tracker_status=LATE, show title + submitted_at

**Assignment history list:**
- Color-coded rows (see Section 10.1)
- Each row tappable → `assignment_detail_screen.dart`

**Empty state:** total_assigned=0 → "No assignments have been posted yet."

---

### 14.12 AI Query Screen (`ai_query_screen.dart`) — Admin and Mentor

**On load:** Load class_id from auth state

**Text input:** Full-width text field with "Ask anything about your class..." placeholder

**"Ask" button:**
- POST /ai/query
- Loading: show typing indicator (3 animated dots)
- On 200: render result card below input

**Result card:**
- `result.message` in bold at top
- If `result.type == "student_list"`: render mini-list of student name + registration_id
- If `result.type == "class_summary"`: render 4 metric tiles
- If `result.type == "student_profile"`: render completion rate + risk badge
- If `result.type == "risk_list"`: render list with risk badges
- If `result.type == "no_data"`: grey info card with suggestion text
- `action_links[]`: render as ElevatedButton row → each navigates to the route in the link

**Query history:** Last 5 queries shown as chips above input field. Tap to re-run.

---

## 15. Frontend ↔ Backend Field Contract

This section lists every field name used in API responses mapped to the exact Dart model field. Zero inconsistency allowed.

### 15.1 UserModel (Dart)
```dart
class UserModel {
  final String id;              // ← "id" (UUID as String)
  final String fullName;        // ← "full_name"
  final String email;           // ← "email"
  final String role;            // ← "role" ("ADMIN"|"MENTOR"|"STUDENT")
  final String? classId;        // ← "class_id" (nullable)
  final String? className;      // ← "class_name" (nullable)
  final String? registrationId; // ← "registration_id" (nullable)
  final String status;          // ← "status"
}
```

### 15.2 ClassModel (Dart)
```dart
class ClassModel {
  final String id;              // ← "id"
  final String className;       // ← "class_name"
  final String? description;    // ← "description"
  final String? academicYear;   // ← "academic_year"
  final String status;          // ← "status"
  final int studentCount;       // ← "student_count"
  final int mentorCount;        // ← "mentor_count"
  final String createdAt;       // ← "created_at"
}
```

### 15.3 AssignmentModel (Dart)
```dart
class AssignmentModel {
  final String id;              // ← "id"
  final String title;           // ← "title"
  final String? description;    // ← "description"
  final String contentType;     // ← "content_type"
  final String? contentUrl;     // ← "content_url"
  final String? richTextBody;   // ← "rich_text_body"
  final String submissionType;  // ← "submission_type"
  final DateTime? deadlineAt;   // ← "deadline_at" (parsed from ISO8601)
  final String status;          // ← "status"
  final String classId;         // ← "class_id"
  final String createdByName;   // ← "created_by_name"
  final DateTime createdAt;     // ← "created_at"
  final StudentSubmissionInfo? studentSubmission; // ← "student_submission"
}

class StudentSubmissionInfo {
  final bool submitted;         // ← "submitted"
  final String? submissionId;   // ← "submission_id"
  final DateTime? submittedAt;  // ← "submitted_at"
  final bool isLate;            // ← "is_late"
  final int version;            // ← "version"
}
```

### 15.4 SubmissionModel (Dart)
```dart
class SubmissionModel {
  final String submissionId;    // ← "submission_id"
  final String assignmentId;    // ← "assignment_id"
  final String assignmentTitle; // ← "assignment_title"
  final String submissionType;  // ← "submission_type"
  final DateTime submittedAt;   // ← "submitted_at"
  final bool isLate;            // ← "is_late"
  final int version;            // ← "version"
}
```

### 15.5 StudentAnalyticsModel (Dart)
```dart
class StudentAnalyticsModel {
  final String studentId;           // ← "student_id"
  final String fullName;            // ← "full_name"
  final String className;           // ← "class_name"
  final int totalAssigned;          // ← "total_assigned"
  final int totalSubmitted;         // ← "total_submitted"
  final int totalMissed;            // ← "total_missed"
  final int totalLate;              // ← "total_late"
  final double completionRate;      // ← "completion_rate"
  final int currentStreak;          // ← "current_streak"
  final int longestStreak;          // ← "longest_streak"
  final double? avgSubmissionDelayHours; // ← "avg_submission_delay_hours"
  final String riskLevel;           // ← "risk_level"
  final int consecutiveMisses;      // ← "consecutive_misses"
  final double classAvgCompletion;  // ← "class_avg_completion"
  final List<AssignmentHistoryItem> assignmentHistory; // ← "assignment_history"
}

class AssignmentHistoryItem {
  final String assignmentId;    // ← "assignment_id"
  final String title;           // ← "title"
  final DateTime? deadlineAt;   // ← "deadline_at"
  final String trackerStatus;   // ← "tracker_status"
  final DateTime? submittedAt;  // ← "submitted_at"
  final bool isLate;            // ← "is_late"
}
```

### 15.6 ClassAnalyticsModel (Dart)
```dart
class ClassAnalyticsModel {
  final String classId;         // ← "class_id"
  final String className;       // ← "class_name"
  final int totalStudents;      // ← "total_students"
  final int totalAssignments;   // ← "total_assignments"
  final double avgCompletion;   // ← "avg_completion"
  final double avgMissRate;     // ← "avg_miss_rate"
  final double avgLateRate;     // ← "avg_late_rate"
  final int highRiskCount;      // ← "high_risk_count"
  final List<BottleneckAssignment> bottleneckAssignments; // ← "bottleneck_assignments"
  final Map<String, int> riskDistribution; // ← "risk_distribution"
}

class BottleneckAssignment {
  final String assignmentId;    // ← "assignment_id"
  final String title;           // ← "title"
  final double completionRate;  // ← "completion_rate"
}
```

### 15.7 TrackerModel (Dart)
```dart
class TrackerModel {
  final String assignmentId;    // ← "assignment_id"
  final String title;           // ← "title"
  final DateTime? deadlineAt;   // ← "deadline_at"
  final String status;          // ← "status"
  final int submittedCount;     // ← "submitted_count"
  final int pendingCount;       // ← "pending_count"
  final int missedCount;        // ← "missed_count"
  final int lateCount;          // ← "late_count"
  final List<TrackerStudent> students; // ← "students"
}

class TrackerStudent {
  final String studentId;       // ← "student_id"
  final String fullName;        // ← "full_name"
  final String registrationId;  // ← "registration_id"
  final String trackerStatus;   // ← "tracker_status"
  final DateTime? submittedAt;  // ← "submitted_at"
  final bool isLate;            // ← "is_late"
  final String? submissionId;   // ← "submission_id"
}
```

### 15.8 NotificationModel (Dart)
```dart
class NotificationModel {
  final String id;              // ← "id"
  final String notificationType; // ← "notification_type"
  final String title;           // ← "title"
  final String body;            // ← "body"
  final Map<String, dynamic>? payload; // ← "payload"
  final bool isRead;            // ← "is_read"
  final DateTime createdAt;     // ← "created_at"
}
```

### 15.9 AiResponseModel (Dart)
```dart
class AiResponseModel {
  final String intent;          // ← "intent"
  final String queryText;       // ← "query_text"
  final AiResult result;        // ← "result"
  final List<ActionLink> actionLinks; // ← "action_links"
}

class AiResult {
  final String type;            // ← "type"
  final List<dynamic> data;     // ← "data"
  final String message;         // ← "message"
}

class ActionLink {
  final String label;           // ← "label"
  final String route;           // ← "route"
}
```

---

## 16. Deployment Architecture

### 16.1 Render Services

| Service | Type | Plan | Notes |
|---|---|---|---|
| `assignhub-api` | Web Service | Free | FastAPI + Uvicorn, 1 worker |
| `assignhub-db` | PostgreSQL | Free | Max 1GB storage, max 97 connections |

**Important:** Render free tier spins down after 15 minutes of inactivity. First request takes 30–60s. Flutter handles this via `GET /health` on splash screen (Section 14.1).

**APScheduler with PostgreSQL jobstore:** Deadline jobs persist across server restarts. Config:
```python
# scheduler/jobs.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url=os.environ['DATABASE_URL'])
}
scheduler = AsyncIOScheduler(jobstores=jobstores)

# Register in main.py lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()
```

### 16.2 Environment Variables

```bash
# Backend/.env

# Database
DATABASE_URL=postgresql://user:password@host:5432/assignhub

# JWT
JWT_SECRET_KEY=minimum_32_char_random_string_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Gmail SMTP (admin OTP)
GMAIL_ADDRESS=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_16_char_app_password

# Brevo SMTP (invitations)
BREVO_SMTP_HOST=smtp-relay.brevo.com
BREVO_SMTP_PORT=587
BREVO_SMTP_USER=your_brevo_login_email
BREVO_SMTP_KEY=your_brevo_smtp_key
SENDER_EMAIL=noreply@assignhub.in
SENDER_NAME=AssignHub

# AWS S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-south-1
S3_BUCKET_NAME=assignhub-files

# FCM
FCM_CREDENTIALS_JSON={"type": "service_account", ...}
# Paste full Firebase service account JSON as a single-line string

# LLM (use one)
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key
LLM_PROVIDER=gemini   # or groq

# App
APP_ENV=production
CORS_ORIGINS=*
```

### 16.3 `main.py` Structure

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from scheduler.jobs import scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="AssignHub API", version="1.0.0", lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Router registration
app.include_router(auth_router,         prefix="/api/v1/auth",          tags=["Auth"])
app.include_router(class_router,        prefix="/api/v1/classes",        tags=["Classes"])
app.include_router(provision_router,    prefix="/api/v1/provision",      tags=["Provisioning"])
app.include_router(assignment_router,   prefix="/api/v1/assignments",    tags=["Assignments"])
app.include_router(submission_router,   prefix="/api/v1",               tags=["Submissions"])
app.include_router(storage_router,      prefix="/api/v1/storage",        tags=["Storage"])
app.include_router(analytics_router,    prefix="/api/v1/analytics",      tags=["Analytics"])
app.include_router(notification_router, prefix="/api/v1/notifications",  tags=["Notifications"])
app.include_router(export_router,       prefix="/api/v1/exports",        tags=["Exports"])
app.include_router(ai_router,           prefix="/api/v1/ai",             tags=["AI"])
app.include_router(ws_router)           # No prefix — registers /api/v1/ws/tracker/{id}

@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
```

### 16.4 Flutter Build

```bash
# In Frontend/ directory
flutter build apk --release

# Output: build/app/outputs/flutter-apk/app-release.apk
# Upload to Google Drive
# Submit Drive link on Unstop
```

**Flutter API base URL** (`core/constants.dart`):
```dart
const String kBaseUrl = "https://assignhub-api.onrender.com/api/v1";
const String kWsUrl   = "wss://assignhub-api.onrender.com/api/v1";
```

---

## 17. No-Mismatch Contract

This section defines binding rules that prevent the class of errors from past projects: field mismatches, type errors, null crashes, enum inconsistencies, routing failures.

### 17.1 Field Naming
- All JSON fields: `snake_case`
- All DB columns: `snake_case`
- All Dart model fields: `camelCase` (mapped from snake_case via `fromJson`)
- No exceptions. No mixed casing.

### 17.2 ID Type
- All primary keys in DB: `UUID`
- All foreign keys: `UUID`
- All IDs in API responses: `String` (JSON)
- All IDs in Dart models: `String`
- Never use `int` for any ID field.

### 17.3 Timestamp Format
- All timestamps stored: `TIMESTAMPTZ` in PostgreSQL
- All timestamps in API responses: ISO 8601 with timezone — `"2026-06-25T10:00:00Z"`
- Flutter parse: `DateTime.parse("2026-06-25T10:00:00Z")` — works natively
- Never return bare date strings like `"2026-06-25"` for datetime fields

### 17.4 Enum Values (uppercase strings, consistently used in DB, API, and Flutter)
```
Role:             ADMIN | MENTOR | STUDENT
User status:      PENDING_OTP | ACTIVE | INACTIVE | BLOCKED
Membership status:PENDING | ACTIVE | INACTIVE | REJECTED
Assignment status:DRAFT | PUBLISHED | CLOSED
Tracker status:   SUBMITTED | PENDING | MISSED | LATE
Risk level:       NORMAL | LOW | MEDIUM | HIGH | RECOVERING
Content type:     PDF | LINK | RICH_TEXT
Submission type:  FILE | TEXT | BOTH
Notification type:STUDENT_APPROVED | STUDENT_REJECTED | ASSIGNMENT_PUBLISHED |
                  DEADLINE_REMINDER | SUBMISSION_RECEIPT | MISSED_DEADLINE |
                  RISK_ALERT | CO_MENTOR_ADDED | CLASS_ARCHIVED
Export status:    PENDING | DONE | FAILED
Import status:    UPLOADED | VALIDATING | PARTIAL | COMPLETED | FAILED
Join via:         MANUAL | BULK_IMPORT
Reminder status:  SCHEDULED | TRIGGERED | CANCELLED
```

### 17.5 Null Handling Rules
- Every nullable field in the API response MUST be included in the JSON with a `null` value — never omitted
- Flutter models declare nullable fields as `String?`, `DateTime?`, etc.
- `student_analytics` row guaranteed to exist for every approved student → no null analytics crash
- `class_analytics` row guaranteed to exist for every class → no null analytics crash
- `assignment_analytics` row guaranteed to exist for every published assignment
- `student_submission` in assignment detail response always present — `submitted: false` when no submission

### 17.6 File Upload Contract
- File is NEVER sent to FastAPI directly
- Flow: presigned URL → S3 PUT → use returned `file_url` in submission JSON body
- Submission body is always `application/json`, never `multipart/form-data`
- `file_url` in submissions table is an S3 URL string — to display/download, always call `/storage/presigned-download` first

### 17.7 Analytics Initialization
- When class is created → `INSERT INTO class_analytics (class_id, all zeros)` — immediately
- When student is APPROVED (not created) → `INSERT INTO student_analytics (student_id, class_id, all zeros)` — immediately
- When assignment is PUBLISHED → `INSERT INTO assignment_analytics (assignment_id, total_targets)` — immediately
- Result: analytics endpoints never return 404 for existing entities

### 17.8 WebSocket Auth
- JWT token passed as query param `?token=<access_token>` (not Authorization header — WebSocket protocol doesn't support headers in Flutter's `web_socket_channel`)
- Backend extracts and validates token on WebSocket connect, before accepting the connection

### 17.9 Student Login Blocking
- `users.status = ACTIVE` for all students — this is the account-level status
- Login is blocked at the class membership level: `class_memberships.status` must be `ACTIVE`
- If `class_memberships.status = PENDING`: return 403 with message "Account pending approval"
- Never expose whether the block is account-level vs membership-level to the client (security)
- Dart client: show the same message for any 403 from login endpoint

### 17.10 APScheduler Persistence
- Jobstore: `SQLAlchemyJobStore` with `DATABASE_URL`
- All deadline-close, reminder, and student-reminder jobs written to DB on creation
- On server restart: APScheduler reloads all pending jobs from DB
- Jobs with `run_date` in the past (missed while server was down) fire immediately on restart

---

*AssignHub Master Architecture v2.0 — Final | DevFusion 3.0 | AssignHub PS-1*  
*All evaluation report issues incorporated. Zero gaps. Zero mocks.*