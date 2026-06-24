# FRONTEND_IMPLEMENTATION.md

## Implementation Goal
Build the Flutter mobile app exactly to the backend contract and master architecture. Use the exact same endpoint paths, field names, and enum values. No drift, no renamed fields, no alternate request shapes.

## Code Style Rules
- Keep widgets practical and readable.
- Use short names like `login`, `loadData`, `openGraph`, `saveForm`.
- Avoid over-engineered state patterns.
- Keep UI logic direct and normal for a hackathon project.
- Do not write code that looks auto-generated or overly uniform.
- Use some helper widgets, but do not over-factor simple UI.

## Repository Layout
Use the exact frontend structure from the master architecture.

```text
Frontend/
├── pubspec.yaml
├── pubspec.lock
├── android/
├── ios/
├── assets/
│   └── images/
└── lib/
    ├── main.dart
    ├── core/
    │   ├── api_client.dart
    │   ├── auth_storage.dart
    │   ├── ws_client.dart
    │   ├── router.dart
    │   ├── constants.dart
    │   └── exceptions.dart
    ├── models/
    │   ├── user_model.dart
    │   ├── class_model.dart
    │   ├── assignment_model.dart
    │   ├── submission_model.dart
    │   ├── analytics_model.dart
    │   ├── notification_model.dart
    │   └── ai_response_model.dart
    ├── providers/
    │   ├── auth_provider.dart
    │   ├── class_provider.dart
    │   ├── assignment_provider.dart
    │   ├── submission_provider.dart
    │   ├── analytics_provider.dart
    │   ├── notification_provider.dart
    │   └── ai_provider.dart
    ├── services/
    │   ├── auth_service.dart
    │   ├── class_service.dart
    │   ├── assignment_service.dart
    │   ├── submission_service.dart
    │   ├── analytics_service.dart
    │   ├── storage_service.dart
    │   ├── notification_service.dart
    │   ├── export_service.dart
    │   └── ai_service.dart
    ├── screens/
    │   ├── auth/
    │   │   ├── splash_screen.dart
    │   │   ├── login_screen.dart
    │   │   ├── admin_signup_screen.dart
    │   │   └── otp_verify_screen.dart
    │   ├── admin/
    │   │   ├── admin_dashboard_screen.dart
    │   │   ├── class_list_screen.dart
    │   │   ├── create_class_screen.dart
    │   │   ├── class_detail_screen.dart
    │   │   ├── class_students_screen.dart
    │   │   ├── approvals_screen.dart
    │   │   ├── student_profile_screen.dart
    │   │   ├── bulk_import_screen.dart
    │   │   ├── add_co_mentor_screen.dart
    │   │   ├── analytics_overview_screen.dart
    │   │   ├── class_analytics_drill_screen.dart
    │   │   └── ai_query_screen.dart
    │   ├── mentor/
    │   │   ├── mentor_dashboard_screen.dart
    │   │   ├── student_list_screen.dart
    │   │   ├── student_profile_screen.dart
    │   │   ├── approvals_screen.dart
    │   │   ├── assignment_list_screen.dart
    │   │   ├── create_assignment_screen.dart
    │   │   ├── assignment_tracker_screen.dart
    │   │   ├── submission_detail_screen.dart
    │   │   ├── analytics_screen.dart
    │   │   ├── risk_list_screen.dart
    │   │   ├── export_screen.dart
    │   │   └── ai_query_screen.dart
    │   └── student/
    │       ├── student_dashboard_screen.dart
    │       ├── assignment_list_screen.dart
    │       ├── assignment_detail_screen.dart
    │       ├── submit_assignment_screen.dart
    │       ├── submission_history_screen.dart
    │       ├── my_analytics_screen.dart
    │       └── notifications_screen.dart
    └── widgets/
        ├── risk_badge_widget.dart
        ├── tracker_card_widget.dart
        ├── analytics_chart_widget.dart
        ├── assignment_card_widget.dart
        ├── notification_tile_widget.dart
        ├── loading_widget.dart
        ├── error_widget.dart
        └── server_wakeup_widget.dart
```

