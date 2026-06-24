# AssignHub

Assignment management platform — DevFusion 3.0, Problem Statement #26ENAH1

**Stack:** Flutter (Android) · FastAPI · PostgreSQL · AWS S3 · FCM · Render

## Structure

```
AssignHub/
├── Backend/    ← FastAPI backend
└── Frontend/   ← Flutter Android app
```

## Backend setup

```bash
cd Backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # fill in all values
alembic upgrade head
uvicorn main:app --reload
```

## Frontend setup

```bash
cd Frontend
flutter pub get
flutter run
```

## Build APK

```bash
cd Frontend
flutter build apk --release
```
