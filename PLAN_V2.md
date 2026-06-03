# Trend-to-Skill Academy — Research-Backed Plan v2

> Supersedes high-level vision in `PLAN.md`. Anchors every pillar to current (2026) evidence and to the existing Tool_Knowledge_RAG repo so we extend instead of starting fresh.

---

## 0. Strategy Decision

**Verdict: extend Tool_Knowledge_RAG, do not greenfield.**

Reasons:
- Existing assets already cover ~40% of platform foundation: FastAPI + Qdrant + Next.js, multi-tenant `org_id` model, embedding registry, ingestion pipeline, RBAC + auth scaffolding, department-based collections (HR, Sales, Engineering, etc.), tool catalog with department/role/audience tagging.
- Department collections become the natural mapping for **Learning Circles**.
- Existing tool catalog becomes seed material for the first generated courses ("How to use Cursor effectively", "Gong for sales coaching").
- Embedding store already exists for retrieval-grounded course and quiz generation (dedupes weekly trends, avoids hallucinated novelty).

What changes: add a `learning` package on the backend, new tables, new agent module, new frontend routes under `/academy`. Existing `/chat`, `/collections`, `/upload` flows stay untouched.

---

## 1. Research Anchors

| Decision area | Anchored to |
|---|---|
| Trend sources | Hugging Face Daily/Trending Papers, ArXiv `cs.LG`/`cs.AI`, `dair-ai/AI-Papers-of-the-Week`, vendor blogs (OpenAI/Anthropic/Google), HN front page |
| Course format | Microlearning consensus: 3–10 min modules, single objective, multimedia, mobile, spaced repetition (Engageli/eLearningIndustry 2026, retention 25–60% lift) |
| Quiz generation | Concept-map-guided MCQ generation (arXiv 2505.02850) — 75% quality vs ~37% baseline; LLM-as-judge (Qwen3) per MDPI 2026; knowledge-graph distractor seeding |
| Gamification | Stack Overflow reputation primitives (+5 question upvote, +10 answer upvote, +15 accept, +2 accept-grant), peer-review gating, IP/account abuse tracking |
| Spaced repetition | SM-2 (open Anki algorithm) — proven, no IP cost |
| RAG freshness | "RAG freshness paradox" (ragaboutit 2026), RAGOps (arXiv 2506.03401) — schedule + change-detection retriggers |
| LMS reference | Open edX AI course-creation pattern, BuddyBoss/D2L gamification taxonomy |

---

## 2. Architecture

### 2.1 Module additions (backend)

```
backend/app/
  learning/
    __init__.py
    trend_scout.py         # Trend Scout Agent
    sources/
      arxiv.py             # arxiv.org/list/cs.LG OAI-PMH or RSS
      huggingface.py       # /api/papers/trending
      vendor_blogs.py      # configurable RSS list
      hn.py                # Algolia HN API (filter score>200 + AI tags)
    scoring.py             # business_impact * urgency * audience_fit
    course_builder.py      # uses chat_default LLM + RAG grounding
    quiz_builder.py        # concept-map then MCQ + distractors
    spaced_repetition.py   # SM-2 implementation
    leaderboard.py
    rewards.py             # XP, badges, season reset
    moderation.py          # rate, dedupe, reputation gates
  graph/                   # ALREADY EXISTS in working tree — repurpose for concept map
  api/
    academy/
      trends.py
      courses.py
      enrollments.py
      quizzes.py
      posts.py
      leaderboard.py
      rewards.py
  jobs/
    scheduler.py           # APScheduler — Monday 06:00 publish, Friday 16:00 quiz
```

### 2.2 New tables

```
trend            (id, week_iso, title, summary, source_urls[], score, status)
course           (id, trend_id|null, title, audience_role, est_minutes, status, version)
module           (id, course_id, order, kind: text|diagram|video|checklist, content_json)
question         (id, course_id, stem, options[], correct_idx, difficulty, concept_tags[])
quiz_session     (id, group_id, scheduled_at, mode: solo|battle, status)
attempt          (id, quiz_session_id, user_id, question_id, picked_idx, correct, ms)
group_           (id, name, org_id, collection_id_link, type: dept|squad)
membership       (group_id, user_id, role: member|facilitator|lead)
enrollment       (user_id, course_id, status, completed_at, retention_score)
review_card      (user_id, concept_tag, ease, interval_days, due_at)       # SM-2
post             (id, author_id, kind: tip|sop|experiment|lesson, body_md, tags[])
vote             (post_id|answer_id, user_id, value: +1|-1, weight)
xp_event         (id, user_id, source, amount, multiplier, created_at)
badge            (id, user_id, code, awarded_at)
reputation       (user_id, score, level, computed_at)
season           (id, starts_at, ends_at, ruleset_version)
```

