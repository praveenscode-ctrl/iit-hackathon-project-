# AGENT_INSTRUCTIONS.md
**Project:** AssignHub — DevFusion 3.0, Problem Statement #26ENAH1
**Stack:** Flutter (Android APK) · FastAPI · PostgreSQL · AWS S3 · FCM · Brevo SMTP · Render
**Read this entire file before writing a single line of code. No exceptions.**

---

## 1. Mission Statement

Your job is to implement specific, scoped features as directed — nothing else.

You are not a scaffolding tool. You are not a boilerplate generator. You are not here to structure the project, auto-complete modules, or demonstrate best practices. You are here to write the exact piece of code that the implementation file specifies, in a way that looks like a developer who knows this codebase personally wrote it under time pressure.

This is a hackathon with active AI-detection by judges. They inspect GitHub commit history, naming patterns, code symmetry, abstraction depth, and comment uniformity. Any output that reads as machine-generated will cause immediate disqualification with no appeal. Every file you touch must pass as human-written. That is a hard constraint, not a suggestion.

The source of truth for every decision is, in order:
1. `MASTER_ARCHITECTURE.txt` — routes, fields, enums, DB schema, flows
2. `BACKEND_IMPLEMENTATION.md` — backend-specific rules, endpoint specs, logic steps
3. `FRONTEND_IMPLEMENTATION.md` — Flutter screen specs, API call patterns, UI rules
4. This file — coding style and behavior rules

Never invent, infer, or expand beyond what those files specify.

---

## 2. What You Are and Are NOT Allowed to Do

### Allowed
- Implement a single function, method, or logic block when explicitly told to
- Fix a specific error when given the exact error message, file name, and line context
- Adjust a single widget's styling, label, or padding when explicitly instructed
- Write one endpoint at a time when told which endpoint to build next
- Translate a specific spec step into code (e.g. "implement the login flow from step 1 to step 14 in Section 4.3")
- Ask a clarifying question if the spec is genuinely ambiguous — one question, not five

### Never Allowed
- Generate a full screen, full router file, full service module, or full model file in one pass
- Use any boilerplate template or starter pattern as a base, even "just to get started"
- Refactor or restructure existing code unless a specific reported bug requires it and you are told to fix it
- Auto-complete logic that is not specified in the implementation files — if the spec doesn't say it, don't add it
- Add extra error handling, logging, or validation beyond what the spec defines
- Create helper utilities, abstract classes, or shared modules that weren't in the architecture
- Rename any field, route, enum value, or table — even if you think a different name is cleaner
- Generate tests, fixtures, seed data, or documentation unless explicitly asked

---

## 3. Code Style Rules — Human-Written Appearance

This section is mandatory. Every file you write must follow these rules. Judges are specifically looking for violations.

### 3.1 Naming Conventions

**Backend (Python/FastAPI):**
- Functions: short, action-first, slightly informal — `get_user`, `make_token`, `calc_risk`, `save_submission`, `load_class_data`, `check_membership`
- Never: `fetchUserDataFromRepositoryAndReturnFormattedResponse`, `executeStudentAnalyticsRecomputationPipeline`
- Variables: `user`, `token`, `cls`, `membership`, `result`, `payload` — not `currentUserObject`, `authenticatedUserRecord`
- Classes: domain-plain — `User`, `ClassMembership`, `SubmissionSchema` — not `AbstractUserRepositoryFactory`, `BaseAuthenticationHandlerMixin`
- File names: `snake_case` — already defined by the folder structure, do not deviate

**Frontend (Flutter/Dart):**
- Functions: `login`, `loadData`, `openGraph`, `saveForm`, `submitAssignment`, `fetchClasses` — not `performUserAuthenticationAndNavigateToRoleBasedDashboard`
- Variables: `token`, `user`, `cls`, `assignment`, `sub` — not `currentlyAuthenticatedUserObject`
- Widget methods: `build`, `_buildHeader`, `_buildStudentRow`, `_onTap` — short and lowercase-prefixed for private
- File names: `camelCase` — already defined by the folder structure, do not deviate

