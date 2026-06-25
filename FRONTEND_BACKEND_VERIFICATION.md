# Frontend vs Backend Implementation Verification Checklist

This document is for verifying that the Frontend implementation **100% matches** the completed Backend implementation. It outlines the exact API endpoints, request bodies, response schemas, and enums that the frontend MUST follow. Any mismatch in field names, data types, or endpoint paths will cause integration failures.

## ⚠️ Golden Rules for Frontend Verification
1. **No Renaming**: Do not rename fields in your Dart models (e.g., do not change `class_id` to `classId` in the JSON serialization, use `@JsonKey(name: 'class_id')`).
2. **Base URL**: The base URL is `https://<backend_url>/api/v1`. All endpoints below are appended to this base.
3. **Authorization**: Every protected endpoint requires the `Authorization: Bearer <access_token>` header.
4. **Enums**: Enum values must match the exact string casing (e.g., `RICH_TEXT`, `STUDENT`, `SUBMITTED`).

---

## 1. Authentication (`/auth`)

### Admin Signup
- **Endpoint**: `POST /auth/admin/signup`
- **Request Body**: `{"full_name": "...", "email": "...", "password": "..."}`
- **Response**: `{"message": "OTP sent to email"}`

### Admin OTP Verification
- **Endpoint**: `POST /auth/admin/verify-otp`
- **Request Body**: `{"email": "...", "otp": "..."}`
- **Response**: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

### Login (All Roles)
- **Endpoint**: `POST /auth/login`
- **Request Body**: 
  ```json
  {
    "email": "...", 
    "password": "...", 
    "registration_id": "...", // Optional, but required for student login
    "fcm_token": "..." // Optional
  }
  ```
- **Response**: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

### Refresh Token
- **Endpoint**: `POST /auth/refresh`
- **Headers**: `Authorization: Bearer <refresh_token>`
- **Response**: `{"access_token": "...", "refresh_token": "...", "token_type": "bearer"}`

### Get Current User Profile
- **Endpoint**: `GET /auth/me`
- **Response**: 
  ```json
  {
    "id": "...", 
    "email": "...", 
    "full_name": "...", 
    "role": "ADMIN|MENTOR|STUDENT", 
    "registration_id": "...", // Can be null
    "fcm_token": "...", // Can be null
    "created_at": "...", 
    "updated_at": "..."
  }
  ```

---

## 2. Classes (`/classes`)

### Create Class
- **Endpoint**: `POST /classes`
- **Request Body**: `{"class_name": "..."}`
- **Response**: `{"id": "...", "class_name": "...", "created_by": "...", "created_at": "..."}`

### Get Classes
- **Endpoint**: `GET /classes`
- **Response**: 
  ```json
  {
    "classes": [
      {
        "id": "...", 
        "class_name": "...", 
        "created_by": "...", 
        "created_at": "..."
      }
    ]
  }
  ```

---

## 3. Provisioning (`/provision`)

### Add Mentor Manually
- **Endpoint**: `POST /provision/manual/mentor`
- **Request Body**: `{"class_id": "...", "full_name": "...", "email": "...", "password": "...", "is_primary_mentor": true|false}`
- **Response**: `{"id": "...", "registration_id": "..."}`

### Add Student Manually
- **Endpoint**: `POST /provision/manual/student`
- **Request Body**: `{"class_id": "...", "full_name": "...", "email": "...", "password": "...", "registration_id": "..."}`
- **Response**: `{"id": "...", "registration_id": "..."}`

### Get Class Students (Mentor/Admin)
- **Endpoint**: `GET /classes/{class_id}/students`
- **Response**: 
  ```json
  {
    "students": [
      {
        "id": "...", 
        "user_id": "...", 
        "class_id": "...", 
        "status": "PENDING|ACTIVE|REJECTED", 
        "joined_at": "...", 
        "full_name": "...", 
        "email": "...", 
        "registration_id": "...", 
        "risk_level": "NORMAL|AT_RISK|CRITICAL"
      }
    ]
  }
  ```

### Approve/Reject Student
- **Approve**: `PATCH /classes/{class_id}/students/{student_id}/approve`
  - **Request Body**: `{}`
  - **Response**: `{"status": "ACTIVE"}`
- **Reject**: `PATCH /classes/{class_id}/students/{student_id}/reject`
  - **Request Body**: `{"rejection_reason": "..."}`
  - **Response**: `{"status": "REJECTED"}`

### Bulk Import
- **Endpoint**: `POST /provision/bulk-import`
- **Request Body**: `{"class_id": "...", "file_url": "...", "file_type": "CSV|EXCEL"}`
- **Response**: `{"job_id": "..."}`

---

## 4. Assignments (`/assignments`)

### Create Assignment
- **Endpoint**: `POST /assignments`
- **Request Body**: 
  ```json
  {
    "class_id": "...", 
    "title": "...", 
    "description": "...", 
    "content_type": "PDF|LINK|RICH_TEXT", 
    "content_url": "...", // Nullable
    "rich_text_body": "...", // Nullable
    "submission_type": "FILE|TEXT|BOTH", 
    "deadline_at": "2023-12-31T23:59:59Z", // Nullable
    "auto_close": true|false
  }
  ```
- **Response**: `{"id": "...", "title": "...", "status": "DRAFT", "deadline_at": "...", "created_at": "..."}`