All inherit `org_id` from the existing multi-tenant pattern in `db.py`.

### 2.3 Frontend additions

```
frontend/app/
  academy/
    page.tsx                 # weekly trends + current course
    course/[id]/page.tsx     # module reader + progress
    quiz/[id]/page.tsx       # solo or team mode
    leaderboard/page.tsx
    feed/page.tsx            # knowledge share
    profile/page.tsx         # XP, badges, due review cards
```

Reuse: `AppShell`, `Sidebar`, `TopBar`, theme system.

### 2.4 Agent topology

`Trend Scout (weekly cron) → Course Builder (RAG-grounded) → Diagram Generator (Excalidraw/Mermaid) → Quiz Builder (concept-map MCQ) → Publish event`

Each step writes a checkpoint row so a human reviewer can intervene before publish (default: auto-publish OFF in MVP).

---

## 3. Trend Scout — Concrete Source List + Scoring

### 3.1 Sources (initial whitelist)
- `https://huggingface.co/api/papers/trending` (JSON, polled hourly)
- `https://export.arxiv.org/api/query?search_query=cat:cs.LG+OR+cat:cs.AI&sortBy=submittedDate` (Atom)
- `https://github.com/dair-ai/AI-Papers-of-the-Week` (parse weekly README)
- Vendor RSS: openai.com/news/rss, anthropic.com/news/rss, ai.googleblog.com/feeds/posts/default
- `https://hn.algolia.com/api/v1/search?tags=front_page&query=AI` (filter `points>200`)

### 3.2 Scoring formula

```
score = w_impact * impact + w_urgency * urgency + w_fit * audience_fit - w_dup * dup_penalty

impact      = log10(citations_or_upvotes + 1) normalized 0-1
urgency     = exp(-age_days / 7)
audience_fit = max(cosine(trend_embedding, dept_centroid) for dept in org)
dup_penalty = 1 if cosine(new, last_4_weeks_trends) > 0.85 else 0
```

Weights: start `(0.4, 0.3, 0.3, 1.0)`. Tune from feedback (CTR, completion). Dedupe uses existing Qdrant — store last 12 weeks of published trends in `docs_gemini_768`.

### 3.3 Output contract

```json
{
  "week_iso": "2026-W21",
  "trends": [
    {"title": "…", "summary": "…", "sources": ["…"], "score": 0.87,
     "audience_roles": ["AI Engineer", "Backend Engineer"],
     "risk_notes": ["data leak risk on prompt sharing"]}
  ]
}
```

