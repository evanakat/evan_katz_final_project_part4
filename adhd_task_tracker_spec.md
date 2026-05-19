# Focus Flow — ADHD-Friendly Task Tracker

A product specification for a task and project management app designed for adults with ADHD.

---

## 1. Product Overview

**Name (working):** Focus Flow

**One-liner:** A task tracker that thinks like an ADHD brain — capture in seconds, surface what matters now, and recover from overdue lists without shame.

**Target users:** Adults (18–55) with diagnosed or self-identified ADHD who struggle with traditional task apps because those apps reward consistency, punish lapses, and force prioritization decisions the user is least equipped to make.

**Problem:** Standard task managers (Todoist, Asana, Things) assume an executive-function baseline ADHD users do not have. Long backlogs become overwhelming, overdue tasks pile up and trigger avoidance, and prioritization requires the very skill the user lacks.

**Differentiators:**
- One-screen "what now?" view that hides everything else
- AI that triages, breaks down, and re-schedules without the user re-planning
- "Reset" instead of "overdue" — guilt-free recovery flows
- Body-doubling and time-blindness aids built in (timers, visible countdowns)
- Optimized for capture-on-the-go (voice, share sheet, single-tap)

---

## 2. ADHD-Informed Design Principles

- **One decision at a time.** Never show the full backlog when asking "what next?"
- **Capture is sacred.** Adding a task must take under 3 seconds and never require a category, due date, or project.
- **Out of sight, not out of mind.** The app remembers; the user doesn't have to.
- **Externalize time.** Timers, countdowns, and visible "now" markers combat time blindness.
- **Friction in the right places.** Easy to add, easy to defer, slightly harder to delete (prevents impulsive clearing).
- **Shame-free recovery.** Overdue tasks are reframed as "needs a new home," not failures.
- **Dopamine, honestly.** Celebrate completions without infantilizing; avoid streak-shaming.
- **Minimal chrome.** No nested menus, no settings buried three taps deep, no feature creep on the main screen.
- **Reversibility.** Undo is always one tap. Nothing is permanent without confirmation.
- **Calm by default.** Muted palette, no red badges, no aggressive notification dots.

---

## 3. Core Features

### 3.1 Quick Capture
- Single text box on launch; press enter to save
- Voice capture via system mic or hotword
- iOS/Android share sheet, browser extension, email-to-inbox
- Natural language parsing ("call dentist tomorrow 3pm")
- No required fields — capture first, organize never (or later)

### 3.2 Today View ("What Now?")
- Default landing screen
- Shows at most 3–5 tasks at a time
- Prominent "Just one thing" mode: hides everything except the current focus task
- Estimated time and energy badge per task (Low / Medium / High)
- Tap to start a focus timer

### 3.3 Brain Dump / Inbox
- Uncategorized capture lives here indefinitely
- Bulk triage flow: swipe right to schedule, left to defer, up to delete
- AI can sort the inbox on request, never automatically

### 3.4 Focus Mode
- Pomodoro-style timer with adjustable durations (default 25/5)
- Visible countdown ring on home screen widget
- Optional ambient sound / lo-fi
- "Body-double" video loops or partner mode (opt-in)
- End-of-session reflection: did you finish? half? need to break it down?

### 3.5 Projects (Lightweight)
- Flat list of projects, no nesting
- Each project has a "next action" pinned at top (David Allen-inspired)
- Optional kanban view (Inbox / Doing / Done) for visual users
- Projects can be archived without deleting tasks

### 3.6 Gentle Reminders
- Soft notifications: "Hey, this was on your list — still want it?"
- Three response options inline: Do now / Snooze / Move to Someday
- No streak counters, no red badges, no escalating alerts
- Quiet hours and per-project notification settings

### 3.7 Reset Flow (Overdue Recovery)
- Replaces traditional "overdue" tab
- Once a week (or on demand), user runs a 60-second Reset:
  - AI groups stale tasks
  - User chooses: Reschedule / Delegate / Drop / Keep as Someday
  - No item-by-item guilt — batched, fast, finished
- Tasks aren't deleted, just moved to "Someday" if dropped

### 3.8 Time Blindness Aids
- "Time-of-day" cues on tasks (Morning / Afternoon / Evening)
- "How long do you think this takes?" prompt that calibrates against past actuals
- Visible week strip showing where today sits
- Optional "current time" persistent banner

### 3.9 Energy & Mood Matching
- Tag tasks with required energy level
- Daily check-in (optional, two taps): "How's your energy?"
- Today view filters or reorders to match current state

---

## 4. Task Workflow

**Capture → Triage → Surface → Do → Reflect**

1. **Capture** — user dumps a task, no required fields
2. **Triage** — done in batches via Inbox; or AI suggests sorting
3. **Surface** — Today view chooses 3–5 tasks based on due date, energy match, and project pinning
4. **Do** — user starts a focus timer; app hides everything else
5. **Reflect** — quick post-session prompt; partial completion is a valid outcome
6. **Reset** — weekly batched recovery for anything stale; never per-task shame

**State machine:** Inbox → Scheduled → Today → In Progress → Done | Someday | Dropped (with Undo at every step)

---

## 5. UX Requirements

