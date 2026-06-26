# AssignHub 🎓

**Intelligent Classroom & Assignment Management Platform**

[![Flutter](https://img.shields.io/badge/Flutter-Dart-02569B?logo=flutter&logoColor=white)](https://flutter.dev)
[![FastAPI](https://img.shields.io/badge/FastAPI-Python%203.11-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-336791?logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![AWS S3](https://img.shields.io/badge/AWS-S3-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/s3/)
[![Firebase](https://img.shields.io/badge/Firebase-FCM-FFCA28?logo=firebase&logoColor=white)](https://firebase.google.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Built for **DevFusion 3.0 Hackathon** — Problem Statement #26ENAH1

AssignHub is a mobile-first educational platform that automates classroom administration, tracks student performance in real time, and centralizes the entire assignment lifecycle — from creation to grading — for Admins, Mentors, and Students.

---

## 🧩 Problem & Solution

Traditional classroom management is fragmented across disconnected tools for assignments, grading, and communication — creating heavy administrative overhead and leaving mentors blind to struggling students until it's too late. Onboarding hundreds of users each year is manual and error-prone, and important deadlines get buried in static portals instead of reaching students directly.

**AssignHub solves this with:**

| Problem | AssignHub's Solution |
|---|---|
| No early warning for struggling students | **Intelligent Analytics Engine** auto-flags "At-Risk" students from submission delays and missed deadlines |
| Manual, error-prone onboarding | **Smart Provisioning** via one-click bulk Excel imports for entire classrooms |
| Missed deadlines & grades | **Real-time sync** via WebSockets + Firebase Cloud Messaging push alerts |
| Fragmented assignment workflow | **End-to-end lifecycle management** — create, publish, submit, version, and grade in one place |

---

## ✨ Key Features

- **Role-based dashboards** — purpose-built interfaces for Admins, Mentors, and Students
- **At-risk student detection** — automated flagging based on submission behavior
- **Live push notifications** — instant FCM alerts for new assignments and grades
- **Bulk onboarding** — import thousands of users via `.xlsx`, with automated OTP email invites
- **Versioned submissions** — secure AWS S3 storage with digital receipts for every submission
- **API-first backend** — fully documented REST endpoints with WebSocket support

---

## 📸 Demo / Screenshots

<table>
  <tr>
    <th align="center">Login / OTP</th>
    <th align="center">Admin Dashboard</th>
    <th align="center">Mentor Dashboard</th>
    <th align="center">Student Dashboard</th>
    <th align="center">Analytics / At-Risk View</th>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/user-attachments/assets/e16fc10d-a7eb-4270-bc08-3a435c2c4dec" width="160" height="auto"/></td>
    <td align="center"><img src="https://github.com/user-attachments/assets/40673d64-9cdd-4f16-8891-b03e6096b22c" width="160" height="auto"/></td>
    <td align="center"><img src="https://github.com/user-attachments/assets/463a0ac7-21fe-4314-be72-9a3fbb865e3c" width="160" height="auto"/></td>
    <td align="center"><img src="https://github.com/user-attachments/assets/09877d48-7a3c-4449-aac0-4d6921d8bec0" width="160" height="auto"/></td>
    <td align="center"><img src="https://github.com/user-attachments/assets/7ec38513-6cad-4e34-9f63-6f6ba82c6887" width="160" height="auto"/></td>
  </tr>
</table>

🎥 **Demo video:** [Add link here]

---

## 🏗️ Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────┐
│  Flutter App     │◄──────►│   FastAPI Backend │◄──────►│  PostgreSQL  │
│  (Android)        │  REST/  │   (Python 3.11)   │   ORM   │              │
│                   │  WS     │                   │         └──────────────┘
└─────────────────┘         └──────────────────┘
        ▲                            │
        │ FCM Push                   │ boto3
        ▼                            ▼
┌─────────────────┐         ┌──────────────────┐
│ Firebase Cloud   │         │     AWS S3        │
│ Messaging         │         │ (submission files)│
└─────────────────┘         └──────────────────┘
```

**Roles & Flow:**
1. **Admin** bulk-uploads rosters (Excel) → backend auto-creates accounts and emails OTP invites
2. **Mentor** approves pending students → analytics profiles generated → manages classroom
3. **Mentor** publishes assignments → push notification blast to enrolled students
4. **Student** submits work (stored in S3) → system versions it and issues a digital receipt
5. **Analytics engine** continuously tracks submission patterns and flags at-risk students

---

## 🛠️ Tech Stack

### Frontend (Mobile)
| Component | Technology |
|---|---|
| Framework | Flutter (Dart) |
| Target Platform | Android |
| State Management | Provider / Riverpod |
| Real-Time | WebSockets, Firebase Cloud Messaging (FCM) |
| File Handling | `file_picker` for Excel/document uploads |

### Backend
| Component | Technology |
|---|---|
| Framework | FastAPI (Python 3.11+) |
| Database | PostgreSQL via SQLAlchemy ORM |
| Auth | JWT + Email OTP |
| File Storage | AWS S3 (`boto3`) |
| Background Jobs | APScheduler (deadline monitoring) |
| Data Processing | `pandas`, `openpyxl` (bulk imports) |
| Deployment | Render |

---

## 🚀 Getting Started

### Prerequisites
- Flutter SDK (Android toolchain)
- Python 3.9+
- PostgreSQL

### 1. Clone the repository
```bash
git clone https://github.com/praveenscode-ctrl/iit-hackathon-project-.git
cd iit-hackathon-project-
```

### 2. Backend setup
```bash
cd Backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
cp .env.example .env         # fill in DB, AWS, and SMTP credentials

alembic upgrade head         # run database migrations
uvicorn main:app --reload --port 8000
```
API will be live at `http://localhost:8000/docs` (interactive Swagger UI).

### 3. Frontend setup
```bash
cd ../Frontend
flutter pub get
flutter run
```
Make sure an Android emulator or physical device is connected.

### 4. Build production APK
```bash
cd Frontend
flutter build apk --release
```
Output: `Frontend/build/app/outputs/flutter-apk/app-release.apk`

---

## 🔐 Environment Variables

Create a `.env` file in `Backend/` based on `.env.example`:

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Secret key for signing JWTs |
| `AWS_ACCESS_KEY_ID` | AWS IAM access key for S3 |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret key for S3 |
| `AWS_S3_BUCKET` | S3 bucket name for submissions |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | Email service for OTP delivery |
| `FCM_SERVER_KEY` | Firebase Cloud Messaging server key |

> ⚠️ Never commit `.env` — it's already excluded via `.gitignore`.

---

## 📊 Project Status

| Domain | Status | Notes |
|---|---|---|
| Frontend App | ✅ Stable | Responsive Android UI complete |
| Backend API | ✅ Functional | Core endpoints tested and working |
| Authentication | ✅ Implemented | JWT + Email OTP verification |
| Analytics Engine | ✅ Active | Real-time risk assessment operational |
| Bulk Import | ✅ Active | Excel (`.xlsx`) parsing and validation |

---

## 🌍 SDG Alignment

- **SDG 4 — Quality Education:** Gives educators the analytics needed to intervene early when students fall behind, improving learning outcomes.
- **SDG 10 — Reduced Inequalities:** Makes enterprise-grade classroom management accessible to institutions of any size, without large IT budgets.

---

## 🗺️ Roadmap

- [ ] iOS support
- [ ] AI-assisted grading suggestions
- [ ] Parent/guardian portal
- [ ] Offline-first submission queue
- [ ] CI/CD pipeline with automated test coverage reporting

---

## 👥 Team

| Name | GitHub |
|---|---|
| Monish R | [@MONISHRCSE](https://github.com/MONISHRCSE) |
| Praveen S | [@praveenscode-ctrl](https://github.com/praveenscode-ctrl) |
| Jaisimha | [Add GitHub link] |



<p align="center">Empowering Education Through Intelligent Systems 💙</p>