## App Structure Rules
- Flutter Android-first.
- Use responsive layouts that still feel mobile-first.
- Keep all screens usable on a 360 px wide device.
- Use tab navigation only where the master architecture implies separate module groups.
- Use stack navigation inside each role module.
- Use modal bottom sheets for quick actions like filter, sort, and select class.

## Global Navigation

### App flow
1. `splash_screen.dart`
2. check secure storage for `access_token`
3. if present, call `GET /auth/me`
4. route based on `role`
5. if token missing or invalid, go to `login_screen.dart`

### Role navigation
- Admin: dashboard -> classes -> class detail -> approvals / students / assignments / analytics / ai
- Mentor: dashboard -> my classes -> class detail -> approvals / students / assignments / tracker / analytics / export / ai
- Student: dashboard -> assignments -> assignment detail -> submit assignment -> submission history -> analytics -> notifications

## Shared UI Rules
- Use the same loading, error, and empty states across screens.
- Every API-backed list must support empty state.
- Every graph must have title, subtitle, axis labels or category labels, and a short caption.
- Every graph must explain exactly what data it shows.
- Every analytics card must come from backend fields only, not local estimates.

## API Integration Layer

### `core/constants.dart`
Store one base URL constant.
- Base URL: `https://assignhub-api.onrender.com/api/v1`
- WebSocket base URL: `wss://assignhub-api.onrender.com/api/v1`
- Do not hardcode endpoint variants elsewhere.

### `core/api_client.dart`
Use Dio.
- Attach `Authorization: Bearer <access_token>` to all protected requests.
- On 401, call `POST /auth/refresh`.
- Retry one time after refresh.
- If refresh fails, clear storage and route to login.

### `core/auth_storage.dart`
Store:
- `access_token`
- `refresh_token`
- cached `role`
- cached `class_id`
- cached `class_name`
- cached `user_id`
- cached `full_name`

Do not store any renamed keys.

### `core/ws_client.dart`
Use it only for tracker updates.
- Connect after assignment tracker screen opens.
- Connection URL: `WSS <base_url>/ws/tracker/{assignment_id}?token=<access_token>`
- On connect: load initial tracker data via `GET /assignments/{assignment_id}/tracker` (REST), render full student list.
- Listen for submission events.
- Reconnect on disconnect with exponential backoff: 2s, 4s, 8s (max 3 attempts). After 3 failures show "Could not connect for live updates" — tracker still works via manual refresh.
- Show a small "Live updates paused" banner with Reconnect button if the socket drops.

WebSocket message handling:
- `submission_created`: find student row by `student.student_id`, update `tracker_status`, `submitted_at`, `is_late`, update summary count badges. No REST refetch needed.
- `tracker_refresh`: update summary counts from payload, refetch full student list via `GET /assignments/{assignment_id}/tracker`, show "Assignment closed" banner.
- `connected`: initial ping — no UI action needed.

## Models
Use model classes that map exactly to backend JSON.
- Do not rename `class_memberships.status` values in UI logic.
- Do not rename `avg_submission_delay_hours`.
- Do not rename `submitted_at`, `file_url`, `registration_id`, `rejection_reason`.

## Auth Screens

### `splash_screen.dart`
Purpose:
- wake server
- read tokens
- route user

UI:
- logo
- loading text
- small server wakeup message if backend is cold

Behavior:
- call `GET /health`
- if success, continue auth check
- if slow, show `server_wakeup_widget.dart` after 5 seconds

### `login_screen.dart`
Fields:
- `email`
- `password`
- `registration_id`
- optional `fcm_token`

UI:
- email input
- password input
- registration id input
- sign in button
- admin signup link

API call:
- `POST /auth/login`

Validation:
- email required and valid
- password required
- registration_id required for mentor and student; can be empty string for admin

Success:
- store tokens
- store user info
- route by role

Error:
- show exact backend error message from `detail`

### `admin_signup_screen.dart`
Fields:
- `full_name`
- `email`
- `password`

API:
- `POST /auth/admin/signup`

After success:
- navigate to `otp_verify_screen.dart`

### `otp_verify_screen.dart`
Fields:
- `email`
- `otp`

API:
- `POST /auth/admin/verify-otp`

Success:
- store tokens
- route to admin dashboard

## Screen Specifications

