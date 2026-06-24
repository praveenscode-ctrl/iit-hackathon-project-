# BACKEND_IMPLEMENTATION.md

## Implementation Goal
Build the backend exactly to the master architecture contract. Use the exact same names, routes, tables, fields, enums, and response shapes everywhere. Do not invent alternate names, alias routes, or extra fields.

## Code Style Rules
- Write plain, practical code.
- Keep functions short and readable.
- Use natural names like `get_user_info`, `make_token`, `calc_risk`, `save_submission`.
- Avoid over-abstracting simple flows.
- Avoid huge service layers when a small helper is enough.
- Do not introduce AI-generated style symmetry or heavy design patterns.
- Keep comments useful but not excessive.

## Repository Layout
Use the exact backend folder structure from the master architecture.

```text
Backend/
├── .env
├── .env.example
├── requirements.txt
├── alembic.ini
├── alembic/
│   └── versions/
│       └── 001_initial_schema.py
├── main.py
├── database.py
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── class_.py
│   ├── assignment.py
│   ├── submission.py
│   ├── analytics.py
│   ├── notification.py
│   ├── bulk_import.py
│   └── export.py
├── schemas/
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
│   ├── auth_service.py
│   ├── email_service.py
│   ├── fcm_service.py
│   ├── s3_service.py
│   ├── analytics_service.py
│   ├── export_service.py
│   └── ai_service.py
├── websocket/
│   └── tracker_ws.py
├── scheduler/
│   └── jobs.py
└── utils/
    ├── id_generator.py
    ├── security.py
    └── dependencies.py
```

## Database Layer

### Database rules
- PostgreSQL only.
- UUID primary keys using `gen_random_uuid()`.
- `TIMESTAMPTZ` for all timestamps.
- Uppercase enum-like values using `VARCHAR` + `CHECK`.
- `snake_case` everywhere.
- Use SQLAlchemy ORM models plus Alembic migrations.
- Keep DB rows and API response fields aligned exactly.

### Table order for migration
Create tables in this order:
1. `users`
2. `otp_verifications`
3. `admin_profiles`
4. `refresh_tokens`
5. `classes`
6. `class_memberships`
7. `assignments`
8. `submissions`
9. `student_analytics`
10. `class_analytics`
11. `assignment_analytics`
12. `notifications`
13. `reminder_jobs`
14. `bulk_import_batches`
15. `bulk_import_errors`
16. `export_jobs`
17. `ai_query_logs`
18. `scheduler_jobs` managed by APScheduler, not created manually

### Seed data requirements
No fake content data.
Only seed lookup-safe defaults if absolutely needed:
- none for classes
- none for users
- none for assignments
- no mock rows
The database must start empty except migration-created tables.

## Table Schemas
Implement every table exactly as below.