**Never produce names that are so descriptive they read like documentation.** A developer under deadline names things for speed and context, not for a stranger reading the code cold.

### 3.2 Function and Method Length

- Target 10–30 lines per function for most logic
- A 40-line function is fine if the logic genuinely needs it — don't split it for the sake of splitting
- Never break a straightforward 15-line function into 4 micro-functions with single-line bodies
- Never chain 6 helper calls when a direct block of code is clearer
- Deeply nested helper hierarchies are a primary AI detection signal — avoid them

### 3.3 Comments

- Comment non-obvious logic only — not every line, not zero lines
- Style: brief, lowercase, plain English
  - Good: `# expired token — force re-login`, `# only approved students can log in`, `# late if deadline already passed`
  - Bad: `# This function handles the case where the JWT access token has expired and needs to be refreshed using the stored refresh token`
- Never add docstrings to every function with identical structure — that pattern is an immediate detection flag
- Add a comment when you'd ask a teammate "wait, why does it do this?" — not when the code already answers it
- Vary comment density naturally: some functions have 2–3 comments, some have none

### 3.4 Error Handling

- Do not copy-paste identical try/except or try/catch blocks across every single handler — vary the structure slightly
- Not every function needs error handling — only the ones where failure is genuinely possible and consequential
- Use the error codes defined in the implementation files exactly: `400`, `401`, `403`, `404`, `409`, `410`, `422`, `500`
- Error messages must match what the master architecture specifies word-for-word where defined

### 3.5 Code Symmetry — The Primary Detection Risk

Judges specifically look for this: every function following the exact same structural template, every handler shaped identically, every class laid out with the same sections in the same order.

You must actively vary:
- Where you declare variables (top of function vs inline vs as-needed)
- Whether you use early returns or a single return path — mix them
- How you format conditionals — sometimes `if not x: raise`, sometimes `if x is None: return default`
- Whether you write `result = query.first()` then check it, or chain it
- Comment placement — top of function sometimes, inline sometimes, sometimes none

This is not about being sloppy. It is about being human. Write each function as if you came back to it after working on something else.

### 3.6 Import Style

**Backend:** Group imports naturally — stdlib, then third-party, then local — but don't be obsessive about sorting every line. A developer working fast will sometimes leave an import slightly out of order.

**Frontend:** Don't import every package at the top of every file in perfect alphabetical order. Import what you use, in the order you reach for it.

---

## 4. Patterns to Actively Avoid

These are the exact patterns judges use to identify AI-generated code. Never produce them.

- **Perfect structural symmetry** — every route handler, every widget build method, every service function following the exact same shape
- **Exhaustive docstrings** — a docstring on every single function, all formatted identically with Args/Returns/Raises sections
- **Identical error handling everywhere** — the same try/except with the same log + raise pattern on every endpoint
- **Over-abstracted service layers** — a `BaseService` with `AbstractRepository` injected via a `ProviderFactory` for what is essentially a 4-table CRUD app
- **Excessive chaining** — `db.query(User).filter(User.email == email).options(selectinload(User.memberships)).with_for_update().first()` when `db.query(User).filter_by(email=email).first()` is enough
- **Mechanical variable names** — `userDataObject`, `classInformationResponse`, `studentAnalyticsResultPayload`
- **Uniform spacing and blank-line placement** — two blank lines before every function, one blank line between every logical block, without variation
- **Boilerplate class structure** — `__init__`, `__repr__`, `__str__`, `__eq__` defined on every model when only `__init__` is needed
- **Over-commented obvious code** — `# Create the user object`, `# Save to database`, `# Return the response`
- **Perfectly alphabetized everything** — routes, imports, fields, all sorted when a developer would just append to the end

---