### Admin dashboard
File: `admin_dashboard_screen.dart`
Data from backend:
- `GET /analytics/admin/overview`
- `GET /notifications`
- `GET /classes`

UI:
- class summary cards
- high risk student summary
- completion rate summary
- recent notifications list
- quick action buttons

Graph rules:
- class comparison bar chart from `avg_completion`, `avg_miss_rate`, `high_risk_count`
- show `primary_mentor_name` on each class card
- chart caption must say what each bar means

### Class list
File: `class_list_screen.dart`
Data:
- `GET /classes`

UI:
- searchable list of classes
- class cards with student and mentor counts
- tap opens `class_detail_screen.dart`

### Create class
File: `create_class_screen.dart`
API:
- `POST /classes`

Fields:
- `class_name`
- `description`
- `academic_year`

### Class detail
File: `class_detail_screen.dart`
Data:
- `GET /classes/{class_id}`
- `GET /classes/{class_id}/students`
- `GET /classes/{class_id}/approvals`
- `GET /analytics/classes/{class_id}`

UI:
- class header
- mentor section
- student preview
- approvals shortcut
- analytics preview cards
- edit/archive actions

API actions:
- edit class -> `PATCH /classes/{class_id}`
- archive class -> `PATCH /classes/{class_id}` with `status: "ARCHIVED"`

### Class students
File: `class_students_screen.dart`
Data:
- `GET /classes/{class_id}/students`

UI:
- list of students
- each row shows `full_name`, `registration_id`, `membership_status`, `joined_at`, `risk_level`, `completion_rate`
- tap opens `student_profile_screen.dart`

### Approvals screen
File: `approvals_screen.dart`
Data:
- `GET /classes/{class_id}/approvals`

Buttons:
- approve -> `PATCH /classes/{class_id}/students/{student_id}/approve`
- reject -> `PATCH /classes/{class_id}/students/{student_id}/reject`

Loading states:
- show spinner per row while action is running

Success states:
- remove row from pending list
- toast confirmation
- use returned `student_id` to remove exact card

Error states:
- show backend `detail`

### Student profile
File: `student_profile_screen.dart`
Data:
- `GET /analytics/students/{student_id}`
- `GET /submissions/my` for student self view only

Note: Do NOT call `GET /notifications` here. That endpoint returns the currently logged-in user's own notifications (scoped by JWT), not the viewed student's notifications. For mentor/admin viewing a student, use the `assignment_history` array from `GET /analytics/students/{student_id}` to show activity timeline.

UI:
- profile header
- analytics summary cards
- timeline section
- recent submissions list

Graph rules:
- line or small bar chart for submission trend only if backend returns enough points
- explain whether it shows submitted count, missed count, or delay trend

### Bulk import
File: `bulk_import_screen.dart`
API:
- `GET /provision/bulk-import/template`
- `POST /provision/bulk-import`
- `GET /provision/bulk-import/{batch_id}`

UI:
- template download button
- file picker for XLSX only
- upload progress
- batch status panel
- error table by sheet and row

File rules:
- accept `.xlsx` only
- show clear size warning before upload
- block unsupported files

### Add co-mentor
File: `add_co_mentor_screen.dart`
API:
- `POST /classes/{class_id}/co-mentors`

Fields:
- `full_name`
- `email`

### Admin analytics overview
File: `analytics_overview_screen.dart`
Data:
- `GET /analytics/admin/overview`

UI:
- institution-level cards
- class comparison cards
- top risk classes
- quick drill-down links

Graph rules:
- a bar chart for class completion comparison
- a second small graph for miss rate or risk count
- each graph must use backend-supplied numbers only

### Class analytics drill
File: `class_analytics_drill_screen.dart`
Data:
- `GET /analytics/classes/{class_id}`
- `GET /analytics/classes/{class_id}/students`
- `GET /analytics/assignments/{assignment_id}`

UI:
- class summary
- assignment performance cards
- student breakdown list
- risk distribution chart if backend supplies grouped values

### Mentor dashboard
File: `mentor_dashboard_screen.dart`
Data:
- `GET /classes/my-classes`
- `GET /notifications`
- `GET /analytics/classes/{class_id}`