### `users`
```sql
CREATE TABLE users (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  role              VARCHAR(10) NOT NULL CHECK (role IN ('ADMIN','MENTOR','STUDENT')),
  full_name         VARCHAR(120) NOT NULL,
  email             VARCHAR(255) UNIQUE NOT NULL,
  password_hash     TEXT        NOT NULL,
  registration_id   VARCHAR(50) UNIQUE,
  phone             VARCHAR(20),
  status            VARCHAR(20) NOT NULL DEFAULT 'ACTIVE'
                    CHECK (status IN ('PENDING_OTP','ACTIVE','INACTIVE','BLOCKED')),
  fcm_token         TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

### `otp_verifications`
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

### `admin_profiles`
```sql
CREATE TABLE admin_profiles (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id           UUID        UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  organization_name VARCHAR(150),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `refresh_tokens`
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

### `classes`
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

### `class_memberships`
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
  rejection_reason  TEXT,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(class_id, user_id)
);
CREATE INDEX idx_cm_class ON class_memberships(class_id);
CREATE INDEX idx_cm_user ON class_memberships(user_id);
CREATE INDEX idx_cm_status ON class_memberships(status);
```

Rules:
- Mentors are created with `status='ACTIVE'`.
- Students are created with `status='PENDING'`.
- Approval changes student membership to `ACTIVE`.
- Rejection changes student membership to `REJECTED`.

### `assignments`
```sql
CREATE TABLE assignments (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  class_id         UUID        NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
  created_by       UUID        NOT NULL REFERENCES users(id),
  title            VARCHAR(200) NOT NULL,
  description      TEXT,
  content_type     VARCHAR(10) NOT NULL CHECK (content_type IN ('PDF','LINK','RICH_TEXT')),
  content_url      TEXT,
  rich_text_body   TEXT,
  submission_type  VARCHAR(5)  NOT NULL CHECK (submission_type IN ('FILE','TEXT','BOTH')),
  deadline_at      TIMESTAMPTZ,
  auto_close       BOOLEAN     NOT NULL DEFAULT false,
  status           VARCHAR(10) NOT NULL DEFAULT 'DRAFT'
                   CHECK (status IN ('DRAFT','PUBLISHED','CLOSED')),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_assignments_class ON assignments(class_id);
CREATE INDEX idx_assignments_status ON assignments(status);
```

### `submissions`
```sql
CREATE TABLE submissions (
  id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  assignment_id    UUID        NOT NULL REFERENCES assignments(id) ON DELETE CASCADE,
  student_id       UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  submission_type  VARCHAR(5)  NOT NULL CHECK (submission_type IN ('FILE','TEXT')),
  file_url         TEXT,
  text_answer      TEXT,
  is_late          BOOLEAN     NOT NULL DEFAULT false,
  version          INT         NOT NULL DEFAULT 1,
  is_current       BOOLEAN     NOT NULL DEFAULT true,
  submitted_at     TIMESTAMPTZ NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(assignment_id, student_id, version)
);
CREATE INDEX idx_submissions_assignment ON submissions(assignment_id);
CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_submissions_current ON submissions(is_current);
```

### `student_analytics`
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

### `class_analytics`
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

### `assignment_analytics`
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
  last_computed_at TIMESTAMPTZ  NOT NULL DEFAULT now()
);
```

### `notifications`
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
  is_read           BOOLEAN     NOT NULL DEFAULT false,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_notif_user ON notifications(user_id);
CREATE INDEX idx_notif_read ON notifications(is_read);
```

### `reminder_jobs`
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

### `bulk_import_batches`
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

### `bulk_import_errors`
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

### `export_jobs`
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

### `ai_query_logs`
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

## Relationships
- `users` has many `class_memberships`, `submissions`, `refresh_tokens`, `notifications`, `student_analytics`, `bulk_import_batches`, `export_jobs`, `ai_query_logs`.
- `classes` has many `class_memberships`, `assignments`, `student_analytics`, `class_analytics`.
- `assignments` has many `submissions`, `reminder_jobs`, `assignment_analytics`.
- `admin_profiles` is 1:1 with `users` for admins.

## ORM Layer
Build one SQLAlchemy model per table.
- Keep table names identical.
- Keep column names identical.
- Use relationship definitions for joins, but do not hide the actual foreign keys.
- Use explicit indexes where listed.

## Core Backend Modules

### `main.py`
Responsibilities:
- create FastAPI app
- register routers
- set CORS
- add exception handlers
- add health route
- start/stop APScheduler
- load environment variables

### `database.py`
Responsibilities:
- create engine
- session factory
- dependency `get_db`

### `utils/security.py`
Responsibilities:
- password hash/verify
- JWT create/verify
- refresh token hash verify
- OTP generation helper

### `utils/dependencies.py`
Responsibilities:
- `get_current_user`
- `require_role`
- `verify_mentor_class_access`
- `verify_admin_class_access`
- student self-check helpers

### `services/auth_service.py`
Responsibilities:
- signup logic
- login logic
- refresh logic
- logout logic
- OTP verify logic

### `services/email_service.py`
Responsibilities:
- Gmail SMTP OTP mail
- Brevo invitation mail

### `services/fcm_service.py`
Responsibilities:
- push notifications for approvals, assignments, reminders, risk alerts

### `services/s3_service.py`
Responsibilities:
- presigned upload generation
- file URL helpers
- presigned download generation

### `services/analytics_service.py`
Responsibilities:
- recompute student analytics
- recompute class analytics
- recompute assignment analytics
- risk flag updates

### `services/export_service.py`
Responsibilities:
- create XLSX exports
- write result to S3

### `services/ai_service.py`
Responsibilities:
- intent parsing via Groq LLM (send only `query_text` — never send DB data or PII to LLM)
- DB query execution based on detected intent
- supported intents (from master architecture Section 13.2 — implement all 6):
  - `who_missed_assignment` — find non-submitters for a given assignment by title match
  - `student_completion_rate` — fetch completion rate for a named student
  - `class_summary` — return class-level analytics from `class_analytics`
  - `risk_students` — return HIGH/MEDIUM risk students for the class
  - `student_profile` — return full analytics row for a named student
  - `general_count` — count classes or students depending on role context
  - `unknown` — catch-all; return `no_data` response with suggestion message
- log every query in `ai_query_logs` table after responding
- refer to master architecture Section 13.3 for the exact SQL for each intent

### `websocket/tracker_ws.py`
Responsibilities:
- tracker room manager
- connect/disconnect
- broadcast submission events

### `scheduler/jobs.py`
Responsibilities:
- APScheduler init
- deadline close jobs
- 24h reminder jobs
- 2h reminder jobs
- PostgreSQL job store setup

## Authentication Flow

### Admin signup
1. `POST /auth/admin/signup`
2. create `users` row with `role='ADMIN'`, `status='PENDING_OTP'`
3. insert `otp_verifications`
4. send Gmail SMTP email
5. return message only

### Admin OTP verify
1. `POST /auth/admin/verify-otp`
2. check latest unused OTP row
3. verify expiry and code
4. mark OTP used
5. update admin `users.status='ACTIVE'`
6. insert `admin_profiles`
7. create access and refresh tokens
8. store hashed refresh token in `refresh_tokens`

### Login
1. `POST /auth/login`
2. verify password
3. verify registration_id for mentor/student
4. verify `users.status='ACTIVE'`
5. if student, require active class membership
6. if mentor, require active class membership
7. update `fcm_token` if present
8. return tokens and user data

### Refresh
1. `POST /auth/refresh`
2. compare token with stored refresh token hashes
3. if valid and not revoked, issue new access token
4. do not change refresh token unless you choose to rotate, but if rotating then update the `refresh_tokens` row and keep the field names same

### Logout
1. `POST /auth/logout`
2. mark matching `refresh_tokens.revoked=true`
3. frontend deletes local tokens

## Health Endpoint

### `GET /health`
**Public — no auth required**
Purpose: Flutter calls on app launch to wake the Render server.
Response HTTP 200:
```json
{ "status": "ok", "timestamp": "2026-06-25T10:00:00Z" }
```

## Auth Endpoint Specs

### `POST /auth/admin/signup`
**Public**
Request:
```json
{ "full_name": "string", "email": "string", "password": "string" }
```
Response HTTP 201:
```json
{ "message": "OTP sent to your email" }
```
Errors:
- `409` email already exists
- `400` invalid email or weak password

### `POST /auth/admin/verify-otp`
**Public**
Request:
```json
{ "email": "string", "otp": "string" }
```
Response:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "user": { "id": "uuid", "full_name": "string", "role": "ADMIN" }
}
```
Errors:
- `400` invalid OTP
- `410` OTP expired

### `POST /auth/login`
**Public**
Request:
```json
{
  "email": "string",
  "password": "string",
  "registration_id": "string",
  "fcm_token": "string"
}
```
Response:
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
Errors:
- `401` invalid credentials
- `403` pending approval
- `403` account blocked or inactive

### `POST /auth/refresh`
**Public**
Request:
```json
{ "refresh_token": "string" }
```
Response:
```json
{ "access_token": "string" }
```
Errors:
- `401` invalid or expired refresh token

### `POST /auth/logout`
**Protected**
Request:
```json
{ "refresh_token": "string" }
```
Response:
```json
{ "message": "Logged out" }
```

### `GET /auth/me`
**Protected**
Response:
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

## Class Endpoints

### `POST /classes`
**Protected: ADMIN**
Request:
```json
{
  "class_name": "string",
  "description": "string | null",
  "academic_year": "string | null"
}
```
Effects:
- insert `classes`
- insert `class_analytics`
Response HTTP 201:
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

### `GET /classes`
**Protected: ADMIN**
Response:
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

### `GET /classes/my-classes`
**Protected: MENTOR**
Response:
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

### `GET /classes/{class_id}`
**Protected: ADMIN or MENTOR**
Response:
```json
{
  "id": "uuid",
  "class_name": "string",
  "description": "string | null",
  "academic_year": "string | null",
  "status": "string",
  "primary_mentor": { "id": "uuid", "full_name": "string", "email": "string" },
  "co_mentors": [ { "id": "uuid", "full_name": "string", "email": "string" } ],
  "student_count": 0,
  "assignment_count": 0
}
```
Note: `primary_mentor` is null if no mentor assigned yet.

### `PATCH /classes/{class_id}`
**Protected: ADMIN (own class)**
Request:
```json
{
  "class_name": "string | null",
  "description": "string | null",
  "status": "ARCHIVED | null"
}
```
Effects:
- UPDATE classes SET updated fields WHERE id = :class_id AND admin_id = :user_id
- If status = 'ARCHIVED': INSERT notifications (notification_type='CLASS_ARCHIVED') for all active members of this class
- Return 404 if class does not belong to this admin
Response: same full shape as GET /classes/{class_id}
Errors:
- 403 if admin does not own this class
- 404 if class not found

### `GET /classes/{class_id}/students`
**Protected: ADMIN or MENTOR**
Response:
```json
{
  "students": [
    {
      "id": "uuid",
      "full_name": "string",
      "email": "string",
      "registration_id": "string",
      "membership_status": "PENDING | ACTIVE | REJECTED | INACTIVE",
      "risk_level": "NORMAL|LOW|MEDIUM|HIGH|RECOVERING",
      "completion_rate": 0.0,
      "joined_via": "MANUAL|BULK_IMPORT",
      "joined_at": "timestamp"
    }
  ]
}
```

### `GET /classes/{class_id}/approvals`
**Protected: ADMIN or MENTOR**
Response:
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

### `PATCH /classes/{class_id}/students/{student_id}/approve`
**Protected: ADMIN or MENTOR**
Request:
```json
{}
```
Effects:
- update `class_memberships.status='ACTIVE'`
- clear `rejection_reason`
- insert `notifications` row with `notification_type='STUDENT_APPROVED'`
- send FCM push
- create `student_analytics` row if missing
Response:
```json
{ "message": "Student approved", "student_id": "uuid" }
```

### `PATCH /classes/{class_id}/students/{student_id}/reject`
**Protected: ADMIN or MENTOR**
Request:
```json
{ "reason": "string | null" }
```
Note: `reason` is optional — Pydantic schema must use `Optional[str] = None`. Backend saves it to `class_memberships.rejection_reason` as-is (can be null).
Effects:
- update `class_memberships.status='REJECTED'`
- save `rejection_reason` (nullable)
- insert `notifications` row with `notification_type='STUDENT_REJECTED'`
- send FCM push
Response:
```json
{ "message": "Student rejected" }
```

### `POST /classes/{class_id}/co-mentors`
**Protected: ADMIN**
Request:
```json
{ "full_name": "string", "email": "string" }
```
Backend steps:
1. Check email not in users → 409 if exists
2. Auto-generate a random password (min 8 chars, alphanumeric) — do NOT ask the caller for it
3. Auto-generate registration_id: `MENTOR-<shortuuid 8 chars uppercase>`
4. INSERT INTO users (role='MENTOR', status='ACTIVE', password_hash=bcrypt(generated_password))
5. INSERT INTO class_memberships (member_role='MENTOR', is_primary_mentor=false, status='ACTIVE', joined_via='MANUAL')
6. Send Brevo invitation email with: email, generated_password, registration_id, class_name
7. Send FCM push to new co-mentor if fcm_token exists: title="Class Access Granted", body="You now have access to [class_name]"
8. INSERT INTO notifications (notification_type='CO_MENTOR_ADDED')
Response HTTP 201:
```json
{
  "id": "uuid",
  "full_name": "string",
  "email": "string",
  "registration_id": "string",
  "message": "Invitation email sent"
}
```

## Provisioning Endpoints

### `GET /provision/bulk-import/template`
**Protected: ADMIN**
Returns XLSX template.

### `POST /provision/bulk-import`
**Protected: ADMIN**
`multipart/form-data` with `file`.
Response HTTP 202:
```json
{
  "batch_id": "uuid",
  "status": "UPLOADED",
  "message": "Processing started"
}
```

### `GET /provision/bulk-import/{batch_id}`
**Protected: ADMIN**
Response:
```json
{
  "batch_id": "uuid",
  "status": "COMPLETED|PARTIAL|FAILED",
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

### `POST /provision/manual/mentor`
**Protected: ADMIN**
Request:
```json
{
  "class_id": "uuid",
  "full_name": "string",
  "email": "string",
  "password": "string",
  "is_primary_mentor": false
}
```
Response HTTP 201:
```json
{ "id": "uuid", "registration_id": "string", "message": "Invitation sent" }
```

### `POST /provision/manual/student`
**Protected: ADMIN or MENTOR (own class)**
Request:
```json
{
  "class_id": "uuid",
  "full_name": "string",
  "email": "string",
  "password": "string",
  "registration_id": "string"
}
```
Response HTTP 201:
```json
{ "id": "uuid", "message": "Student created. Awaiting approval." }
```

## Assignment Endpoints

### `POST /assignments`
**Protected: ADMIN or MENTOR**
Request:
```json
{
  "class_id": "uuid",
  "title": "string",
  "description": "string",
  "content_type": "PDF|LINK|RICH_TEXT",
  "content_url": "string or null",
  "rich_text_body": "string or null",
  "submission_type": "FILE|TEXT|BOTH",
  "deadline_at": "ISO8601 timestamp or null",
  "auto_close": true
}
```
Validation:
- mentor must own class
- one of `content_url` or `rich_text_body` must be present depending on `content_type`
- `submission_type` must match allowed upload mode
Response HTTP 201:
```json
{
  "id": "uuid",
  "title": "string",
  "status": "DRAFT",
  "deadline_at": "timestamp or null",
  "created_at": "timestamp"
}
```

### `GET /assignments?class_id={uuid}`
**Protected**
Response:
```json
{
  "assignments": [
    {
      "id": "uuid",
      "title": "string",
      "description": "string",
      "content_type": "string",
      "content_url": "string or null",
      "submission_type": "string",
      "deadline_at": "timestamp or null",
      "status": "DRAFT|PUBLISHED|CLOSED",
      "created_by_name": "string",
      "created_at": "timestamp"
    }
  ]
}
```

### `GET /assignments/{assignment_id}`
**Protected**
Response:
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
Note: `student_submission` is always present. When no submission exists, use the default object above. Key is present for all roles but populated only when role=STUDENT.

### `POST /assignments/{assignment_id}/publish`
**Protected: ADMIN or MENTOR**
Effects:
- set status to `PUBLISHED`
- insert `notifications` for all active students in class
- send FCM push to all active students: title="New Assignment", body="[title] — due [deadline or 'No deadline']"
- create `assignment_analytics` row with `total_targets = count of active students in class`
- if `deadline_at` is set, schedule **3 APScheduler jobs**:
  - `close_assignment_job` — fires at `deadline_at` → closes assignment + recomputes all analytics
  - `send_reminder_job` (24h) — fires at `deadline_at - 24 hours` → FCM to non-submitting students
  - `send_reminder_job` (2h) — fires at `deadline_at - 2 hours` → FCM to non-submitting students
- if `deadline_at` is null, no scheduler jobs created
Response:
```json
{ "status": "PUBLISHED", "message": "Assignment published and students notified" }
```

### `POST /assignments/{assignment_id}/close`
**Protected: ADMIN or MENTOR**
Effects:
- set status to `CLOSED`
- recompute analytics
- recalc risk for students
Response:
```json
{ "status": "CLOSED" }
```

### `GET /assignments/{assignment_id}/tracker`
**Protected: ADMIN or MENTOR**
Response:
```json
{
  "assignment_id": "uuid",
  "title": "string",
  "deadline_at": "timestamp or null",
  "status": "string",
  "submitted_count": 0,
  "pending_count": 0,
  "missed_count": 0,
  "late_count": 0,
  "students": [
    {
      "student_id": "uuid",
      "full_name": "string",
      "registration_id": "string",
      "tracker_status": "SUBMITTED|PENDING|MISSED|LATE",
      "submitted_at": "timestamp or null",
      "is_late": false,
      "submission_id": "uuid or null"
    }
  ]
}
```

## Submission Endpoints

### `POST /assignments/{assignment_id}/submit`
**Protected: STUDENT**
Request:
```json
{
  "submission_type": "FILE|TEXT",
  "file_url": "string or null",
  "text_answer": "string or null"
}
```
Validation:
- assignment must be `PUBLISHED`
- student must belong to the assignment class
- if deadline passed, set `is_late=true`
- if existing submission exists, mark old row `is_current=false`
- if `submission_type='FILE'`, require `file_url`
- if `submission_type='TEXT'`, require `text_answer`
Response HTTP 201:
```json
{
  "submission_id": "uuid",
  "submitted_at": "timestamp",
  "is_late": false,
  "version": 1,
  "receipt": "Submitted successfully at 10:45 AM on 25 Jun 2026"
}
```

### `GET /submissions/my`
**Protected: STUDENT**
Backend query filters WHERE is_current = true — only returns current submissions.
Response:
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

### `GET /assignments/{assignment_id}/submissions`
**Protected: ADMIN or MENTOR**
Note: Only returns `is_current=true` rows.
Response:
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

## Storage Endpoints

### `POST /storage/presigned-upload`
**Protected**
Request:
```json
{
  "file_name": "string",
  "file_type": "string",
  "upload_purpose": "ASSIGNMENT | SUBMISSION"
}
```
Response:
```json
{
  "upload_url": "string",
  "file_url": "string",
  "expires_in": 300
}
```

Rules:
- frontend uploads directly to S3 using `upload_url`
- frontend then sends `file_url` to backend in the related JSON payload

### `POST /storage/presigned-download`
**Protected: Any authenticated role**
Request:
```json
{ "file_url": "string" }
```
Backend:
- Extract S3 key from file_url
- Generate presigned GET URL: s3.generate_presigned_url('get_object', Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key}, ExpiresIn=300)
Response:
```json
{ "download_url": "string", "expires_in": 300 }
```
Errors:
- 400 if file_url is not a valid S3 URL for this bucket

## Analytics Endpoints

### `GET /analytics/admin/overview`
**Protected: ADMIN**
Response:
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

### `GET /analytics/classes/{class_id}`
**Protected: ADMIN or MENTOR**
Response:
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

### `GET /analytics/classes/{class_id}/students`
**Protected: ADMIN or MENTOR**
Response:
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

### `GET /analytics/students/{student_id}`
**Protected: ADMIN, MENTOR, or STUDENT (own only)**
Backend: If Student role, enforce student_id == JWT sub.
Backend query:
```sql
SELECT sa.*, c.class_name,
  (SELECT COALESCE(AVG(sa2.completion_rate), 0) FROM student_analytics sa2 WHERE sa2.class_id = sa.class_id) as class_avg_completion
FROM student_analytics sa
JOIN classes c ON c.id = sa.class_id
WHERE sa.student_id = :student_id
```
Assignment history query:
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
Response:
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

### `GET /analytics/risk/students?class_id={uuid}`
**Protected: ADMIN or MENTOR**
Backend query:
```sql
SELECT sa.student_id, u.full_name, sa.risk_level, sa.consecutive_misses, sa.completion_rate
FROM student_analytics sa
JOIN users u ON u.id = sa.student_id
WHERE sa.class_id = :class_id AND sa.risk_level IN ('HIGH','MEDIUM')
ORDER BY sa.risk_level DESC, sa.consecutive_misses DESC
```
Response:
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

### `GET /analytics/assignments/{assignment_id}`
**Protected: ADMIN or MENTOR**
Response:
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

## Notification Endpoints

**CRITICAL ROUTE ORDER:** In `routers/notifications.py`, define `PATCH /read-all` BEFORE `PATCH /{notification_id}/read`. FastAPI matches routes top-to-bottom; if `/{notification_id}/read` is defined first, a request to `/read-all` will be captured by it with `notification_id="read-all"` and return 404/403 instead of marking all as read.

### `GET /notifications`
**Protected**
Response:
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

### `PATCH /notifications/{notification_id}/read`
**Protected**
Backend: Verify notification.user_id == JWT sub → 403 otherwise.
Response HTTP 200:
```json
{ "is_read": true }
```

### `PATCH /notifications/read-all`
**Protected**
Backend: `UPDATE notifications SET is_read=true WHERE user_id=:user_id`
Response HTTP 200:
```json
{ "message": "All notifications marked as read" }
```

### `POST /notifications/reminder`
**Protected: STUDENT**
Request:
```json
{ "assignment_id": "uuid", "remind_at": "ISO8601 timestamp" }
```
Backend:
1. Verify assignment is PUBLISHED and student belongs to class
2. Verify remind_at is in the future
3. INSERT INTO reminder_jobs (user_id, assignment_id, remind_at, status='SCHEDULED')
4. APScheduler: add_job(send_student_reminder_job, 'date', run_date=remind_at, args=[reminder_job_id])
Response HTTP 201:
```json
{ "reminder_id": "uuid", "remind_at": "timestamp" }
```

## Export Endpoints

### `POST /exports/assignment-tracker`
**Protected: ADMIN or MENTOR**
Request:
```json
{ "assignment_id": "uuid" }
```
Backend:
1. Verify assignment.status == 'CLOSED' → 409 if not closed
2. Verify caller owns assignment's class
3. INSERT INTO export_jobs (requested_by, assignment_id, export_type='ASSIGNMENT_TRACKER', status='PENDING')
4. Launch background task: generate_export(export_job_id)
Response HTTP 202:
```json
{ "export_job_id": "uuid", "status": "PENDING" }
```

### `GET /exports/{export_job_id}`
**Protected**
Response:
```json
{
  "export_job_id": "uuid",
  "status": "PENDING|DONE|FAILED",
  "file_url": "string | null"
}
```

## AI Query Endpoints

### `POST /ai/query`
**Protected: ADMIN or MENTOR**
Request:
```json
{ "query_text": "string", "class_id": "uuid or null" }
```
Response:
```json
{
  "intent": "string",
  "query_text": "string",
  "result": {
    "type": "student_list | class_summary | student_profile | risk_list | count | no_data",
    "data": [],
    "message": "string"
  },
  "action_links": [
    { "label": "string", "route": "string" }
  ]
}
```

## WebSocket Endpoint

### `WSS /ws/tracker/{assignment_id}`
**Auth:** JWT passed as query param `?token=<access_token>` (not Authorization header)
**Protected: ADMIN or MENTOR with active membership in assignment's class**

Backend on connect:
1. Extract token from query param
2. Decode JWT — verify signature and expiry
3. Verify caller is ADMIN or MENTOR with active class membership for assignment's class
4. Add connection to in-memory channel map: `channels[assignment_id].add(websocket)`
5. Send initial ping: `{ "event": "connected", "assignment_id": "uuid" }`
On disconnect: remove from channel map.

**Event: `submission_created`** — broadcast when a student submits:
```json
{
  "event": "submission_created",
  "assignment_id": "uuid",
  "submitted_count": 0,
  "pending_count": 0,
  "missed_count": 0,
  "late_count": 0,
  "student": {
    "student_id": "uuid",
    "full_name": "string",
    "tracker_status": "SUBMITTED | LATE",
    "submitted_at": "ISO8601 timestamp",
    "is_late": false
  }
}
```

**Event: `tracker_refresh`** — broadcast after assignment close:
```json
{
  "event": "tracker_refresh",
  "assignment_id": "uuid",
  "status": "CLOSED",
  "submitted_count": 0,
  "pending_count": 0,
  "missed_count": 0,
  "late_count": 0
}
```

Backend manager in `websocket/tracker_ws.py`:
```python
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
```

Router registration in `main.py`: `app.include_router(ws_router)` — no prefix, registers at `/api/v1/ws/tracker/{assignment_id}`.

## Business Logic Rules

### Approval
- student account exists before approval
- student membership starts as `PENDING`
- mentor/admin approves or rejects from `/classes/{class_id}/approvals`
- approval creates notification and push

### Assignment publication
- publish creates notifications and reminder jobs
- if `deadline_at` is null, no deadline jobs are scheduled
- if `deadline_at` is set, schedule 24h and 2h reminders and close job

### Submission handling
- only one current submission per student per assignment
- every resubmission increments `version`
- `submitted_at` is the user action time
- `created_at` is row creation time
- `is_late` depends on deadline comparison

### Analytics
- recompute student analytics after approval, submission, close, and missed deadline job
- recompute class analytics after close and membership changes
- recompute assignment analytics after publish, submission, and close

### Risk engine
- use deterministic rule set only
- no ML
- update `student_analytics.risk_level` and `consecutive_misses`

### Bulk import
- process workbook sheets in this order: Classes, Mentors, Students
- keep per-row error log in `bulk_import_errors`
- allow partial success
- `bulk_import_batches.status` can be `UPLOADED`, `VALIDATING`, `PARTIAL`, `COMPLETED`, `FAILED`

## Query and Transaction Patterns

### Transactions required for:
- admin signup + OTP insert
- OTP verify + admin profile insert + token insert
- class create + class analytics insert
- student approval + analytics row create + notification insert
- student rejection + notification insert
- assignment publish + notification insert + reminder jobs insert + analytics insert
- submission insert + is_current toggle + analytics recompute log
- bulk import batch insert + per-row inserts + error inserts
- export request insert + file generation update

### Query style
- use SQLAlchemy ORM for most CRUD
- use explicit SQL or ORM joins for analytics-heavy endpoints
- use `selectinload` only when it keeps queries simple
- do not build giant service classes

## Error Response Standard
Use JSON errors in the same style everywhere:
```json
{ "detail": "message" }
```
Use proper HTTP codes:
- `400` validation error
- `401` authentication failed
- `403` authorization failed
- `404` not found
- `409` conflict
- `410` expired OTP
- `422` body validation issues
- `500` unexpected error

## No-Mismatch Rules
- Every route here must match the frontend file exactly.
- Every field here must be spelled exactly the same in the frontend file.
- Do not rename `registration_id`, `class_memberships.status`, `avg_submission_delay_hours`, `file_url`, `submitted_at`, or any enum.
- Do not add fields in responses unless the frontend file also expects them.
- Keep `snake_case` in API JSON.

## Final Implementation Checklist
- Add all routers in `main.py` with these exact prefixes:
  - auth_router → `/api/v1/auth`
  - class_router → `/api/v1/classes`
  - provision_router → `/api/v1/provision`
  - assignment_router → `/api/v1/assignments`
  - submission_router → `/api/v1` (registers `/api/v1/submissions/my` and `/api/v1/assignments/{id}/submit`)
  - storage_router → `/api/v1/storage`
  - analytics_router → `/api/v1/analytics`
  - notification_router → `/api/v1/notifications`
  - export_router → `/api/v1/exports`
  - ai_router → `/api/v1/ai`
  - ws_router → no prefix (registers at `/api/v1/ws/tracker/{assignment_id}`)
- Base URL: `https://assignhub-api.onrender.com/api/v1`
- Make `GET /health` public (registered at root, not under `/api/v1`).
- Protect all other endpoints correctly.
- Confirm CORS allows the Flutter app origin during development.
- Confirm JWT middleware applies before route handlers.
- Confirm DB migrations run cleanly from empty PostgreSQL.
- Confirm all joins used in `/auth/me`, analytics overview, tracker, and class detail are documented in the code.
