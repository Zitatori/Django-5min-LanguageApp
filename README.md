# QuickLesson — 5-Minute Online Language Lessons (WIP)

**Live demo (development):** https://django-5min-languageapp.onrender.com/

**Status:** 🚧 Heavy work in progress. Not production-ready.

---

## What is QuickLesson?

QuickLesson is a **safety-first language conversation platform** focused on:

- **Student ↔ Approved Tutor only**
- **Strict 5-minute lesson limit**
- No dating / erotic / casual chat misuse

> Talk for 5 minutes. Learn. The session ends.

---

## Core Principles

- ❌ No random user-to-user calls
- ❌ No long or endless sessions
- ✅ Short, focused language practice
- ✅ Built for moderation from day one

---

## Roles (UI labels)

Internal system roles remain `student / tutor / admin`.

| Language | Waiting side | Joining side |
|---|---|---|
| Japanese | 相手役 | 参加者 |
| English | Partner | Guest |
| Spanish | Guía | Participante |
| French | Guide | Participant |

---

## Tech Stack (MVP)

- Python / Django
- SQLite (dev only)
- Server-rendered templates + lightweight custom CSS

---

## Current Features (MVP)

### Models

- **LessonLanguage** — supported languages  
- **StudentProfile** — minimal student profile  
- **TutorProfile**
  - supported languages (ManyToMany)
  - `is_online`
  - `can_interview`
  - *(planned)* `is_approved`
- **QuickLessonRequest**
  - lesson request (`waiting / matched / cancelled`)
  - `purpose`: `lesson / interview`
- **QuickLessonMatch**
  - who matched with whom
  - `started_at / end_at` (5-minute slot)
  - `price` (future credits)
  - room metadata (future WebRTC)

---

## Current Flow (MVP)

### Student

1. Login
2. Select a language
3. Request a 5-minute lesson
4. Backend searches for tutors that are:
   - online
   - approved
   - compatible with the requested language
5. If matched → lesson room
6. If not → waiting screen with auto-retry

### Tutor

1. Login
2. Open `/tutor/dashboard/`
3. Toggle online/offline
4. Get matched automatically
5. View recent lesson history (minimal)

### Admin (current)

- Django Admin:
  - manage languages
  - create users
  - link profiles
- Planned:
  - role management
  - tutor approval workflow

---

## Roadmap (short)

- Enforce strict **Student ↔ Tutor only** logic everywhere
- Real **5-minute enforcement** (server + client)
- In-browser **WebRTC video**（Daily Prebuilt）
- Admin monitoring & recording
- Reports / bans / moderation tools
- Credit-based payments (anti-abuse)

---

## Quick Start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