UI:
- my classes cards
- pending approvals shortcut
- assignment shortcuts
- recent alerts

### Mentor student list
File: `student_list_screen.dart`
Data:
- `GET /classes/{class_id}/students`

### Mentor approvals
File: `approvals_screen.dart`
Same behavior as admin approvals but only for mentor-owned classes.

### Assignment list
File: `assignment_list_screen.dart`
Data:
- `GET /assignments?class_id={class_id}`

UI:
- cards for draft, published, closed assignments
- filter by status

### Create assignment
File: `create_assignment_screen.dart`
API:
- `POST /assignments`
- `POST /storage/presigned-upload` if content or submission file is selected

Fields:
- `class_id`
- `title`
- `description`
- `content_type`
- `content_url`
- `rich_text_body`
- `submission_type`
- `deadline_at`
- `auto_close`

Rules:
- if `content_type='PDF'`, upload file first and use `file_url` from `POST /storage/presigned-upload` as `content_url`
- if `content_type='LINK'`, paste external URL into `content_url`
- if `content_type='RICH_TEXT'`, fill `rich_text_body`

### Assignment tracker
File: `assignment_tracker_screen.dart`
Data:
- `GET /assignments/{assignment_id}/tracker`
- WebSocket live updates

UI:
- status counters
- student table/list
- live update dot
- submission timestamps

Graph rules:
- if showing tracker chart, it should represent submitted vs pending vs missed vs late counts from backend
- label counts clearly

### Submission detail
File: `submission_detail_screen.dart`
Data:
- `GET /assignments/{assignment_id}/submissions`
- `GET /analytics/students/{student_id}` if needed

UI:
- submitted file/text content
- submitted time
- late flag
- version number

### Mentor analytics
File: `analytics_screen.dart`
Data:
- `GET /analytics/classes/{class_id}`
- `GET /analytics/classes/{class_id}/students`
- `GET /analytics/risk/students?class_id={class_id}`

### Risk list
File: `risk_list_screen.dart`
Data:
- `GET /analytics/risk/students?class_id={class_id}`

UI:
- cards for high risk and recovering students
- risk badges use `risk_level`

### Export
File: `export_screen.dart`
API:
- `POST /exports/assignment-tracker`
- `GET /exports/{export_job_id}`
- `POST /storage/presigned-download`

UI:
- export request button (format is always XLSX — no selector needed, backend defaults to XLSX)
- job status card
- download link when ready

Download flow:
- read `export_job_id` from POST response
- poll `GET /exports/{export_job_id}` every 3 seconds while status=PENDING
- when status=DONE, call `POST /storage/presigned-download` with `file_url`
- open returned `download_url`

### AI query
File: `ai_query_screen.dart`
API:
- `POST /ai/query`

UI:
- query input
- submit button
- result panel
- show `intent`, `query_text`, `result.type`, `result.message`, and action links

## Student Screens

### Student dashboard
File: `student_dashboard_screen.dart`
Data:
- `GET /assignments?class_id={class_id}`
- `GET /notifications`
- `GET /analytics/students/{student_id}`

Note: Do NOT call `GET /auth/me` here. The `user_id`, `class_id`, and `class_name` are already cached in `auth_storage.dart` after login (and after splash-screen restoration). Read them from secure storage directly. Only call `GET /auth/me` from `splash_screen.dart` for route restoration.

UI:
- active assignments summary
- missed or late summary
- notification list
- progress card

### Assignment list
File: `assignment_list_screen.dart`
Data:
- `GET /assignments?class_id={class_id}`

Rules:
- show only published assignments
- hide drafts and closed assignments unless backend explicitly returns them for student

### Assignment detail
File: `assignment_detail_screen.dart`
Data:
- `GET /assignments/{assignment_id}`

UI:
- title
- description
- content section
- submission status section
- set reminder button
- submit button

API actions:
- set reminder -> `POST /notifications/reminder`
  - on success (HTTP 201): read `remind_at` from response and show confirmation toast with the scheduled time; store `reminder_id` for future reference
- view content file -> `POST /storage/presigned-download`

### Submit assignment
File: `submit_assignment_screen.dart`
API:
- `POST /storage/presigned-upload` for file submissions
- direct upload to S3 using `upload_url`
- `POST /assignments/{assignment_id}/submit`

