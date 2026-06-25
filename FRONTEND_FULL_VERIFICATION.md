# AssignHub — Full Frontend Verification Suite
**Purpose:** End-to-end verification that the Flutter frontend matches the backend contract, master architecture, and frontend implementation spec with zero mismatch.  
**Who runs this:** Developer after the AI editor claims frontend is complete.  
**Critical rule:** Every screen must show real data from the backend. No mock values. No hardcoded strings.

---

## How to Use This File

```
Section 1  — File & Folder Structure
Section 2  — Core Layer (api_client, auth_storage, ws_client, router, constants)
Section 3  — Model Field Contract (exact field names matching backend JSON)
Section 4  — Auth Screens
Section 5  — Admin Screens
Section 6  — Mentor Screens
Section 7  — Student Screens
Section 8  — Widget Verification
Section 9  — API Call Contract (every endpoint called correctly)
Section 10 — WebSocket Verification
Section 11 — S3 Upload/Download Flow
Section 12 — Analytics Display Verification
Section 13 — AI Query Screen
Section 14 — Export Flow
Section 15 — RBAC & Navigation Guards
Section 16 — Error & Empty State Handling
Section 17 — Critical Mismatch Checklist (most common AI-generated frontend bugs)
```

---

## Section 1 — File & Folder Structure

### 1.1 Manual Check — All Files Must Exist

Run from `Frontend/`:
```bash
find lib/ -name "*.dart" | sort
```

**Expected — every file must exist:**
```
lib/main.dart
lib/core/api_client.dart
lib/core/auth_storage.dart
lib/core/constants.dart
lib/core/exceptions.dart
lib/core/router.dart
lib/core/ws_client.dart
lib/models/ai_response_model.dart
lib/models/analytics_model.dart
lib/models/assignment_model.dart
lib/models/class_model.dart
lib/models/notification_model.dart
lib/models/submission_model.dart
lib/models/user_model.dart
lib/providers/ai_provider.dart
lib/providers/analytics_provider.dart
lib/providers/assignment_provider.dart
lib/providers/auth_provider.dart
lib/providers/class_provider.dart
lib/providers/notification_provider.dart
lib/providers/submission_provider.dart
lib/screens/admin/add_co_mentor_screen.dart
lib/screens/admin/admin_dashboard_screen.dart
lib/screens/admin/ai_query_screen.dart
lib/screens/admin/analytics_overview_screen.dart
lib/screens/admin/approvals_screen.dart
lib/screens/admin/bulk_import_screen.dart
lib/screens/admin/class_analytics_drill_screen.dart
lib/screens/admin/class_detail_screen.dart
lib/screens/admin/class_list_screen.dart
lib/screens/admin/class_students_screen.dart
lib/screens/admin/create_class_screen.dart
lib/screens/admin/student_profile_screen.dart
lib/screens/auth/admin_signup_screen.dart
lib/screens/auth/login_screen.dart
lib/screens/auth/otp_verify_screen.dart
lib/screens/auth/splash_screen.dart
lib/screens/mentor/ai_query_screen.dart
lib/screens/mentor/analytics_screen.dart
lib/screens/mentor/approvals_screen.dart
lib/screens/mentor/assignment_list_screen.dart
lib/screens/mentor/assignment_tracker_screen.dart
lib/screens/mentor/create_assignment_screen.dart
lib/screens/mentor/export_screen.dart
lib/screens/mentor/mentor_dashboard_screen.dart
lib/screens/mentor/risk_list_screen.dart
lib/screens/mentor/student_list_screen.dart
lib/screens/mentor/student_profile_screen.dart
lib/screens/mentor/submission_detail_screen.dart
lib/screens/student/assignment_detail_screen.dart
lib/screens/student/assignment_list_screen.dart
lib/screens/student/my_analytics_screen.dart
lib/screens/student/notifications_screen.dart
lib/screens/student/student_dashboard_screen.dart
lib/screens/student/submission_history_screen.dart
lib/screens/student/submit_assignment_screen.dart
lib/widgets/ai_response_model.dart
lib/widgets/analytics_chart_widget.dart
lib/widgets/assignment_card_widget.dart
lib/widgets/error_widget.dart
lib/widgets/loading_widget.dart
lib/widgets/notification_tile_widget.dart
lib/widgets/risk_badge_widget.dart
lib/widgets/server_wakeup_widget.dart
lib/widgets/tracker_card_widget.dart
```

**PASS condition:** Every file exists. Zero missing files.

### 1.2 pubspec.yaml Required Dependencies

```bash
cat pubspec.yaml | grep -E "dio|flutter_secure_storage|go_router|web_socket_channel|file_picker|open_file|riverpod|fl_chart|intl"
```

**Expected packages (must be present):**
```yaml
dio:                      # HTTP client with interceptors
flutter_secure_storage:   # Token storage
go_router:                # Navigation
web_socket_channel:       # WebSocket tracker
file_picker:              # File uploads
riverpod: OR provider:    # State management
fl_chart: OR syncfusion_flutter_charts:  # Analytics charts
intl:                     # Date formatting
open_file: OR url_launcher:  # Opening download URLs
```

**PASS condition:** All packages present in pubspec.yaml and pubspec.lock.

---

## Section 2 — Core Layer Verification

### 2.1 constants.dart — Base URL Must Be Exact

```bash
grep -n "kBaseUrl\|kWsUrl\|onrender\|api/v1" lib/core/constants.dart
```

**Expected:**
```dart
const String kBaseUrl = "https://assignhub-api.onrender.com/api/v1";
const String kWsUrl   = "wss://assignhub-api.onrender.com/api/v1";
```

**FAIL conditions:**
- URL contains trailing slash: `https://assignhub-api.onrender.com/api/v1/` ← causes double-slash in all requests
- URL missing `/api/v1` ← all endpoints will 404
- URL is `http://` not `https://` ← CORS + security fail on device
- WebSocket URL is `ws://` not `wss://` ← SSL required by Render
- Hardcoded `localhost` anywhere in constants

### 2.2 api_client.dart — Interceptor Verification

```bash
grep -n "401\|refresh\|Authorization\|Bearer\|retry\|interceptor" lib/core/api_client.dart
```

**Verify these behaviors are implemented:**

| Behavior | Must find in code |
|---|---|
| Auth header attached to all requests | `Authorization: Bearer` in interceptor |
| 401 triggers refresh call | `401` check → `POST /auth/refresh` call |
| Retry original request after refresh | request retry after new token |
| On refresh fail → clear storage → login | clear token + navigate to login |
| Base URL from constants | `kBaseUrl` reference, not hardcoded string |

**FAIL conditions:**
```
❌ auth token added per-service instead of in interceptor (missed calls)
❌ 401 handled by showing error instead of refreshing
❌ Base URL hardcoded in api_client.dart instead of using kBaseUrl
❌ No retry after token refresh (second call with new token missing)
```

### 2.3 auth_storage.dart — All 7 Keys Must Be Stored

```bash
grep -n "access_token\|refresh_token\|class_id\|class_name\|user_id\|full_name\|role" lib/core/auth_storage.dart
```

**Expected — all 7 keys present:**
```dart
static const _accessToken  = 'access_token';
static const _refreshToken = 'refresh_token';
static const _role         = 'role';
static const _classId      = 'class_id';
static const _className    = 'class_name';
static const _userId       = 'user_id';
static const _fullName     = 'full_name';
```

**FAIL conditions:**
```
❌ class_id not stored → student/mentor dashboard breaks on app restart
❌ role not stored → routing on restart fails
❌ user_id not stored → student analytics call has no student_id
❌ Using SharedPreferences instead of flutter_secure_storage (security)
```

### 2.4 ws_client.dart — WebSocket Behavior

```bash
grep -n "wss://\|tracker\|token=\|submission_created\|tracker_refresh\|connected\|backoff\|reconnect" lib/core/ws_client.dart
```

**Verify:**