## 5. Implementation Pace Rules

- Implement **one unit at a time**: one endpoint, one screen, one model, one service function
- Stop after each unit and wait for confirmation before moving to the next
- Never implement an entire router file, screen file, or service layer in a single output
- If a spec step says "insert X, then insert Y, then send email" — implement that exact sequence, not a generalised version of it
- If something is not specified in the implementation files, do not implement it — ask instead
- Never pre-emptively implement error cases, edge cases, or validation beyond what the spec defines

---

## 6. Field and Endpoint Contract Rules

These are non-negotiable. Getting these wrong causes 404 errors and body-shape crashes at runtime.

- Every route path must match `MASTER_ARCHITECTURE.txt` exactly — including pluralization, nesting, and query params
- Every JSON field name must be `snake_case` and match the master architecture exactly — `export_job_id` not `job_id`, `upload_purpose` not `folder`, `membership_status` not `status`, `student_id` not `id`
- Every enum value must be uppercase and match exactly — `PENDING_OTP`, `BULK_IMPORT`, `RICH_TEXT`, `RECOVERING` — not lowercased, not renamed
- Every ID field is a `String` UUID — never `int`, never `num`
- Timestamps are ISO 8601 with timezone: `"2026-06-25T10:00:00Z"` — never bare date strings
- Nullable fields are always included in the response as `null` — never omitted
- The `student_submission` key is always present in `GET /assignments/{assignment_id}` for all roles
- `GET /notifications` returns the JWT user's own notifications only — never use it to show another user's notifications
- WebSocket auth is via query param `?token=<access_token>` — not Authorization header
- File submissions are always `application/json` — never `multipart/form-data` to the FastAPI submit endpoint

**Router prefix table — backend `main.py` must register exactly these:**

| Router | Prefix |
|---|---|
| auth_router | `/api/v1/auth` |
| class_router | `/api/v1/classes` |
| provision_router | `/api/v1/provision` |
| assignment_router | `/api/v1/assignments` |
| submission_router | `/api/v1` |
| storage_router | `/api/v1/storage` |
| analytics_router | `/api/v1/analytics` |
| notification_router | `/api/v1/notifications` |
| export_router | `/api/v1/exports` |
| ai_router | `/api/v1/ai` |
| ws_router | *(no prefix — registers at `/api/v1/ws/tracker/{assignment_id}`)* |

`GET /health` is registered at root — **not** under `/api/v1`.

---

## 7. Backend-Specific Rules

- In `routers/notifications.py`: define `PATCH /read-all` **before** `PATCH /{notification_id}/read` — FastAPI resolves top-to-bottom and `read-all` will be swallowed by the path param route if ordered wrong
- `POST /classes/{class_id}/co-mentors`: auto-generate the password and `registration_id` on the backend — do not ask the caller for a password
- WebSocket `broadcast()` in `websocket/tracker_ws.py`: wrap each `send_json` in try/except, collect dead connections in a list, remove them after the loop — do not iterate and mutate in the same loop
- Analytics rows must be created immediately on these events — not lazily:
  - Class created → insert `class_analytics`
  - Student approved → insert `student_analytics`
  - Assignment published → insert `assignment_analytics`
- `users.status` controls account validity; `class_memberships.status` controls class access — these are separate and must not be conflated in login logic
- Student login must be blocked when `class_memberships.status = PENDING` — return `403` with the message from the architecture, not a generic error

---

## 8. Frontend-Specific Rules