Rules:
- if `submission_type='FILE'`, ask for file picker and upload first
- if `submission_type='TEXT'`, show text area only
- if `submission_type='BOTH'`, let user choose either path if backend allows it
- send `file_url` in JSON payload after upload
- never send multipart body for submit

### Submission history
File: `submission_history_screen.dart`
Data:
- `GET /submissions/my`

### My analytics
File: `my_analytics_screen.dart`
Data:
- `GET /analytics/students/{student_id}`

Graph rules:
- show completion, missed, late, and streak trends if backend returns them
- each graph must have a one-line caption

### Notifications
File: `notifications_screen.dart`
Data:
- `GET /notifications`
- `PATCH /notifications/{notification_id}/read`
- `PATCH /notifications/read-all`

## State Management

### Global state
Store globally:
- auth user object
- access token state
- current role
- current class list for mentor/admin
- current notifications
- current network loading state
- active WebSocket tracker status

### Local screen state
Each screen keeps:
- form inputs
- selected filters
- loading spinner flags
- expanded card state
- current tab in screen only

## Validation Rules

### Auth
- email must be valid
- password required
- registration_id required for mentor/student login
- admin signup requires full name, email, password

### Class and approvals
- class_id must come from selected backend list
- approve/reject actions must use the exact `student_id` and `class_id`

### Assignments
- title required
- `content_type` must be one of `PDF`, `LINK`, `RICH_TEXT`
- `submission_type` must be one of `FILE`, `TEXT`, `BOTH`
- `deadline_at` must be ISO string or null

### Uploads
- only `.pdf` for assignment PDFs
- only allowed file types configured by app for submissions
- enforce size limit in UI before upload starts
- show progress while presigned upload is happening

## API Request Shapes
Use exactly these shapes.

### Login
```json
{
  "email": "string",
  "password": "string",
  "registration_id": "string",
  "fcm_token": "string"
}
```

### Create assignment
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

### Submit assignment
```json
{
  "submission_type": "FILE|TEXT",
  "file_url": "string or null",
  "text_answer": "string or null"
}
```

### Approve student
```json
{}
```

### Reject student
```json
{ "reason": "string" }
```

### Export request
```json
{ "assignment_id": "uuid" }
```

## Response Handling Rules
- Always read backend `detail` on error.
- On success, update local state immediately.
- After approve/reject, refresh approvals and class student list.
- After class edit/archive, refresh class detail and class list.
- After assignment publish, refresh assignment list and tracker.
- After submission, refresh submission history and assignment detail.
- After notification read, update notification badge count.
- After reminder creation, show scheduled time and confirmation toast.

## Graph and Analysis UI Rules
- Use simple charts, not flashy charts.
- Every chart must say what backend data it uses.
- Suggested chart types:
  - bar chart for class comparison
  - line chart for trend values
  - donut chart for status split when backend provides counts
- Do not compute business numbers locally if the backend already provides them.
- If backend data is missing, hide the chart instead of inventing values.

## Error and Empty States
- 401: redirect to login after token refresh fails
- 403: show permission denied card
- 404: show not found text tied to backend entity name
- empty list: show no data illustration or text
- network failure: retry button

## Files and 404 Safety
- Use the exact endpoint names from the backend file.
- Do not call non-existent paths.
- Do not rename screens in API logic.
- Keep route strings in one place if possible.
- Any route change must be updated in both frontend and backend implementation files before coding.

## Final Checklist
- Match every request and response field exactly.
- Use secure storage for tokens.
- Use Dio interceptor refresh flow.
- Use `/health` on startup.
- Use `GET /auth/me` for route restoration.
- Use `GET /classes/my-classes` for mentor class switching.
- Use `POST /storage/presigned-upload` before file upload flows.
- Use `POST /storage/presigned-download` before opening private files.
- Use `GET /assignments/{assignment_id}/tracker` plus WebSocket for live tracker.
- Use `POST /exports/assignment-tracker` to start export, read `export_job_id` from response, poll `GET /exports/{export_job_id}` every 3 seconds until status=DONE.
- Keep graphs purely backend-driven.