| Behavior | Must find |
|---|---|
| Connection URL includes token as query param | `?token=` in URL construction |
| URL uses `kWsUrl` constant | `kWsUrl` reference |
| `submission_created` event handled | case/if block for `submission_created` |
| `tracker_refresh` event handled | case/if block for `tracker_refresh` |
| `connected` event handled | no UI action needed but handled |
| Exponential backoff: 2s, 4s, 8s | delay values 2000, 4000, 8000 or similar |
| Max 3 reconnect attempts | counter capped at 3 |
| "Live updates paused" banner on disconnect | disconnect handler shows message |
| Initial tracker data via REST not WS | GET tracker call on connect |

**FAIL conditions:**
```
❌ Token in Authorization header instead of ?token= query param
❌ WS URL hardcoded instead of using kWsUrl
❌ No reconnect logic → tracker goes dark silently
❌ Using WebSocket instead of web_socket_channel package
```

### 2.5 router.dart — Role Guards

```bash
grep -n "redirect\|role\|ADMIN\|MENTOR\|STUDENT\|GoRouter\|GoRoute" lib/core/router.dart
```

**Verify:**

| Guard | Must be implemented |
|---|---|
| Unauthenticated → /login | redirect when no token |
| Role=ADMIN → admin routes only | admin dashboard route |
| Role=MENTOR → mentor routes only | mentor dashboard route |
| Role=STUDENT → student routes only | student dashboard route |
| Deep link to wrong role → redirect | cross-role protection |

---

## Section 3 — Model Field Contract (Frontend ↔ Backend)

This section verifies that every Dart model field name exactly matches the backend JSON field name.

### 3.1 UserModel

```bash
grep -n "fromJson\|full_name\|class_id\|class_name\|registration_id\|fcm_token" lib/models/user_model.dart
```

**Expected field mapping:**
```dart
// JSON key          → Dart field
"id"                → id
"full_name"         → fullName      (fromJson: json['full_name'])
"email"             → email
"role"              → role
"class_id"          → classId       (fromJson: json['class_id'])  ← CRITICAL
"class_name"        → className     (fromJson: json['class_name']) ← CRITICAL
"registration_id"   → registrationId (fromJson: json['registration_id'])
"status"            → status
```

**FAIL conditions:**
```
❌ json['classId'] instead of json['class_id']    → always null, routing breaks
❌ json['className'] instead of json['class_name'] → always null
❌ json['registrationId'] instead of json['registration_id'] → login blocks mentor/student
❌ json['fullName'] instead of json['full_name']   → name never displays
```

### 3.2 ClassModel

```bash
grep -n "fromJson\|class_name\|student_count\|mentor_count\|academic_year" lib/models/class_model.dart
```

**Expected mapping:**
```dart
"class_name"     → className    (fromJson: json['class_name'])
"student_count"  → studentCount (fromJson: json['student_count'])
"mentor_count"   → mentorCount  (fromJson: json['mentor_count'])
"academic_year"  → academicYear (fromJson: json['academic_year'])
"created_at"     → createdAt    (fromJson: json['created_at'])
// In detail response:
"primary_mentor" → primaryMentor
"co_mentors"     → coMentors    (fromJson: json['co_mentors'])
"is_primary_mentor" → isPrimaryMentor (fromJson: json['is_primary_mentor'])
```

### 3.3 AssignmentModel

```bash
grep -n "fromJson\|content_type\|submission_type\|deadline_at\|rich_text_body\|created_by_name\|student_submission" lib/models/assignment_model.dart
```

**Expected mapping:**
```dart
"content_type"    → contentType    (fromJson: json['content_type'])
"submission_type" → submissionType (fromJson: json['submission_type'])
"deadline_at"     → deadlineAt     (fromJson: json['deadline_at']) ← parse as DateTime?
"rich_text_body"  → richTextBody   (fromJson: json['rich_text_body'])
"content_url"     → contentUrl     (fromJson: json['content_url'])
"created_by_name" → createdByName  (fromJson: json['created_by_name']) ← CRITICAL
"class_id"        → classId        (fromJson: json['class_id'])
"student_submission" → studentSubmission (fromJson: json['student_submission'])
```

**StudentSubmissionInfo model (nested):**
```dart
"submitted"    → submitted
"submission_id" → submissionId (fromJson: json['submission_id'])
"submitted_at" → submittedAt  (fromJson: json['submitted_at'])
"is_late"      → isLate       (fromJson: json['is_late'])
"version"      → version
```

**FAIL conditions:**
```
❌ json['submissionType'] → always null, FILE/TEXT selector breaks
❌ json['deadlineAt'] instead of json['deadline_at'] → deadline never shows
❌ Missing 'student_submission' key handling → crash on null access
❌ 'created_by_name' not parsed → assignment list shows empty creator name
```

### 3.4 SubmissionModel

```bash
grep -n "fromJson\|submission_id\|assignment_title\|submitted_at\|is_late\|text_answer\|file_url\|student_name" lib/models/submission_model.dart
```

**Expected mapping:**
```dart
// GET /submissions/my response:
"submission_id"    → submissionId    (fromJson: json['submission_id'])  ← NOT 'id'
"assignment_id"    → assignmentId    (fromJson: json['assignment_id'])
"assignment_title" → assignmentTitle (fromJson: json['assignment_title'])
"submission_type"  → submissionType  (fromJson: json['submission_type'])
"submitted_at"     → submittedAt     (fromJson: json['submitted_at'])
"is_late"          → isLate          (fromJson: json['is_late'])
"version"          → version

// GET /assignments/{id}/submissions response (mentor view):
"student_id"   → studentId   (fromJson: json['student_id'])
"student_name" → studentName (fromJson: json['student_name'])
"file_url"     → fileUrl     (fromJson: json['file_url'])
"text_answer"  → textAnswer  (fromJson: json['text_answer'])
```

**FAIL condition:**
```
❌ Using json['id'] instead of json['submission_id'] → submission list empty
```

### 3.5 StudentAnalyticsModel

```bash
grep -n "fromJson\|total_assigned\|total_submitted\|total_missed\|total_late\|completion_rate\|current_streak\|longest_streak\|avg_submission_delay_hours\|risk_level\|consecutive_misses\|class_avg_completion\|assignment_history" lib/models/analytics_model.dart
```

**Expected mapping (ALL fields must be parsed):**
```dart
"student_id"                  → studentId
"full_name"                   → fullName             (json['full_name'])
"class_name"                  → className            (json['class_name'])
"total_assigned"              → totalAssigned         (json['total_assigned'])
"total_submitted"             → totalSubmitted        (json['total_submitted'])
"total_missed"                → totalMissed           (json['total_missed'])
"total_late"                  → totalLate             (json['total_late'])
"completion_rate"             → completionRate        (json['completion_rate'])
"current_streak"              → currentStreak         (json['current_streak'])
"longest_streak"              → longestStreak         (json['longest_streak'])
"avg_submission_delay_hours"  → avgSubmissionDelayHours (json['avg_submission_delay_hours'])
"risk_level"                  → riskLevel             (json['risk_level'])
"consecutive_misses"          → consecutiveMisses     (json['consecutive_misses'])
"class_avg_completion"        → classAvgCompletion    (json['class_avg_completion'])
"assignment_history"          → assignmentHistory     (json['assignment_history'])
```

**AssignmentHistoryItem mapping:**
```dart
"assignment_id"  → assignmentId  (json['assignment_id'])
"title"          → title
"deadline_at"    → deadlineAt    (json['deadline_at'])
"tracker_status" → trackerStatus (json['tracker_status'])
"submitted_at"   → submittedAt   (json['submitted_at'])
"is_late"        → isLate        (json['is_late'])
```