### Get Assignments (List)
- **Endpoint**: `GET /assignments?class_id={class_id}`
- **Response**: 
  ```json
  {
    "assignments": [
      {
        "id": "...", 
        "class_id": "...", 
        "created_by": "...", 
        "created_by_name": "...", 
        "title": "...", 
        "description": "...", 
        "content_type": "...", 
        "content_url": "...", 
        "rich_text_body": "...", 
        "submission_type": "...", 
        "deadline_at": "...", 
        "auto_close": true|false, 
        "status": "DRAFT|PUBLISHED|CLOSED", 
        "created_at": "...", 
        "updated_at": "..."
      }
    ]
  }
  ```

### Get Assignment Details
- **Endpoint**: `GET /assignments/{assignment_id}`
- **Response**: Returns the assignment object as above, but adds `student_submission` nested object (for Mentor and Student):
  ```json
  {
    ...assignment_fields,
    "student_submission": {
      "submitted": true|false, 
      "submission_id": "...", // Nullable
      "submitted_at": "...", // Nullable
      "is_late": true|false, 
      "version": 1 // Int
    }
  }
  ```

### Publish / Close Assignment
- **Publish**: `POST /assignments/{assignment_id}/publish` (Body: `{}`) -> `{"status": "PUBLISHED", "message": "..."}`
- **Close**: `POST /assignments/{assignment_id}/close` (Body: `{}`) -> `{"status": "CLOSED"}`

### Assignment Tracker (Live View)
- **Endpoint**: `GET /assignments/{assignment_id}/tracker`
- **Response**: 
  ```json
  {
    "submitted_count": 0,
    "pending_count": 0,
    "missed_count": 0,
    "late_count": 0,
    "students": [
      {
        "student_id": "...",
        "full_name": "...",
        "email": "...",
        "registration_id": "...",
        "risk_level": "NORMAL|AT_RISK|CRITICAL",
        "tracker_status": "PENDING|SUBMITTED|LATE|MISSED",
        "submission_id": "...", // Nullable
        "submitted_at": "...", // Nullable
        "is_late": true|false,
        "version": 0
      }
    ]
  }
  ```

---

## 5. Submissions (`/submissions` & `/assignments/.../submit`)

### Submit Assignment
- **Endpoint**: `POST /assignments/{assignment_id}/submit`
- **Request Body**: 
  ```json
  {
    "submission_type": "FILE|TEXT", 
    "file_url": "...", // Nullable
    "text_answer": "..." // Nullable
  }
  ```
- **Response**: `{"submission_id": "...", "version": 1, "is_late": false, "submitted_at": "..."}`

### Get My Submissions (Student)
- **Endpoint**: `GET /submissions/my`
- **Response**: 
  ```json
  {
    "submissions": [
      {
        "submission_id": "...",
        "assignment_id": "...",
        "assignment_title": "...",
        "submission_type": "...",
        "submitted_at": "...",
        "is_late": true|false,
        "version": 1
      }
    ]
  }
  ```

### Get All Submissions (Mentor)
- **Endpoint**: `GET /assignments/{assignment_id}/submissions`
- **Response**: 
  ```json
  {
    "submissions": [
      {
        "submission_id": "...",
        "student_id": "...",
        "student_name": "...",
        "submission_type": "...",
        "file_url": "...",
        "text_answer": "...",
        "submitted_at": "...",
        "is_late": true|false,
        "version": 1
      }
    ]
  }
  ```

---

## 6. Storage (`/storage`)

### Get Presigned Upload URL
- **Endpoint**: `POST /storage/presigned-upload`
- **Request Body**: `{"file_name": "...", "file_type": "application/pdf", "upload_purpose": "ASSIGNMENT|SUBMISSION|BULK_IMPORT"}`
- **Response**: `{"upload_url": "...", "file_url": "..."}`

### Get Presigned Download URL
- **Endpoint**: `POST /storage/presigned-download`
- **Request Body**: `{"file_url": "..."}`
- **Response**: `{"download_url": "..."}`

---

## 7. Notifications (`/notifications`)

### Create Reminder (Student)
- **Endpoint**: `POST /notifications/reminder`
- **Request Body**: `{"assignment_id": "...", "remind_at": "2023-12-31T12:00:00Z"}`
- **Response**: `{"reminder_id": "...", "remind_at": "..."}`

---

## 8. WebSockets (Live Tracker)

- **Connection URL**: `wss://<backend_url>/api/v1/ws/tracker/{assignment_id}?token=<access_token>`
- **Expected Events**:
  1. `connected`: Sent by server immediately. No action required by frontend.
  2. `tracker_refresh`: Indicates the frontend should REST refetch the tracker data (due to bulk change/closure).
  3. `submission_created`: Sent when a student submits.
     - **Payload**:
       ```json
       {
         "event": "submission_created",
         "student": {
           "student_id": "...",
           "is_late": true|false,
           "submitted_at": "...",
           "tracker_status": "SUBMITTED|LATE"
         },
         "summary": {
           "submitted_count": 5,
           "late_count": 1
         }
       }
       ```
     - **Frontend Action**: Update the specific student row locally and update the summary counters.

---

## Final Verification Steps for Frontend Dev:
1. [ ] Check all API Paths against the Dart `api_client.dart` or service files.
2. [ ] Check all JSON serialization/deserialization keys in your Dart Models.
3. [ ] Check all Enums string values.
4. [ ] Ensure your WebSocket parses `event` properly and updates the state.
5. [ ] Ensure you send `Authorization: Bearer <token>` exactly formatted on REST calls.
6. [ ] Ensure you pass `?token=<access_token>` as a query parameter for the WebSocket connection.