- `GET /auth/me` is called only from `splash_screen.dart` for route restoration — not from individual screens
- `student_dashboard_screen.dart` reads `user_id`, `class_id`, `class_name` from `auth_storage.dart` (cached at login) — it does not call `GET /auth/me`
- `student_profile_screen.dart` does not call `GET /notifications` — that returns the logged-in user's notifications, not the viewed student's. Use `assignment_history` from `GET /analytics/students/{student_id}` for activity display
- Never send multipart form data to `POST /assignments/{assignment_id}/submit` — always JSON
- S3 file upload flow in order: `POST /storage/presigned-upload` → HTTP PUT to `upload_url` → use returned `file_url` in JSON body — never skip or reorder steps
- Export poll flow: `POST /exports/assignment-tracker` → read `export_job_id` from response → poll `GET /exports/{export_job_id}` every 3 seconds → on `status=DONE` call `POST /storage/presigned-download` with `file_url` → open `download_url`
- WebSocket tracker: on `submission_created` event, update the matching student row in the local list by `student.student_id` — do not refetch the full list
- On `tracker_refresh` event: update summary counts from payload, then refetch via `GET /assignments/{assignment_id}/tracker`
- Reconnect backoff: 2s, 4s, 8s — max 3 attempts — then show "Could not connect for live updates" static message

---

## 9. Payment Integration Rule

This project does not currently include payments. If any payment feature is added:

- Use sandbox/test mode only — Razorpay Test Mode, Stripe Test Mode, PayU Sandbox, or equivalent
- Use only the test card numbers and dummy UPI IDs provided by the payment gateway's documentation
- Never write or commit live transaction code under any circumstances — this is a disqualification trigger independent of the AI-detection rules

---

## 10. Deployment Requirements

- No `localhost` URLs in any production config file or constants file
- Flutter `core/constants.dart` base URL must be: `https://assignhub-api.onrender.com/api/v1`
- Flutter WebSocket base URL must be: `wss://assignhub-api.onrender.com/api/v1`
- Flutter build target is Android APK: `flutter build apk --release` from the `Frontend/` directory
- FastAPI must have a `Procfile` or Render-compatible start command — not just a local `uvicorn main:app` note
- APScheduler must use `SQLAlchemyJobStore` with `DATABASE_URL` — not the in-memory default — so jobs survive server restarts on Render

---

## 11. Commit Message Style

If you assist with or suggest commit messages, use this style:

- Short, lowercase, past-tense, plain English
- Good: `added login endpoint`, `fixed token refresh bug`, `wired up tracker websocket`, `updated risk badge color`
- Never: `feat: implement comprehensive JWT authentication system with refresh token rotation and role-based access control`
- Never use conventional commits format (`feat:`, `fix:`, `chore:`, `refactor:`) — judges flag it as AI-generated workflow

---

## 12. Final Compliance Checklist

Run this check internally before outputting any code block. If any answer is wrong, revise before sending.

- [ ] Does this code look like a developer wrote it under deadline pressure — not a machine generating it cleanly?
- [ ] Are all variable and function names practical and slightly informal, not descriptive-to-the-point-of-mechanical?
- [ ] Am I implementing only what the specification says — nothing more, nothing inferred?
- [ ] Is there any boilerplate, template pattern, scaffolding, or auto-generated structure in this output? (If yes, strip it)
- [ ] Are comments natural and sparse — non-obvious logic only, brief, varied in density?
- [ ] Is this one focused unit of work — one endpoint, one screen, one function — not a full module?
- [ ] Do all field names, route paths, and enum values exactly match `MASTER_ARCHITECTURE.txt`?
- [ ] Are there any perfectly symmetrical code blocks across multiple functions that would flag as generated? (If yes, vary them)
- [ ] Is every ID field a `String` UUID, not an `int`?
- [ ] Are nullable response fields included as `null` — not omitted?
- [ ] Is the notification router ordered with `read-all` before `/{notification_id}/read`?
- [ ] Does the WebSocket broadcast handle dead connections with try/except and post-loop removal?
- [ ] Is `GET /auth/me` only called from the splash screen, nowhere else?
- [ ] Is the base URL pointing to the Render deployment, not localhost?

If all boxes pass, output the code. If any fail, fix first.

---

*This file is binding for every AI agent working on this project. Last updated before implementation begins. Do not modify without team agreement.*
