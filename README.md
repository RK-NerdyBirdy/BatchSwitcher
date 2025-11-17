# Batch Swap Platform

A FastAPI-based platform that enables VIT students to swap class batches based on CGPA eligibility.

## Overview

Students often get assigned to batches that don't fit their schedule. This platform allows students to find eligible swap partners (within CGPA tolerance), send swap requests, and communicate through real-time chat to coordinate batch swaps.

## Key Features

- **Google OAuth Authentication** - Secure login with VIT student emails
- **Smart Matching** - Find students within CGPA tolerance (±0.06)
- **Real-time Chat** - WebSocket-based messaging
- **Swap Management** - Send, accept, reject, or cancel swap requests
- **Batch Tracking** - Track original and current batch assignments

## Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **Database**: PostgreSQL / NeonDB (async with SQLAlchemy)
- **Authentication**: Google OAuth 2.0 (Authlib)
- **Real-time**: WebSockets
- **Validation**: Pydantic

## Quick Start

```bash
# Clone and setup
git clone <[repo-url](https://github.com/RK-NerdyBirdy/BatchSwitcher)>
cd BatchSwitcher/Backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run
uvicorn main:app --reload
```

## 📁 Project Structure

```
BatchSwitcher/backend/
├── main.py              # Application entry point
├── config.py            # Configuration settings
├── database.py          # Database setup
├── models.py            # Database models
├── schemas.py           # Pydantic schemas
├── auth.py              # Auth utilities
└── routers/             # API endpoints
    ├── auth.py          # Authentication
    ├── students.py      # Student management
    ├── swap_requests.py # Swap handling
    └── chat.py          # Real-time chat
```

## 🔑 Environment Setup

Required environment variables in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
SECRET_KEY=your-secret-key
SESSION_SECRET_KEY=your-session-secret
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
CGPA_TOLERANCE=0.06
```

## 📚 API Endpoints

- **Auth**: `/auth/login`, `/auth/callback`, `/auth/register`, `/auth/me`
- **Students**: `/students/eligible`, `/students/me`
- **Swaps**: `/swap-requests`, `/swap-requests/{id}/accept`
- **Chat**: `/chat/messages/{id}`, `/chat/ws/{id}`

**API Docs**: http://localhost:8000/docs

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable Google+ API
3. Create OAuth credentials
4. Add redirect URI: `http://localhost:8000/auth/callback`
5. Copy Client ID & Secret to `.env`

## Database Schema

- **Students**: User profiles with CGPA and batch info
- **SwapRequests**: Tracks swap requests between students
- **ChatMessages**: Stores chat history

## Deployment

Works with Railway, Render, or any platform supporting Python + PostgreSQL.

```bash
# Example: Railway
railway init
railway add postgresql
railway up
```

Update OAuth redirect URI to production URL after deployment.

## License

MIT License - see LICENSE file for details.

---

**Made with ❤️ for CSBS students**

