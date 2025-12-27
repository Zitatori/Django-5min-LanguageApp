QuickLesson — 5-Minute Online Language Lessons (WIP)

Live demo (development):
https://django-5min-languageapp.onrender.com/

Status: 🚧 Heavy work in progress. Not production-ready.

QuickLesson is a safety-first, minimal language conversation platform focused on
5-minute, tutor-only online lessons.

The core idea is simple:

Talk for 5 minutes. Learn. Stop. No dating, no endless chatting.

Concept

QuickLesson is intentionally restrictive by design.

Only Student ↔ Approved Tutor matching

Hard 5-minute time limit (forced end)

Tutors are reviewed & approved

Built to prevent dating / erotic / casual chat misuse

Designed for future moderation and admin intervention

Roles (UI labels)
Language	Waiting side	Joining side
Japanese	相手役	参加者
English	Partner	Guest
Spanish	Guía	Participante
French	Guide	Participant

(Internal system roles remain student / tutor / admin.)

Tech Stack (MVP)

Python / Django

SQLite (dev only)

Server-rendered templates + custom lightweight CSS

No frontend framework

Current Features (MVP)
Models

LessonLanguage — supported languages

StudentProfile — minimal student profile

TutorProfile

supported languages

is_online

can_interview

(planned) is_approved

QuickLessonRequest

lesson request (waiting / matched / cancelled)

purpose: lesson / interview

QuickLessonMatch

who matched with whom

started_at / end_at (5-minute slot)

price (for future credits)

room metadata (future WebRTC)

Current Flow
Student

Login

Select a language

Request a 5-minute lesson

Backend searches for:

online

approved

language-compatible tutors

If matched → lesson room

If not → waiting screen with auto-retry

Tutor

Login

Open dashboard

Toggle online/offline

Get matched automatically

See recent lesson history (minimal)

Admin (for now)

Django Admin:

create languages

manage users

link profiles

Planned:

role management

tutor approval

Roadmap (Short)

Enforce strict Student ↔ Tutor only logic

Real 5-minute enforcement (server + client)

In-browser WebRTC video

Admin monitoring & recording

Reports / bans / moderation

Credit-based payments (anti-abuse)

Philosophy

This project intentionally trades flexibility for safety.

No random user calls

No long sessions

No anonymity loopholes

No “just chatting”

If someone wants to misuse it, the system should make it annoying.

Quick Start
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver


Then in Django Admin:

Create LessonLanguage

Create users

Attach StudentProfile / TutorProfile

Purpose of This Repo

Personal learning project

Django backend design practice

WebRTC experimentation

Moderation & safety-oriented system design

Target vision:

A place where you can safely speak a foreign language for 5 minutes —
and where dating misuse is blocked by design.