**ClassAnalyticsModel mapping:**
```dart
"class_id"              → classId
"class_name"            → className              (json['class_name'])
"total_students"        → totalStudents          (json['total_students'])
"total_assignments"     → totalAssignments       (json['total_assignments'])
"avg_completion"        → avgCompletion          (json['avg_completion'])
"avg_miss_rate"         → avgMissRate            (json['avg_miss_rate'])
"avg_late_rate"         → avgLateRate            (json['avg_late_rate'])
"high_risk_count"       → highRiskCount          (json['high_risk_count'])
"bottleneck_assignments"→ bottleneckAssignments  (json['bottleneck_assignments'])
"risk_distribution"     → riskDistribution       (json['risk_distribution'])
```

**AdminOverviewModel mapping:**
```dart
"total_classes"    → totalClasses    (json['total_classes'])
"total_mentors"    → totalMentors    (json['total_mentors'])
"total_students"   → totalStudents   (json['total_students'])
"total_assignments"→ totalAssignments (json['total_assignments'])
"classes"          → classes
// Per class:
"class_id"              → classId
"primary_mentor_name"   → primaryMentorName (json['primary_mentor_name']) ← CRITICAL
"avg_completion"        → avgCompletion
"avg_miss_rate"         → avgMissRate
"high_risk_count"       → highRiskCount
"student_count"         → studentCount
```

### 3.6 ClassStudentsModel (Students List)

```bash
grep -n "membership_status\|joined_at\|joined_via\|completion_rate\|risk_level" lib/models/class_model.dart
```

**Expected mapping (from `GET /classes/{id}/students`):**
```dart
"id"                → id
"full_name"         → fullName          (json['full_name'])
"email"             → email
"registration_id"   → registrationId    (json['registration_id'])
"membership_status" → membershipStatus  (json['membership_status'])  ← NOT 'status'
"risk_level"        → riskLevel         (json['risk_level'])
"completion_rate"   → completionRate    (json['completion_rate'])
"joined_via"        → joinedVia         (json['joined_via'])
"joined_at"         → joinedAt          (json['joined_at'])
```

**FAIL condition:**
```
❌ json['status'] instead of json['membership_status'] → always null, filter breaks
```

### 3.7 ApprovalsModel

```bash
grep -n "pending_count\|student_id\|requested_at\|joined_via" lib/models/class_model.dart
```

**Expected mapping (from `GET /classes/{id}/approvals`):**
```dart
"pending_count" → pendingCount (json['pending_count'])
"pending"       → pending      (list)
// Per pending student:
"student_id"   → studentId    (json['student_id'])  ← NOT 'id'
"full_name"    → fullName      (json['full_name'])
"email"        → email
"registration_id" → registrationId (json['registration_id'])
"requested_at" → requestedAt  (json['requested_at'])  ← NOT 'created_at'
"joined_via"   → joinedVia    (json['joined_via'])
```

**FAIL conditions:**
```
❌ json['id'] instead of json['student_id'] → wrong student approved/rejected
❌ json['created_at'] instead of json['requested_at'] → date never shows
```

### 3.8 TrackerModel

```bash
grep -n "submitted_count\|pending_count\|missed_count\|late_count\|tracker_status\|student_id\|registration_id" lib/models/assignment_model.dart
```

**Expected mapping (from `GET /assignments/{id}/tracker`):**
```dart
"assignment_id"   → assignmentId
"submitted_count" → submittedCount (json['submitted_count'])
"pending_count"   → pendingCount   (json['pending_count'])
"missed_count"    → missedCount    (json['missed_count'])
"late_count"      → lateCount      (json['late_count'])
"students"        → students
// Per student:
"student_id"      → studentId      (json['student_id'])
"full_name"       → fullName       (json['full_name'])
"registration_id" → registrationId (json['registration_id'])
"tracker_status"  → trackerStatus  (json['tracker_status'])
"submitted_at"    → submittedAt    (json['submitted_at'])
"is_late"         → isLate         (json['is_late'])
"submission_id"   → submissionId   (json['submission_id'])
```

### 3.9 NotificationModel

```bash
grep -n "notification_type\|is_read\|created_at\|unread_count" lib/models/notification_model.dart
```

**Expected mapping:**
```dart
"id"                → id
"notification_type" → notificationType (json['notification_type'])  ← NOT 'type'
"title"             → title
"body"              → body
"payload"           → payload          (Map<String, dynamic>?)
"is_read"           → isRead           (json['is_read'])
"created_at"        → createdAt        (json['created_at'])
// Response wrapper:
"notifications"     → notifications    (list)
"unread_count"      → unreadCount      (json['unread_count'])
```

### 3.10 AiResponseModel

```bash
grep -n "fromJson\|query_text\|action_links\|result\|no_data\|intent" lib/models/ai_response_model.dart
```

**Expected mapping:**
```dart
"intent"       → intent
"query_text"   → queryText    (json['query_text'])
"result"       → result       (AiResult)
"action_links" → actionLinks  (json['action_links'])
// AiResult:
"type"         → type
"data"         → data         (List<dynamic>)
"message"      → message
// ActionLink:
"label"        → label
"route"        → route
```

---

## Section 4 — Auth Screen Verification

### 4.1 splash_screen.dart

**Check in code:**
```bash
grep -n "health\|auth/me\|role\|ADMIN\|MENTOR\|STUDENT\|server_wakeup\|5.*second\|Duration" lib/screens/auth/splash_screen.dart
```

| Behavior | Must find |
|---|---|
| Calls `GET /health` first | `/health` in call |
| Shows server wakeup after 5s | 5000ms or Duration(seconds:5) |
| Reads token from secure storage | auth_storage read |
| Calls `GET /auth/me` if token found | `/auth/me` call |
| Routes by role | ADMIN/MENTOR/STUDENT branch |
| Goes to login if no token | navigate to login |

**FAIL conditions:**
```
❌ Skips GET /health → judge sees blank screen for 30s on Render cold start
❌ Uses hardcoded role instead of response role
❌ Does not clear token on 401 from /auth/me
❌ server_wakeup_widget not shown when health check is slow
```

### 4.2 login_screen.dart

**Check API call shape:**
```bash
grep -n "registration_id\|fcm_token\|email\|password\|POST.*login\|403\|401\|pending" lib/screens/auth/login_screen.dart
```

| Behavior | Must find |
|---|---|
| Sends `registration_id` (even empty string for admin) | `registration_id` in body |
| Sends `fcm_token` (even empty string) | `fcm_token` in body |
| Stores all 7 auth storage keys on success | all keys written |
| Shows backend `detail` on error | `detail` field read from error response |
| 403 "pending approval" shows correct message | pending message displayed |
| Routes by `user.role` from response | role routing after login |

**FAIL conditions:**
```
❌ registration_id omitted from body → mentor/student always get 401
❌ fcm_token omitted → FCM push never works for this device
❌ class_id not stored after login → mentor/student dashboard breaks
❌ Showing generic "Login failed" instead of backend detail message
```

### 4.3 admin_signup_screen.dart

```bash
grep -n "full_name\|POST.*signup\|otp_verify\|navigate\|201" lib/screens/auth/admin_signup_screen.dart
```

| Behavior | Must find |
|---|---|
| Sends `full_name` (not `name`) | `full_name` in request body |
| Navigates to OTP screen on 201 | navigate + otp reference |
| Passes email to OTP screen | email passed as argument |

### 4.4 otp_verify_screen.dart

```bash
grep -n "verify-otp\|otp\|access_token\|refresh_token\|admin.*dashboard\|navigate" lib/screens/auth/otp_verify_screen.dart
```

| Behavior | Must find |
|---|---|
| Calls `POST /auth/admin/verify-otp` | verify-otp in URL |
| Stores tokens on success | access_token + refresh_token stored |
| Routes to admin dashboard | admin dashboard navigation |
| Shows error on 400/410 | error handling present |

---

## Section 5 — Admin Screen Verification

### 5.1 admin_dashboard_screen.dart