- **Latency:** Quick Capture from cold launch in under 2 seconds
- **Tap depth:** Common actions (capture, complete, snooze) reachable in 1–2 taps
- **Visual hierarchy:** One primary action per screen, generously sized
- **Typography:** Large, high-contrast, dyslexia-friendly default font option
- **Color:** Calm palette; no red urgency cues; configurable themes including dark and low-stimulation modes
- **Motion:** Reduced-motion respected; no surprise animations
- **Empty states:** Encouraging, not nagging ("Nothing right now — that's allowed.")
- **Accessibility:** WCAG 2.2 AA, full screen reader support, voice control, large-touch-target mode
- **Offline:** Full capture and view offline; sync when reconnected
- **No login wall:** First-run capture works before any account creation

---

## 6. AI-Assisted Features

- **Task breakdown:** "Plan my taxes" → AI suggests 4–6 sub-steps with estimates; user accepts or edits
- **Smart triage:** AI groups inbox by theme, urgency, or project on request
- **Time estimation:** Suggests realistic durations based on user's history (combats planning fallacy)
- **Reschedule helper:** During Reset, AI proposes new dates based on calendar and patterns
- **Natural language editing:** "Move everything for Tuesday to Thursday"
- **Daily plan suggestion:** Optional morning "Here's a possible Today" the user approves or ignores
- **Stuck detector:** If a task has been moved 3+ times, AI gently asks if it should be broken down, delegated, or dropped
- **Voice-first capture:** Whisper-class transcription with date/time parsing

**AI constraints:**
- Always suggestion, never auto-action on data the user wrote
- All AI actions reviewable and reversible
- On-device or privacy-preserving inference for task content where possible
- Clear opt-in; full feature parity without AI for privacy-conscious users

---

## 7. MVP Scope

**In scope for v1:**
- Quick Capture (text + voice)
- Inbox + Today views
- Flat projects with next-action pinning
- Focus timer (Pomodoro)
- Gentle reminders with three-option response
- Weekly Reset flow
- AI task breakdown and smart triage (cloud-backed)
- iOS, Android, web (responsive)
- Offline-first sync

**Out of scope for v1:**
- Team collaboration / shared projects
- Advanced calendar integration (read-only Google/Apple Calendar OK; write later)
- Body-double video and partner mode
- Habit tracking (separate concern, easy feature creep trap)
- Time-tracking reports
- Browser extension (post-launch)
- Native widgets beyond a single Today widget

---

## 8. Data Model

```
User
  id, email, timezone, prefs (theme, quiet_hours, ai_enabled, low_stim_mode)

Task
  id, user_id, title, notes?, project_id?, status (inbox|scheduled|today|doing|done|someday|dropped)
  due_at?, scheduled_for?, energy (low|med|high)?, time_estimate_min?, actual_min?
  created_at, updated_at, completed_at?, snooze_count, move_count
  source (manual|voice|share|email|ai)

Project
  id, user_id, name, color, next_action_task_id?, archived_at?

FocusSession
  id, user_id, task_id?, started_at, ended_at, planned_min, actual_min, outcome (done|partial|abandoned)

Reminder
  id, task_id, fire_at, channel (push|email), responded_at?, response (do|snooze|someday)

ResetRun
  id, user_id, started_at, ended_at, tasks_touched, outcomes_json

CheckIn
  id, user_id, at, energy (low|med|high), mood (optional 1–5)
```

Indexes on `user_id + status`, `user_id + scheduled_for`, `task_id + fire_at`.

---

## 9. Success Metrics

**Activation:**
- 70% of new users capture a task in the first session
- 50% return on day 2

**Engagement (healthy, not addictive):**
- Median 3+ captures per active day
- 40% of users complete a focus session per week
- Weekly Reset completion rate above 30%

**ADHD-specific outcomes:**
- Task completion rate among "Today" items above 60%
- Reduction in time-to-first-action after capture (target: 24h median)
- Reduction in "stuck" tasks (moved 3+ times without action) quarter over quarter
- Survey: self-reported overwhelm score decreases after 30 days of use

**Anti-metrics (we do not optimize for):**
- Daily active users at all costs
- Streak length
- Notifications sent

---

## 10. Recommended Tech Stack

**Frontend:**
- React Native (Expo) for iOS + Android, sharing logic with web
- Next.js (App Router) for web
- TanStack Query for data fetching, Zustand for local UI state
- Tailwind + Radix primitives for accessible components

**Backend:**
- Node.js (Fastify) or Go for the API
- PostgreSQL for primary store, Redis for reminder scheduling and queues
- Prisma or Drizzle ORM
- Sync via CRDT-light approach (operation log per device) for offline-first

**AI:**
- Claude (Anthropic) for task breakdown, triage, and natural language parsing
- On-device Whisper-class model for voice capture (privacy + latency)
- Prompt caching and structured tool outputs for cost control

**Infra:**
- Hosted on Fly.io or Vercel (web) + Render/Fly for API
- Auth via Clerk or Supabase Auth (passkeys preferred, magic links fallback)
- Push via APNs/FCM; transactional email via Resend
- Observability: Sentry, PostHog (privacy-respecting analytics)

**Quality:**
- TypeScript end-to-end
- Playwright for web E2E, Detox for mobile
- Accessibility CI checks (axe) on every PR
