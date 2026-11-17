# Project 2: Fridge Tracker

This document gives instructions to install and run the backend and frontend software.

## Requirements

Ensure that you install this software first:
- Python 3.10 or newer
- Node.js 18 or newer
- npm 9 or newer

---

## 1. Backend Setup

Follow these steps to prepare and start the backend service.

### Step 1: Open the Project Root Directory
Open your terminal and go to the project directory:
```bash
cd /path/to/project2-csci270
```

### Step 2: Create and Activate a Virtual Environment
Create a Python virtual environment:
```bash
python3 -m venv venv
```

Activate the virtual environment:
- On macOS and Linux:
  ```bash
  source venv/bin/activate
  ```
- On Windows:
  ```bash
  venv\Scripts\activate
  ```

### Step 3: Install Required Python Packages
Install the required packages in your virtual environment:
```bash
pip install fastapi uvicorn python-multipart pydantic torch torchvision ultralytics pillow
```

### Step 4: Start the Backend Server
Run the FastAPI application from the repository root:
```bash
python3 -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

The backend server starts at:
- API Root: `http://127.0.0.1:8000/`
- API Documentation: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

---

## 2. Frontend Setup

Follow these steps to prepare and start the frontend application.

### Step 1: Go to the Frontend Directory
Open a new terminal window and go to the frontend directory:
```bash
cd /path/to/project2-csci270/frontend
```

### Step 2: Install Node Dependencies
Install the package dependencies:
```bash
npm install
```

### Step 3: Start the Frontend Development Server
Start the development server:
```bash
npm run dev
```

The frontend development server starts at:
- Local URL: `http://localhost:3000/`

---

## 3. Verify the System

Verify that both services operate together:
1. Keep the backend server running in the first terminal.
2. Keep the frontend server running in the second terminal.
3. Open `http://localhost:3000/` in your web browser.
4. Upload a refrigerator photo to detect food items, calculate expiration dates, and view inventory.