```bash
grep -n "analytics/admin/overview\|notifications\|primary_mentor_name\|avg_completion\|high_risk_count\|total_classes" lib/screens/admin/admin_dashboard_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /analytics/admin/overview` | endpoint present |
| Calls `GET /notifications` | endpoint present |
| Displays `primary_mentor_name` on class card | field read from model |
| Displays `avg_completion` per class | field read |
| Displays `high_risk_count` per class | field read |
| Does NOT call `GET /auth/me` on load | should NOT be present |
| Uses cached values from auth_storage | auth_storage read |

**FAIL conditions:**
```
❌ Calling GET /auth/me on dashboard load (slow + unnecessary — use cached values)
❌ primary_mentor_name hardcoded or missing → class card shows wrong data
❌ Stats computed locally instead of from backend
```

### 5.2 approvals_screen.dart (Admin)

```bash
grep -n "class_id.*approvals\|student_id\|approve\|reject\|pending_count\|requested_at\|optimistic" lib/screens/admin/approvals_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /classes/{class_id}/approvals` | correct endpoint |
| Reads `student_id` (not `id`) for approve/reject | `studentId` field used |
| Approve calls `PATCH .../students/{student_id}/approve` | correct path |
| Reject shows reason dialog → sends `{ "reason": "..." }` | reason field in body |
| Removes card from list after approve/reject | optimistic/immediate UI update |
| Shows per-row spinner while action in progress | loading per row |
| Displays `requested_at` (not `created_at`) | field name correct |
| Empty state when `pending_count == 0` | empty state rendered |

### 5.3 class_students_screen.dart

```bash
grep -n "membership_status\|joined_at\|completion_rate\|risk_level\|registration_id" lib/screens/admin/class_students_screen.dart
```

| Field | What to check |
|---|---|
| `membership_status` | must read `membershipStatus` (not `status`) from model |
| `joined_at` | displayed, not `created_at` |
| `risk_level` | drives RiskBadge color |
| `completion_rate` | displayed as percentage |
| `registration_id` | shown per student |

**FAIL condition:**
```
❌ Uses model.status instead of model.membershipStatus → always null
```

### 5.4 class_detail_screen.dart

```bash
grep -n "GET.*classes/{class_id}\|approvals\|students\|PATCH.*class\|ARCHIVED\|primary_mentor" lib/screens/admin/class_detail_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /classes/{class_id}` | endpoint present |
| Shows `primary_mentor` name from response (not hardcoded) | field read |
| Shows `co_mentors` list | co_mentors parsed |
| Archive action calls `PATCH /classes/{class_id}` with `"status": "ARCHIVED"` | body correct |
| Refresh after archive | data reload triggered |

### 5.5 bulk_import_screen.dart

```bash
grep -n "bulk-import/template\|bulk-import\|batch_id\|COMPLETED\|PARTIAL\|xlsx\|polling\|3.*second" lib/screens/admin/bulk_import_screen.dart
```

| Behavior | Must verify |
|---|---|
| Template download calls `GET /provision/bulk-import/template` | correct endpoint |
| Upload calls `POST /provision/bulk-import` with `multipart/form-data` | multipart |
| Reads `batch_id` from 202 response | `batch_id` read |
| Polls `GET /provision/bulk-import/{batch_id}` every 3s | timer + endpoint |
| Stops polling on COMPLETED/PARTIAL/FAILED | status check |
| Shows error table by `sheet_name`, `row_number`, `error_message` | fields read |
| Accepts `.xlsx` only | file filter |

### 5.6 add_co_mentor_screen.dart

```bash
grep -n "co-mentors\|full_name\|email\|registration_id.*response\|Invitation" lib/screens/admin/add_co_mentor_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `POST /classes/{class_id}/co-mentors` | endpoint present |
| Request body has only `full_name` and `email` | NO password field (backend generates it) |
| Shows `registration_id` from response | response field read |
| Shows "Invitation email sent" message | message field read |

**FAIL condition:**
```
❌ Sending 'password' in co-mentor request body → backend ignores it or errors
```

### 5.7 analytics_overview_screen.dart

```bash
grep -n "analytics/admin/overview\|primary_mentor_name\|avg_completion\|avg_miss_rate\|class_id\|drill" lib/screens/admin/analytics_overview_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /analytics/admin/overview` | endpoint present |
| Bar chart uses `avg_completion` from backend | field read (not computed) |
| Second chart uses `avg_miss_rate` or `high_risk_count` | field read |
| Tap on class → navigate to `class_analytics_drill_screen.dart` with `class_id` | navigation |
| Each chart has a one-line caption | caption text present |

### 5.8 class_analytics_drill_screen.dart (Admin drill into class)

```bash
grep -n "analytics/classes/{class_id}\|analytics/classes/{class_id}/students\|risk_distribution\|bottleneck_assignments\|NORMAL.*LOW.*MEDIUM" lib/screens/admin/class_analytics_drill_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /analytics/classes/{class_id}` | endpoint present |
| Displays `risk_distribution` as donut chart | 5 segments: NORMAL,LOW,MEDIUM,HIGH,RECOVERING |
| Shows `bottleneck_assignments` list | field read |
| Student list from `GET /analytics/classes/{class_id}/students` | correct endpoint |
| Each student row tappable → student profile | navigation present |

---

## Section 6 — Mentor Screen Verification

### 6.1 mentor_dashboard_screen.dart

```bash
grep -n "classes/my-classes\|analytics/classes\|notifications\|auth/me\|class_id" lib/screens/mentor/mentor_dashboard_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /classes/my-classes` | correct endpoint (NOT `GET /classes`) |
| Calls `GET /analytics/classes/{class_id}` | analytics loaded |
| Does NOT call `GET /auth/me` on load | use cached class_id |
| Shows pending approvals count | approvals shortcut |

**FAIL condition:**
```
❌ Calls GET /classes instead of GET /classes/my-classes → admin endpoint, mentor gets 403
```

### 6.2 create_assignment_screen.dart

```bash
grep -n "content_type\|submission_type\|rich_text_body\|content_url\|auto_close\|deadline_at\|presigned-upload\|POST.*assignments" lib/screens/mentor/create_assignment_screen.dart
```

| Behavior | Must verify |
|---|---|
| Request body uses `content_type` (not `contentType`) | snake_case |
| Request body uses `submission_type` (not `submissionType`) | snake_case |
| Request body uses `rich_text_body` | field name correct |
| Request body uses `deadline_at` as ISO string or null | correct format |
| Request body uses `auto_close` boolean | field present |
| PDF content: presigned upload first → `file_url` used as `content_url` | flow correct |
| LINK content: user pastes URL into `content_url` | handled |
| RICH_TEXT: user fills `rich_text_body` | handled |

**FAIL conditions:**
```
❌ Sending camelCase keys → backend returns 422 validation error
❌ Sending file to submit endpoint instead of S3 → crashes on Render memory limit
❌ deadline_at sent as locale date string instead of ISO8601 → backend 422
```

### 6.3 assignment_tracker_screen.dart

```bash
grep -n "tracker\|WebSocket\|ws_client\|submission_created\|tracker_refresh\|submitted_count\|pending_count\|tracker_status\|student_id" lib/screens/mentor/assignment_tracker_screen.dart
```

| Behavior | Must verify |
|---|---|
| Loads initial data via `GET /assignments/{id}/tracker` | REST call on open |
| Opens WebSocket via ws_client | ws_client used |
| `submission_created` event updates student row by `student.student_id` | studentId lookup |
| `submission_created` updates count badges | counters updated |
| `tracker_refresh` triggers full REST refetch | GET tracker called |
| Shows "Assignment closed" banner on tracker_refresh | banner shown |
| "Live updates paused" shown on WS disconnect | disconnect handler |
| Reconnect button retries WS | reconnect logic |
| Close button → `POST /assignments/{id}/close` | endpoint present |
| Close button only shown when status=PUBLISHED | conditional render |
| Export button → `POST /exports/assignment-tracker` | for mentor |
| Export button only shown when status=CLOSED | conditional render |

**FAIL conditions:**
```
❌ No WebSocket — tracker only shows initial data, never updates
❌ Updating count badges with local math instead of WS payload counts
❌ Export available before assignment is CLOSED
```

### 6.4 export_screen.dart

```bash
grep -n "exports/assignment-tracker\|export_job_id\|DONE\|PENDING\|presigned-download\|3.*second\|poll\|file_url\|download_url" lib/screens/mentor/export_screen.dart
```

| Behavior | Must verify |
|---|---|
| POST to `POST /exports/assignment-tracker` | correct endpoint |
| Reads `export_job_id` from 202 response | field read |
| Polls `GET /exports/{export_job_id}` every 3 seconds | timer present |
| Stops polling when `status == "DONE"` or `"FAILED"` | status check |
| On DONE: calls `POST /storage/presigned-download` with `file_url` | correct endpoint |
| Opens `download_url` from presigned-download response | url opened |
| Shows error on FAILED | error state |

**FAIL conditions:**
```
❌ Reading file_url directly without presigned-download → S3 private files return 403
❌ Opening file_url instead of download_url → download fails
❌ No polling → user sees "PENDING" forever
```

### 6.5 analytics_screen.dart (Mentor)

```bash
grep -n "analytics/classes/{class_id}\|analytics/classes/{class_id}/students\|analytics/risk\|risk_distribution\|bottleneck\|avg_completion\|avg_miss_rate" lib/screens/mentor/analytics_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls 3 endpoints in parallel or sequence | all 3 present |
| `GET /analytics/classes/{class_id}` | endpoint present |
| `GET /analytics/classes/{class_id}/students` | endpoint present |
| `GET /analytics/risk/students?class_id={class_id}` | endpoint with query param |
| Donut chart for `risk_distribution` | 5-key map used |
| `bottleneck_assignments` shown as list | field read |

