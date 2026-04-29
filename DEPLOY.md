# Deployment Guide: Zero Waste Mess Management System

The application has been upgraded to support a **Local Development Stack** (FastAPI + SQL) alongside a **Production Stack** (Firebase + Netlify).

## 1. Local Development (FastAPI + React)

The local stack continues to work exactly as before, with full offline capabilities using SQLite/PostgreSQL.
Firebase imports are gracefully skipped when not in a cloud environment.

```bash
# Start Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Start Frontend
cd frontend
npm install
npm run dev
```

## 2. Production Deployment (Firebase + Netlify)

The application can be deployed as a serverless production app using Firebase for the backend/database and Netlify (or Firebase Hosting) for the frontend.

### Step 2.1: Firebase Backend Setup
1. Create a Firebase Project in the Firebase Console.
2. Enable Firestore, Realtime Database, and Storage.
3. Install Firebase CLI: `npm install -g firebase-tools`
4. Login: `firebase login`
5. Initialize the project: `firebase init` (Select Functions & Hosting). Select the project you created.

### Step 2.2: Backend Environment Variables
Create a production environment file:
```bash
cd backend
cp .env.firebase .env.prod
```
Edit `.env.prod` with your actual production database URL (e.g., Neon/PlanetScale for SQL, or rely entirely on Firestore), and your JWT keys.
Set the secrets in Firebase Functions:
```bash
firebase functions:secrets:set JWT_SECRET_KEY
firebase functions:secrets:set DATABASE_URL
```

### Step 2.3: Deploy Backend (Functions)
```bash
cd backend
# Make sure to install mangum and firebase-admin locally if you haven't
pip install mangum firebase-admin firebase-functions
firebase deploy --only functions
```
After deployment, Firebase will provide a URL for your function (e.g., `https://us-central1-yourproject.cloudfunctions.net/api` or a Cloud Run URL). Note this URL.

### Step 2.4: Deploy Frontend (Netlify or Firebase)

**Option A: Netlify (Recommended)**
1. Connect your repository to Netlify.
2. Netlify will read `netlify.toml` automatically.
3. In Netlify dashboard, set the Environment Variable:
   `VITE_API_URL = "https://your-firebase-function-url/api"`
4. Deploy the site.

**Option B: Firebase Hosting**
1. Build the React app:
```bash
cd frontend
npm run build
```
2. Deploy to Firebase Hosting:
```bash
firebase deploy --only hosting
```

## 3. Architecture Changes in Production
* **Routing:** `main_firebase.py` wraps FastAPI via Mangum.
* **Database:** SQL writes are mirrored to Firestore via `firestore_sync.py`.
* **Realtime:** WebSockets are supplemented by Firebase Realtime Database broadcasts (`firebase_realtime.py`).
* **Storage:** Profile images and the ML model (`attendance_model.pkl`) are saved to Firebase Storage (`firebase_storage.py`).