Mandatory: every trend ships with `risk_notes` and at least one `internal_use_case` proposal (governance rule #2 from v1 plan kept).

---

## 4. Course Generator — Grounded, Reviewed, Versioned

### 4.1 Pipeline

1. Retrieve top-k chunks from Qdrant for the trend topic (limits hallucination, satisfies RAG freshness pattern).
2. Generate course skeleton with `gemini_pro` (registry-configured) using fixed JSON schema.
3. Render diagrams: Mermaid for flow/architecture, Excalidraw export for before/after visuals (Excalidraw MCP server already available).
4. Insert mandatory blocks: `summary`, `internal_use_cases`, `risks_and_compliance`, `implementation_checklist`.
5. Persist as `course` + `module` rows, status=`draft`.
6. Optional human review gate (toggle per org).
7. On publish: spawn `question` rows via §5 pipeline.

### 4.2 Quality gates
- Each module ≤ 10 min reading time (microlearning evidence).
- Schema validation rejects missing risk/checklist blocks.
- LLM-as-judge pass: `Qwen3` (or `gemini_flash`) scores factuality, role-fit, redundancy. Block publish < 0.7.

---

## 5. Quiz Generator — Concept-Map First (75% Quality Path)

Per arXiv 2505.02850, concept-map-guided MCQs hit ~75% quality vs ~37% with naive LLM prompting. Pipeline:

1. Extract concept map from course modules → nodes + edges (use existing `backend/app/graph/` skeleton).
2. For each leaf concept, prompt LLM to produce: stem, correct answer, then **3 distractors targeting common misconceptions** (graph siblings used as distractor seeds).
3. LLM-as-judge (Qwen3 or gemini_flash) rates each MCQ on: stem clarity, distractor plausibility, single-correct, no leakage. Drop if `score < 0.7`.
4. Difficulty assigned from path length in concept map + Bloom-tag classifier.
5. Adaptive selection at runtime via Elo-style item response: rep up if user beats expected, down if loses.

Battle mode: same item pool, synchronized timer, score = `correctness * speed_bonus * difficulty`.

---

## 6. Gamification — Stack Overflow-grade Anti-Spam

### 6.1 Point table

| Action | Base XP |
|---|---|
| Complete module | +5 |
| Pass quiz (≥70%) | +10 |
| Win quiz battle | +15 |
| Post: tip/SOP/experiment/lesson | +2 (provisional) |
| Post upvote | +10 |
| Post downvote | -2 to author, -1 to voter (mirrors SO downvote cost) |
| Post marked playbook | +25 |
| Accept peer answer | +15 |
| Daily streak (≥3 days) | +3 |

### 6.2 Quality multiplier

```
contribution_weight = clamp(reputation_level, 0.5, 2.0)
xp_final = xp_base * contribution_weight * (1 - spam_score)
spam_score in [0,1] from heuristics:
  - duplicate cosine > 0.9 over last 30 days
  - posting velocity > N/hour
  - downvote_ratio > 0.4
  - low-effort length & no media
```

Reputation level steps: 0/100/500/2500/10000 unlock: vote, comment, edit-others, close-flag, moderate.

### 6.3 Anti-spam additions (gap flagged in v1)
- Cooldown: max 5 posts/user/day until level 2.
- Embedding-dedup on post creation.
- IP + account abuse log (SO pattern).
- Season reset every 90 days, weighted carry-over (50% reputation, 0% XP) to avoid grind-forever incentives.

---

## 7. Spaced Repetition — SM-2

Every `concept_tag` a user has answered correctly creates a `review_card` (ease=2.5, interval=1, due=+1d). Each correct re-answer updates `interval ← interval * ease`. Wrong answer resets to interval=1, ease -= 0.2 (floor 1.3). Daily push: notify user of due cards. Aim: 90% retention (Journal of Applied Psychology figure).

---

## 8. Weekly Operating Rhythm (kept, hardened)

Cron jobs (`backend/app/jobs/scheduler.py`):
- Mon 06:00 — trend scout + scoring + publish top 3.
- Mon 12:00 — course builder for top 1 (top 2 & 3 batched Tue 06:00).
- Wed 14:00 — facilitator nudge.
- Fri 16:00 — quiz battle auto-scheduled per group.
- Sun 22:00 — leaderboard freeze + season check + playbook promotion (auto-promote posts with `score ≥ 50` AND `quality_judge ≥ 0.8`).

---

## 9. Identity, Auth, Tenancy

Repo already has `backend/app/api/auth.py`, `core/auth.py`, `core/rbac.py` in flight. Extend:
- Roles: `member`, `facilitator`, `lead`, `admin`.
- All academy endpoints gated by `org_id` (mirrors existing collections pattern).
- SSO deferred to post-MVP (note in `START.md`).

---

## 10. Tech-Risk Register

| Risk | Mitigation |
|---|---|
| Course hallucination | RAG grounding + LLM-as-judge gate + optional human review |
| MCQ quality collapse | Concept-map pipeline + judge score floor + manual override on flagged questions |
| Gamification gaming | Quality multiplier + spam_score + season weighted reset |
| Trend duplication | Embedding dedupe vs last 12 weeks |
| Cost blowout | Default `gemini_flash` for judge + scout summaries; `gemini_pro` only on course skeleton |
| Stale knowledge | Weekly cron + change-detection re-trigger (RAGOps pattern) |
| Quiz cheating in battle | Server-issued shuffled option order + per-question timer + answer signed with session token |

---

## 11. Revised MVP Sprints

### Sprint 0 — Foundation (1 week)
- Migrate new tables (Alembic — note repo currently uses `create_tables`; add Alembic or extend create_tables function).
- Wire `auth.py` + `rbac.py` end-to-end (already partially there).
- Add `learning/sources/arxiv.py` and `huggingface.py` only.
- Manual trigger endpoint `POST /academy/scout/run`.
- Frontend skeleton route `/academy`.

**Exit:** one human-curated trend rendered in UI.

### Sprint 1 — Agent-Assisted Course + Groups (2 weeks)
- `course_builder.py` with RAG grounding + JSON schema + judge gate.
- `course` + `module` UI reader.
- Group create + membership UI (auto-create one per existing department collection).
- Knowledge feed v1 (post, comment, upvote — no downvote yet).

**Exit:** generate Course 1 from a real trend; 2 groups complete it end-to-end.

### Sprint 2 — Quiz + Leaderboard (2 weeks)
- Concept-map extractor on existing `graph/`.
- MCQ + distractor generator + judge.
- Solo quiz + group battle (WebSocket via existing `events.py` SSE).
- Weekly leaderboard + XP + first 3 badges.

**Exit:** Friday battle runs for both pilot groups.

### Sprint 3 — Rewards, Playbooks, Dashboard (2 weeks)
- Reputation level system + downvotes + cooldowns.
- Spaced repetition cards + daily due list.
- Auto-promotion of top posts to playbooks (new `playbook` flag on `post`).
- Admin dashboard: completion, participation, retention, contribution quality.
- Season reset job.

**Exit:** anti-spam scoring live; 90-day pilot loop runnable unattended.

---

## 12. Open Decisions (need user input)

1. Hosting model: stay on embedded Qdrant + SQLite for pilot, or move to managed Qdrant + Postgres now?
2. Diagram engine: Mermaid only (no infra) vs Excalidraw export (richer, slower)?
3. Auto-publish on/off default per org?
4. Pilot org size — how many users / how many groups for Sprint 2 exit?
5. SSO required for pilot or password+OTP good enough?

---

## 13. Acceptance Metrics (Sprint exits)

- Sprint 0: 1 trend live, 0 manual edits needed for source ingest.
- Sprint 1: ≥ 5 modules generated, judge score ≥ 0.7, completion rate ≥ 60%.
- Sprint 2: ≥ 20 MCQs, distractor judge ≥ 0.7, battle participation ≥ 50% of group.
- Sprint 3: contribution per team per month ≥ 1, spam_score on 0 promoted posts, retention day-7 ≥ 60%.

---

## 14. Sources

- [Hugging Face Trending Papers](https://huggingface.co/papers/trending)
- [dair-ai AI-Papers-of-the-Week](https://github.com/dair-ai/AI-Papers-of-the-Week)
- [Concept-Map MCQ generation (arXiv 2505.02850)](https://arxiv.org/pdf/2505.02850)
- [Distractor quality benchmark (MDPI 2026)](https://www.mdpi.com/2073-431X/15/2/130)
- [Knowledge-Graph distractor generation (arXiv 2506.00612)](https://arxiv.org/pdf/2506.00612)
- [Stack Overflow reputation mechanics](https://internal.stackoverflow.help/en/articles/8775594-reputation-and-voting)
- [Microlearning + retention statistics 2026](https://www.engageli.com/blog/20-microlearning-statistics-in-2026)
- [Spaced repetition for enterprise learning](https://getrapl.com/blog/how-spaced-repetition-and-microlearning-help-enterprise-learning/)
- [Open edX AI course creation](https://openedx.org/blog/ai-driven-course-creation-crafting-engaging-content-in-the-open-edx-lms-with-llm/)
- [RAG freshness paradox](https://ragaboutit.com/the-rag-freshness-paradox-why-your-enterprise-agents-are-making-decisions-on-yesterdays-data/)
- [RAGOps paper (arXiv 2506.03401)](https://arxiv.org/html/2506.03401v1)
- [BuddyBoss gamification primer](https://buddyboss.com/blog/gamification-for-learning-to-boost-engagement-with-points-badges-rewards/)
- [D2L gamified LMS 2026](https://www.d2l.com/blog/gamified-learning-management-system/)