### 6.6 ai_query_screen.dart (Mentor)

```bash
grep -n "POST.*ai/query\|class_id\|query_text\|intent\|action_links\|no_data\|route\|result\." lib/screens/mentor/ai_query_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `POST /ai/query` | endpoint present |
| Sends `class_id` (from cached auth_storage, not user input) | class_id in body |
| Sends `query_text` from text field | field name correct |
| Displays `result.message` | field read |
| Displays `result.type` | field read |
| Renders `action_links` as tappable buttons | links rendered |
| Each action_link navigates using `route` field | route used for navigation |
| Shows no_data card when `result.type == "no_data"` | handled |
| Works when no data exists (e.g. no classes yet) | no crash |

---

## Section 7 — Student Screen Verification

### 7.1 student_dashboard_screen.dart

```bash
grep -n "analytics/students\|assignments.*class_id\|notifications\|auth/me\|user_id\|total_submitted\|total_missed\|risk_level" lib/screens/student/student_dashboard_screen.dart
```

| Behavior | Must verify |
|---|---|
| Reads `user_id` and `class_id` from auth_storage (not API) | storage read |
| Calls `GET /analytics/students/{student_id}` | endpoint with stored user_id |
| Calls `GET /assignments?class_id={class_id}` | endpoint with stored class_id |
| Calls `GET /notifications` | endpoint present |
| Does NOT call `GET /auth/me` | should be absent |
| Shows `total_submitted`, `total_missed` from analytics | fields read |
| Shows `risk_level` | field read |

**FAIL conditions:**
```
❌ Calls GET /auth/me on every dashboard load → slow, unnecessary extra API call
❌ Uses hardcoded student_id instead of cached user_id → wrong student analytics
❌ Computes completion locally instead of reading completion_rate from backend
```

### 7.2 assignment_detail_screen.dart

```bash
grep -n "student_submission\|submitted\|submission_id\|submitted_at\|is_late\|set.*reminder\|notifications/reminder\|presigned-download\|201.*remind" lib/screens/student/assignment_detail_screen.dart
```

| Behavior | Must verify |
|---|---|
| Reads `student_submission.submitted` to check if submitted | correct field path |
| Shows submission receipt if `student_submission.submitted == true` | conditional render |
| Submit button hidden if already submitted (or shows resubmit) | state driven by field |
| Set reminder button calls `POST /notifications/reminder` | endpoint present |
| Reminder body sends `assignment_id` and `remind_at` as ISO string | body shape correct |
| On reminder 201: reads `remind_at` from response and shows toast | response field read |
| View PDF calls `POST /storage/presigned-download` | endpoint present |

**FAIL conditions:**
```
❌ Using json['studentSubmission'] instead of json['student_submission'] → always null, submit shows incorrectly
❌ Calling submit without checking if deadline passed → student confused about is_late
❌ Hardcoded reminder time instead of ISO timestamp → backend 422
```

### 7.3 submit_assignment_screen.dart

```bash
grep -n "presigned-upload\|upload_url\|file_url\|POST.*submit\|submission_type\|text_answer\|multipart\|FILE.*TEXT.*BOTH" lib/screens/student/submit_assignment_screen.dart
```

| Behavior | Must verify |
|---|---|
| FILE submissions: calls `POST /storage/presigned-upload` first | endpoint present |
| HTTP PUT to `upload_url` with file bytes | PUT method to S3 |
| Only sends `file_url` to submit endpoint — NOT multipart | JSON body only |
| Submit body uses `file_url` not `file` | field name correct |
| TEXT submissions: sends `text_answer` | field present |
| `submission_type` sent as `"FILE"` or `"TEXT"` string | enum correct |
| Shows receipt from 201 response | `receipt` field displayed |
| `is_late` flag shown if response `is_late == true` | field read |
| `version` number shown (for resubmissions) | field read |
| FILE upload blocked if S3 PUT fails | error handling |

**FAIL conditions:**
```
❌ Sending multipart form to submit endpoint → backend expects JSON
❌ Not calling presigned-upload first → no file_url to send
❌ Sending json['fileUrl'] instead of json['file_url'] in body → backend 422
❌ Not showing is_late banner when is_late=true
```

### 7.4 submission_history_screen.dart

```bash
grep -n "submissions/my\|submission_id\|assignment_title\|is_late\|version" lib/screens/student/submission_history_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /submissions/my` | correct endpoint |
| Uses `submission_id` (not `id`) | field name |
| Shows `assignment_title` | field read |
| Shows `is_late` badge | field read |
| Shows `version` for resubmissions | field read |

### 7.5 my_analytics_screen.dart

```bash
grep -n "analytics/students\|user_id\|completion_rate\|current_streak\|class_avg_completion\|assignment_history\|tracker_status" lib/screens/student/my_analytics_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /analytics/students/{student_id}` using cached `user_id` | correct |
| Shows `completion_rate` as percentage | field read |
| Shows `current_streak` | field read |
| Shows `class_avg_completion` for comparison | field read |
| Assignment history list shows `tracker_status` per item | field read |
| History items color coded: SUBMITTED=green, MISSED=red, LATE=orange, PENDING=grey | colors |
| Charts are backend-driven — no computed values | no local math |

### 7.6 notifications_screen.dart

```bash
grep -n "notifications\|PATCH.*read-all\|PATCH.*{notification_id}.*read\|unread_count\|notification_type\|is_read" lib/screens/student/notifications_screen.dart
```

| Behavior | Must verify |
|---|---|
| Calls `GET /notifications` | endpoint present |
| Mark one read: `PATCH /notifications/{notification_id}/read` | endpoint with ID |
| Mark all read: `PATCH /notifications/read-all` | correct endpoint |
| Shows `unread_count` badge | field read |
| Shows `notification_type` | field read |
| Updates badge count after read | local count update |

---

## Section 8 — Widget Verification

### 8.1 risk_badge_widget.dart

```bash
grep -n "NORMAL\|LOW\|MEDIUM\|HIGH\|RECOVERING\|Color\|color" lib/widgets/risk_badge_widget.dart
```

**Expected — all 5 risk levels handled with distinct colors:**
```
NORMAL     → green or grey
LOW        → yellow or light orange
MEDIUM     → orange
HIGH       → red
RECOVERING → blue or teal
```

**FAIL:** Any risk level not handled → default/null color shown

### 8.2 tracker_card_widget.dart

```bash
grep -n "SUBMITTED\|PENDING\|MISSED\|LATE\|tracker_status\|submittedAt\|isLate" lib/widgets/tracker_card_widget.dart
```

**All 4 tracker statuses must have distinct visual treatment:**
```
SUBMITTED → green
PENDING   → grey
MISSED    → red
LATE      → orange
```

### 8.3 analytics_chart_widget.dart

```bash
grep -n "backend\|fromJson\|hardcode\|mock\|dummy\|completion_rate\|avg_completion" lib/widgets/analytics_chart_widget.dart
```

**FAIL conditions:**
```
❌ Any hardcoded data arrays [45, 60, 72] → must come from backend models
❌ Any random() or DateTime.now() used for chart data
❌ Chart renders when data list is empty (should show empty state)
```

### 8.4 server_wakeup_widget.dart

```bash
grep -n "5.*second\|Duration\|Render\|starting\|cold\|wake" lib/widgets/server_wakeup_widget.dart
```

**Must show:** Message about server starting up, shown only after 5-second delay on splash.

---

## Section 9 — API Call Contract Verification

### 9.1 Complete Endpoint Coverage Check

Run this to find all endpoint strings in the frontend:
```bash
grep -rn "api/v1\|/auth/\|/classes\|/assignments\|/submissions\|/analytics\|/provision\|/storage\|/notifications\|/exports\|/ai/" lib/ | grep -v "test"
```

**Expected — every endpoint below must appear at least once:**

| Endpoint | File it should appear in |
|---|---|
| `GET /health` | splash_screen.dart |
| `POST /auth/admin/signup` | admin_signup_screen.dart |
| `POST /auth/admin/verify-otp` | otp_verify_screen.dart |
| `POST /auth/login` | login_screen.dart |
| `POST /auth/refresh` | api_client.dart (interceptor) |
| `POST /auth/logout` | auth_provider.dart or settings |
| `GET /auth/me` | splash_screen.dart only |
| `POST /classes` | create_class_screen.dart |
| `GET /classes` | class_list_screen.dart (admin) |
| `GET /classes/my-classes` | mentor_dashboard_screen.dart |
| `GET /classes/{class_id}` | class_detail_screen.dart |
| `PATCH /classes/{class_id}` | class_detail_screen.dart |
| `GET /classes/{class_id}/students` | class_students_screen.dart |
| `GET /classes/{class_id}/approvals` | approvals_screen.dart |
| `PATCH /classes/{class_id}/students/{id}/approve` | approvals_screen.dart |
| `PATCH /classes/{class_id}/students/{id}/reject` | approvals_screen.dart |
| `POST /classes/{class_id}/co-mentors` | add_co_mentor_screen.dart |
| `GET /provision/bulk-import/template` | bulk_import_screen.dart |
| `POST /provision/bulk-import` | bulk_import_screen.dart |
| `GET /provision/bulk-import/{batch_id}` | bulk_import_screen.dart |
| `POST /provision/manual/mentor` | admin screen (manual provision) |
| `POST /provision/manual/student` | admin/mentor screen |
| `POST /assignments` | create_assignment_screen.dart |
| `GET /assignments?class_id=` | assignment_list_screen.dart |
| `GET /assignments/{id}` | assignment_detail_screen.dart |
| `POST /assignments/{id}/publish` | assignment_list or tracker screen |
| `POST /assignments/{id}/close` | assignment_tracker_screen.dart |
| `GET /assignments/{id}/tracker` | assignment_tracker_screen.dart |
| `POST /assignments/{id}/submit` | submit_assignment_screen.dart |
| `GET /assignments/{id}/submissions` | submission_detail_screen.dart |
| `GET /submissions/my` | submission_history_screen.dart |
| `POST /storage/presigned-upload` | submit + create_assignment |
| `POST /storage/presigned-download` | assignment_detail + export |
| `GET /analytics/admin/overview` | analytics_overview_screen.dart |
| `GET /analytics/classes/{id}` | analytics screens |
| `GET /analytics/classes/{id}/students` | analytics screens |
| `GET /analytics/students/{id}` | student_profile + my_analytics |
| `GET /analytics/risk/students?class_id=` | risk_list_screen.dart |
| `GET /analytics/assignments/{id}` | class_analytics_drill |
| `GET /notifications` | multiple screens |
| `PATCH /notifications/{id}/read` | notifications_screen.dart |
| `PATCH /notifications/read-all` | notifications_screen.dart |
| `POST /notifications/reminder` | assignment_detail_screen.dart |
| `POST /exports/assignment-tracker` | export_screen.dart |
| `GET /exports/{export_job_id}` | export_screen.dart |
| `POST /ai/query` | ai_query_screen.dart |

### 9.2 Request Body Field Names (Must Be snake_case)

```bash
grep -rn "\"full_name\"\|\"class_id\"\|\"content_type\"\|\"submission_type\"\|\"deadline_at\"\|\"rich_text_body\"\|\"auto_close\"\|\"registration_id\"\|\"fcm_token\"\|\"file_url\"\|\"text_answer\"\|\"query_text\"\|\"assignment_id\"\|\"remind_at\"" lib/
```

**Every key in every request body must be snake_case.**

**FAIL — common camelCase mistakes to detect:**
```bash
grep -rn "\"contentType\"\|\"submissionType\"\|\"deadlineAt\"\|\"richTextBody\"\|\"autoClose\"\|\"classId\"\|\"registrationId\"\|\"fcmToken\"\|\"fileUrl\"\|\"textAnswer\"\|\"queryText\"\|\"assignmentId\"\|\"remindAt\"" lib/
```

If any of the above appear in request bodies → **critical mismatch**, backend returns 422.

---

## Section 10 — WebSocket Verification

### 10.1 Connection URL Format

```bash
grep -n "?token=\|wss://\|kWsUrl\|/ws/tracker" lib/core/ws_client.dart
```

**Expected connection URL:**
```
wss://assignhub-api.onrender.com/api/v1/ws/tracker/{assignment_id}?token=<access_token>
```

**FAIL conditions:**
```
❌ Authorization header used instead of ?token= query param
   (WebSocket protocol does not support custom headers in Flutter's web_socket_channel)
❌ ws:// instead of wss:// → connection rejected by Render HTTPS
❌ Token missing → backend rejects with 403, no tracker updates
```

### 10.2 Event Handling

```bash
grep -n "submission_created\|tracker_refresh\|connected\|event\|json" lib/core/ws_client.dart
```

**Expected handling:**
```dart
switch (event["event"]) {
  case "submission_created":
    // update student row by student.student_id
    // update count badges from payload (not local math)
    break;
  case "tracker_refresh":
    // refetch GET /assignments/{id}/tracker
    // show "Assignment closed" banner
    break;
  case "connected":
    // no UI action needed
    break;
}
```

### 10.3 Reconnect Logic

```bash
grep -n "reconnect\|backoff\|attempt\|2000\|4000\|8000\|3.*attempt" lib/core/ws_client.dart
```

**Expected:**
- Attempt 1: wait 2 seconds
- Attempt 2: wait 4 seconds
- Attempt 3: wait 8 seconds
- After 3 failures: show "Could not connect for live updates" message
- Tracker still functional via manual refresh button (REST call)

---

## Section 11 — S3 Upload/Download Flow

### 11.1 Assignment PDF Upload Flow

```bash
grep -n "presigned-upload\|upload_url\|PUT\|file_url.*content_url\|ASSIGNMENT" lib/screens/mentor/create_assignment_screen.dart
```

**Expected flow (must be in this exact order):**
1. `POST /storage/presigned-upload` with `upload_purpose: "ASSIGNMENT"`
2. HTTP PUT to `upload_url` with file bytes + `Content-Type` header
3. On PUT 200: use `file_url` from step 1 response as `content_url` in assignment body
4. `POST /assignments` with `content_url` = file_url

**FAIL:**
```
❌ Sending file to FastAPI endpoint (multipart) → memory crash on Render
❌ Using response body from S3 PUT as file_url → S3 PUT returns empty body
❌ Skipping Content-Type header on S3 PUT → upload fails silently
```

### 11.2 Submission File Upload Flow

```bash
grep -n "presigned-upload\|upload_url\|PUT\|file_url\|SUBMISSION\|submit" lib/screens/student/submit_assignment_screen.dart
```

**Expected flow:**
1. `POST /storage/presigned-upload` with `upload_purpose: "SUBMISSION"`
2. HTTP PUT to `upload_url` with file bytes
3. On PUT 200: use `file_url` in submit body
4. `POST /assignments/{id}/submit` with `{ "submission_type": "FILE", "file_url": "..." }`

### 11.3 File Download Flow

```bash
grep -n "presigned-download\|download_url\|file_url\|open\|launch\|url_launcher" lib/screens/
```

**Expected flow:**
1. `POST /storage/presigned-download` with `{ "file_url": "s3_url_string" }`
2. Read `download_url` from response
3. Open `download_url` using `url_launcher` or `open_file`

**FAIL:**
```
❌ Opening file_url directly → S3 bucket is private, returns 403
❌ Reading download_url as file_url → wrong field
```

---

## Section 12 — Analytics Display Verification

### 12.1 No Locally Computed Analytics

```bash
grep -rn "\.length\|\.where\|\.filter\|count.*local\|sum.*local\|percentage.*local" lib/screens/*/analytics*.dart lib/screens/*/my_analytics*.dart lib/screens/*/student_profile*.dart
```

**Check that the following values are NOT computed locally:**
- Completion rate → must come from `completionRate` model field
- Miss rate → must come from `avgMissRate` model field
- Risk count → must come from `highRiskCount` model field
- At-risk list → must come from `GET /analytics/risk/students`

**FAIL:** Any `list.length` used as a metric → local computation, not from backend.

### 12.2 Student Dashboard Analytics Tappable Cards

```bash
grep -n "onTap\|GestureDetector\|InkWell.*total_submitted\|onTap.*total_missed\|onTap.*total_late" lib/screens/student/student_dashboard_screen.dart
```

**Expected:**
- Tap `total_submitted` card → show filtered assignment_history list (tracker_status=SUBMITTED)
- Tap `total_missed` card → show filtered list (tracker_status=MISSED)
- Tap `total_late` card → show filtered list (tracker_status=LATE)
- Each item shows `title` + `submitted_at` or `deadline_at`

### 12.3 Admin Overview Bar Chart

```bash
grep -n "avg_completion\|avgCompletion\|class_name\|className\|BarChart\|BarRod\|BarTouch" lib/screens/admin/analytics_overview_screen.dart
```

**Expected:** Bar chart X axis = class names, Y axis = avg_completion values, all from backend.

### 12.4 Risk Distribution Donut Chart

```bash
grep -n "risk_distribution\|riskDistribution\|NORMAL\|LOW\|MEDIUM\|HIGH\|RECOVERING\|PieChart\|PieSection" lib/screens/mentor/analytics_screen.dart lib/screens/admin/class_analytics_drill_screen.dart
```

**Expected:** 5-segment donut reading `riskDistribution` map from `ClassAnalyticsModel`.

---

## Section 13 — AI Query Screen Verification

### 13.1 ai_query_screen.dart (Both Admin and Mentor versions)

```bash
grep -rn "POST.*ai/query\|query_text\|class_id\|result\.\|action_links\|no_data\|intent\|route" lib/screens/admin/ai_query_screen.dart lib/screens/mentor/ai_query_screen.dart
```

| Behavior | Must verify |
|---|---|
| Sends `class_id` from cached auth_storage | not from user input |
| Sends `query_text` from text field | field name snake_case |
| Displays `result.message` prominently | field read |
| Renders `action_links` as buttons | list rendered |
| Each button uses `link.route` for navigation | route field used |
| `no_data` response shows helpful message | type check |
| Works when class has zero data | no crash |
| Renders data type: `student_list` as list | list render |
| Renders data type: `class_summary` as cards | card render |
| Renders data type: `risk_list` with risk badges | risk badge used |

**FAIL conditions:**
```
❌ class_id hardcoded or missing → AI queries wrong class
❌ action_links not rendered → user cannot navigate to results
❌ Crash when result.data is empty array
```

---

## Section 14 — Export Flow Verification

```bash
grep -rn "exports/assignment-tracker\|export_job_id\|DONE\|PENDING\|FAILED\|presigned-download\|download_url\|poll\|timer\|3.*second" lib/screens/mentor/export_screen.dart
```

**Full flow check:**

| Step | Must find |
|---|---|
| POST `/exports/assignment-tracker` with `assignment_id` | endpoint + body |
| Read `export_job_id` from 202 response | field read |
| Timer: poll every 3 seconds | Timer.periodic or Future.delayed |
| GET `/exports/{export_job_id}` in poll | endpoint in loop |
| Stop timer on DONE or FAILED | timer.cancel() |
| On DONE: POST `/storage/presigned-download` with `file_url` | endpoint called |
| Open `download_url` | url opened |
| FAILED state shows error message | error UI |
| Only available for CLOSED assignments | status guard |

---

## Section 15 — RBAC & Navigation Guards

### 15.1 Role-Based Route Access

```bash
grep -rn "ADMIN\|MENTOR\|STUDENT\|redirect\|role\|guard" lib/core/router.dart
```

**Verify these guards exist:**

| Protection | Expected behavior |
|---|---|
| Admin routes | blocked for MENTOR and STUDENT |
| `GET /classes` (admin only) | not callable by mentor UI |
| Mentor uses `GET /classes/my-classes` | explicit check |
| `GET /analytics/admin/overview` | admin-only route |
| Student cannot reach tracker screen | route guard |
| Student cannot reach approvals screen | route guard |

### 15.2 No Cross-Role API Calls

```bash
grep -rn "analytics/admin/overview" lib/screens/mentor/ lib/screens/student/
```
Expected: zero results (admin-only endpoint not called from mentor or student screens)

```bash
grep -rn "GET /classes\"" lib/screens/mentor/
```
Expected: zero results (admin endpoint; mentor must use `/classes/my-classes`)

---

## Section 16 — Error & Empty State Handling

### 16.1 Error Handling on Every Screen

```bash
grep -rn "catch\|onError\|detail\|401\|403\|404\|500\|errorWidget\|ErrorWidget" lib/screens/
```

**Every screen must handle:**

| HTTP Code | Expected behavior |
|---|---|
| 401 | Interceptor refreshes token; if fail → logout |
| 403 | Show "Permission denied" card, do NOT crash |
| 404 | Show "Not found" message tied to entity name |
| 422 | Show validation error from `detail` |
| 500 | Show "Server error, try again" with retry |
| Network error | Show retry button, not blank screen |

### 16.2 Empty State on Every List

```bash
grep -rn "isEmpty\|empty\|No.*assignments\|No.*students\|No.*classes\|No.*notifications\|EmptyState\|emptyState" lib/screens/
```

**Every list-based screen must have empty state:**

| Screen | Empty state text |
|---|---|
| Assignment list | "No assignments yet in your class" |
| Student list | "No students in this class yet" |
| Approvals | "No pending approvals" |
| Notifications | "No notifications" |
| Submission history | "No submissions yet" |
| Class list | "Create your first class to get started" |
| Risk list | "No at-risk students" |

---

## Section 17 — Critical Mismatch Checklist

Run these grep commands. Any result = bug.

### 17.1 camelCase Keys in Request Bodies (Must Be Zero Results)
```bash
grep -rn "\"classId\"\|\"fullName\"\|\"className\"\|\"contentType\"\|\"submissionType\"\|\"deadlineAt\"\|\"richTextBody\"\|\"autoClose\"\|\"registrationId\"\|\"fcmToken\"\|\"fileUrl\"\|\"textAnswer\"\|\"queryText\"\|\"assignmentId\"\|\"remindAt\"\|\"isPrimaryMentor\"\|\"academicYear\"" lib/
```
**Expected: zero results.** Any camelCase in a request body → backend returns 422.

### 17.2 Wrong Field Names in fromJson (Must Be Zero Results)
```bash
grep -rn "json\['classId'\]\|json\['fullName'\]\|json\['className'\]\|json\['submissionType'\]\|json\['contentType'\]\|json\['deadlineAt'\]\|json\['isLate'\]\|json\['isCurrent'\]\|json\['trackerStatus'\]\|json\['riskLevel'\]\|json\['membershipStatus'\]\|json\['registrationId'\]\|json\['submissionId'\]\|json\['assignmentTitle'\]\|json\['assignmentId'\]\|json\['requestedAt'\]\|json\['createdAt'\]\|json\['joinedAt'\]\|json\['completionRate'\]\|json\['studentId'\]\|json\['primaryMentorName'\]\|json\['highRiskCount'\]" lib/
```
**Expected: zero results.** All fromJson must use snake_case keys.

### 17.3 GET /auth/me Called Outside Splash (Should Be Zero)
```bash
grep -rn "auth/me" lib/screens/admin/ lib/screens/mentor/ lib/screens/student/
```
**Expected: zero results.** GET /auth/me is only called from splash_screen.dart.

### 17.4 GET /classes Called from Mentor Screen (Must Be Zero)
```bash
grep -rn "GET.*'/classes'" lib/screens/mentor/ lib/screens/student/
```
**Expected: zero results.** Mentor uses `/classes/my-classes`. Admin uses `/classes`.

### 17.5 Multipart Submit to Assignment Submit Endpoint (Must Be Zero)
```bash
grep -rn "multipart\|FormData.*submit\|MultipartFile.*submit" lib/screens/student/submit_assignment_screen.dart
```
**Expected: zero results.** Submit endpoint accepts JSON only.

### 17.6 Missing snake_case Key for membership_status (Must Be Zero)
```bash
grep -rn "json\['status'\]" lib/models/class_model.dart
```
**Expected: zero.** The field is `membership_status`, not `status`.

### 17.7 student_id Instead of id in Approvals (Must Find student_id)
```bash
grep -n "studentId\|student_id" lib/screens/admin/approvals_screen.dart lib/screens/mentor/approvals_screen.dart
```
**Expected: `studentId` or `student_id` used for approve/reject calls.** `id` used → wrong student acted on.

### 17.8 submission_id Instead of id (Must Find submission_id)
```bash
grep -n "submissionId\|submission_id" lib/models/submission_model.dart
```
**Expected: submission_id parsed.** If `id` used → submission history broken.

### 17.9 Hardcoded Data Check (Must Be Zero)
```bash
grep -rn "\[45,\s*60\|mock.*data\|dummy.*data\|fake.*data\|\[0\.45\|\[0\.6" lib/
```
**Expected: zero results.** No mock/dummy/hardcoded metric data.

### 17.10 Export File URL Opened Directly Without Presigned Download (Must Be Zero)
```bash
grep -rn "openFile.*file_url\|launch.*file_url\|open.*fileUrl" lib/screens/mentor/export_screen.dart
```
**Expected: zero results.** Must call presigned-download first.

### 17.11 WebSocket Token in Header Instead of Query Param (Must Be Zero)
```bash
grep -n "Authorization.*WebSocket\|headers.*wss\|headers.*ws://" lib/core/ws_client.dart
```
**Expected: zero results.** Token goes in `?token=` query param.

### 17.12 GET /analytics/admin/overview Called from Mentor/Student (Must Be Zero)
```bash
grep -rn "analytics/admin/overview" lib/screens/mentor/ lib/screens/student/
```
**Expected: zero results.**

---

## Section 18 — Full Manual Walkthrough Checklist

Run the app and verify these flows manually against the live backend:

### Admin Flow
```
□ App launches → sees "connecting" / server wakeup on first open
□ Navigate to admin signup → fill form → OTP email received → verify → land on admin dashboard
□ Admin dashboard shows class cards from API (not placeholders)
□ Create class → class appears in list immediately (from response, not reload)
□ Download bulk import template → opens as XLSX with 3 sheets
□ Upload filled XLSX → polling shows COMPLETED → imported users visible in class
□ Add co-mentor manually → email received with credentials
□ View approvals → approve student → student card removed from list instantly
□ Reject student with reason → status changes to REJECTED in students list
□ Create assignment (PDF type) → PDF uploads to S3 first → assignment saved
□ Publish assignment → FCM notification shows on student device
□ Analytics overview → bar chart shows class comparison from backend data
□ AI query "who are at-risk students?" → shows list with action links
□ Tap action link → navigates to correct student profile
```

### Mentor Flow
```
□ Login with email + password + registration_id → lands on mentor dashboard
□ Dashboard shows class data (not generic placeholder)
□ View approvals → approve → student can now login
□ Create RICH_TEXT assignment → publish → tracker opens
□ Tracker shows live updates when student submits (WebSocket)
□ tracker_refresh received on close → "Assignment closed" banner shown
□ Close assignment → export button appears → export XLSX → file downloads
□ Risk list shows at-risk students with correct badges
□ AI query screen works with class context
```

### Student Flow
```
□ Login fails with 403 while pending → message says "pending approval"
□ After approval: login succeeds → dashboard shows assignments from class
□ Open assignment → see content, submission status, set reminder
□ Set reminder → toast shows scheduled time from API response
□ Submit text answer → receipt shown with timestamp, is_late=false if on time
□ Submit again → receipt shows version=2
□ Submission history shows only current submission (version 2 only)
□ My analytics → shows completion_rate, streaks, history list
□ History list: color coded by tracker_status
□ Notifications screen → mark all read → badge clears
```

---

## Summary — Pass Criteria

| Section | What it checks | Gate |
|---|---|---|
| 1. File Structure | All 57 Dart files exist | All present |
| 2. Core Layer | api_client interceptor, auth_storage keys, ws_client behavior | All behaviors implemented |
| 3. Model Fields | All fromJson use snake_case keys | Zero camelCase keys |
| 4. Auth Screens | Correct API calls, body shapes, routing | All flows correct |
| 5. Admin Screens | Correct endpoints, field names, data display | All screens verified |
| 6. Mentor Screens | Correct endpoints especially my-classes | All screens verified |
| 7. Student Screens | No auth/me on dashboard, correct field access | All screens verified |
| 8. Widgets | Risk badges, tracker colors, no hardcoded data | All variants handled |
| 9. API Coverage | All 44 endpoints called from correct screens | All present |
| 10. WebSocket | ?token= param, correct events, reconnect logic | All behaviors |
| 11. S3 Flow | presigned-upload → PUT → file_url → submit | Full flow in code |
| 12. Analytics | Backend-driven charts, no local computation | Zero local metrics |
| 13. AI Query | class_id from storage, action_links rendered | All behaviors |
| 14. Export | Poll every 3s, presigned-download before open | Full flow |
| 15. RBAC | Role guards, no cross-role endpoint calls | All guards |
| 16. Error States | Every screen handles 401/403/404/500/network | All handled |
| 17. Mismatch Check | Zero camelCase in bodies, zero wrong fromJson keys | All 12 checks zero |
| 18. Manual Walk | Full user journeys verified on real device | All flows pass |

**Frontend is verified 100% when all 18 sections pass and all 12 mismatch grep checks return zero.**
