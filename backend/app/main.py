"""
FastAPI application entry point.

Startup:
  1. Create local database tables
  2. Initialize embedded Qdrant collections
  3. Ensure local storage is ready
  4. Seed default collections if empty
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import AsyncQdrantClient
from sqlalchemy import select, update

import uuid

from app.api.chat import router as chat_router
from app.api.collections import router as collections_router
from app.api.events import router as events_router
from app.api.auth import router as auth_router
from app.api.upload import router as upload_router
from app.config import settings
from app.core.registry import resolve_embedding_profile
from app.db import AsyncSessionLocal, CollectionDB, DocumentDB, create_tables
from app.ingestion.pipeline import index_tool_record
from app.retrieval.qdrant import init_collections
from app.storage import ensure_storage_ready

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_COLLECTIONS = [
    {
        "id": "dept-hr",
        "name": "HR",
        "section": "Business Teams",
        "description": "Hiring, onboarding, policy, and people operations tools.",
        "color": "#ef4444",
    },
    {
        "id": "dept-marketing",
        "name": "Marketing",
        "section": "Business Teams",
        "description": "Campaign, content, SEO, and brand workflow tools.",
        "color": "#f59e0b",
    },
    {
        "id": "dept-sales",
        "name": "Sales",
        "section": "Business Teams",
        "description": "Lead generation, CRM, forecasting, and proposal tools.",
        "color": "#14b8a6",
    },
    {
        "id": "dept-operations",
        "name": "Operations",
        "section": "Business Teams",
        "description": "Operations, support, process, and delivery coordination tools.",
        "color": "#6366f1",
    },
    {
        "id": "dept-developer",
        "name": "Developers",
        "section": "Engineering",
        "description": "General engineering tools for implementation and productivity.",
        "color": "#10a37f",
    },
    {
        "id": "dept-frontend",
        "name": "Frontend",
        "section": "Engineering",
        "description": "UI engineering, component systems, and client-side tooling.",
        "color": "#0ea5e9",
    },
    {
        "id": "dept-backend",
        "name": "Backend",
        "section": "Engineering",
        "description": "APIs, data systems, integrations, and backend services.",
        "color": "#8b5cf6",
    },
    {
        "id": "dept-tester",
        "name": "QA & Testing",
        "section": "Engineering",
        "description": "Test automation, quality workflows, and validation tools.",
        "color": "#e11d48",
    },
    {
        "id": "dept-architect",
        "name": "Architecture",
        "section": "Engineering",
        "description": "Architecture design, platform planning, and systems thinking tools.",
        "color": "#22c55e",
    },
]

DEFAULT_TOOLS = [
    # HR
    {"collection_id": "dept-hr", "tool_name": "Rippling", "tool_url": "https://www.rippling.com/", "short_description": "Unified HR, IT, payroll, benefits, and workforce automation platform.", "department": "HR", "primary_role": "People Operations", "audience_roles": ["HR Manager", "IT Admin", "Finance Ops"], "importance_note": "Centralizes employee lifecycle work that normally spans HR, IT, payroll, and compliance systems.", "impact_note": "Reduces manual onboarding and offboarding steps, improves policy consistency, and keeps employee data synchronized.", "rating": 5},
    {"collection_id": "dept-hr", "tool_name": "Deel", "tool_url": "https://www.deel.com/", "short_description": "Global hiring, payroll, contractor management, and compliance platform.", "department": "HR", "primary_role": "Global HR", "audience_roles": ["HR Manager", "Finance Ops", "Founder"], "importance_note": "Useful for teams hiring across countries without building local legal and payroll infrastructure.", "impact_note": "Speeds international onboarding while helping teams manage contracts, payroll, and compliance in one place.", "rating": 5},
    {"collection_id": "dept-hr", "tool_name": "Greenhouse", "tool_url": "https://www.greenhouse.com/", "short_description": "Applicant tracking and structured hiring platform for recruiting teams.", "department": "HR", "primary_role": "Recruiter", "audience_roles": ["Recruiter", "Hiring Manager", "People Ops"], "importance_note": "Structured hiring workflows help growing teams evaluate candidates more consistently.", "impact_note": "Improves pipeline visibility, interview coordination, and candidate feedback loops.", "rating": 4},
    {"collection_id": "dept-hr", "tool_name": "Leapsome", "tool_url": "https://www.leapsome.com/", "short_description": "Performance management, OKRs, learning, and employee engagement platform.", "department": "HR", "primary_role": "HR Manager", "audience_roles": ["HR Manager", "Team Lead", "People Ops"], "importance_note": "Links performance reviews, goal tracking, and learning into one continuous people development workflow.", "impact_note": "Improves feedback cycles, goal alignment, engagement surveys, and manager effectiveness.", "rating": 4},
    # Marketing
    {"collection_id": "dept-marketing", "tool_name": "Jasper", "tool_url": "https://www.jasper.ai/", "short_description": "AI writing and campaign content platform for brand-aligned marketing teams.", "department": "Marketing", "primary_role": "Content Marketer", "audience_roles": ["Content Marketer", "Demand Gen", "Brand Manager"], "importance_note": "Helps teams draft campaign assets while maintaining reusable brand voice and messaging patterns.", "impact_note": "Accelerates blog, ad, email, and landing page drafts for human editing and approval.", "rating": 4},
    {"collection_id": "dept-marketing", "tool_name": "Canva", "tool_url": "https://www.canva.com/", "short_description": "Visual design platform with AI-assisted creative production for teams.", "department": "Marketing", "primary_role": "Designer", "audience_roles": ["Designer", "Social Media Manager", "Marketing Generalist"], "importance_note": "Gives non-designers a fast way to produce on-brand graphics, decks, and campaign assets.", "impact_note": "Reduces creative bottlenecks for social posts, presentations, ads, and lightweight collateral.", "rating": 5},
    {"collection_id": "dept-marketing", "tool_name": "Surfer SEO", "tool_url": "https://surferseo.com/", "short_description": "SEO content planning and optimization platform for search-driven teams.", "department": "Marketing", "primary_role": "SEO Specialist", "audience_roles": ["SEO Specialist", "Content Marketer", "Growth Marketer"], "importance_note": "Connects content production with search intent, keyword coverage, and competitive page structure.", "impact_note": "Helps prioritize content briefs, improve existing articles, and make SEO recommendations more repeatable.", "rating": 4},
    {"collection_id": "dept-marketing", "tool_name": "HubSpot Marketing Hub", "tool_url": "https://www.hubspot.com/products/marketing", "short_description": "Marketing automation, email, landing page, lead capture, and campaign reporting platform.", "department": "Marketing", "primary_role": "Marketing Operations", "audience_roles": ["Marketing Ops", "Demand Gen", "Sales Ops"], "importance_note": "Connects campaign execution with CRM data so teams can attribute leads and nurture prospects.", "impact_note": "Improves lead capture, segmentation, email automation, and campaign reporting across the funnel.", "rating": 5},
    # Sales
    {"collection_id": "dept-sales", "tool_name": "Salesforce Einstein", "tool_url": "https://www.salesforce.com/artificial-intelligence/", "short_description": "AI features across Salesforce for sales forecasting, recommendations, and CRM workflows.", "department": "Sales", "primary_role": "Sales Operations", "audience_roles": ["Account Executive", "Sales Manager", "RevOps"], "importance_note": "Adds AI assistance to the CRM system many revenue teams already use daily.", "impact_note": "Supports forecasting, account prioritization, next-best actions, and customer interaction summaries.", "rating": 5},
    {"collection_id": "dept-sales", "tool_name": "Gong", "tool_url": "https://www.gong.io/", "short_description": "Revenue intelligence platform for call recording, deal insights, coaching, and forecasting.", "department": "Sales", "primary_role": "Sales Manager", "audience_roles": ["Account Executive", "Sales Manager", "Customer Success"], "importance_note": "Turns sales conversations into searchable signals for coaching, deal risk, and pipeline inspection.", "impact_note": "Improves rep coaching, follow-up quality, objection tracking, and forecast confidence.", "rating": 5},
    {"collection_id": "dept-sales", "tool_name": "Apollo.io", "tool_url": "https://www.apollo.io/", "short_description": "B2B prospecting, enrichment, sequencing, and sales engagement platform.", "department": "Sales", "primary_role": "Sales Development", "audience_roles": ["SDR", "Account Executive", "Growth Marketer"], "importance_note": "Combines contact discovery and outreach workflows for outbound revenue teams.", "impact_note": "Helps build targeted prospect lists, enrich records, and run sequenced outreach campaigns.", "rating": 4},
    {"collection_id": "dept-sales", "tool_name": "Clari", "tool_url": "https://www.clari.com/", "short_description": "Revenue operations and forecasting platform for pipeline visibility and deal inspection.", "department": "Sales", "primary_role": "Sales Manager", "audience_roles": ["Sales Manager", "RevOps", "CRO"], "importance_note": "Accurate forecasting and pipeline health require a purpose-built layer on top of CRM data.", "impact_note": "Reduces forecast variance, surfaces at-risk deals earlier, and improves revenue team alignment.", "rating": 5},
    # Operations
    {"collection_id": "dept-operations", "tool_name": "Zapier", "tool_url": "https://zapier.com/", "short_description": "No-code automation platform connecting apps, data, and AI-assisted workflows.", "department": "Operations", "primary_role": "Operations Manager", "audience_roles": ["Ops Manager", "RevOps", "Support Ops", "Founder"], "importance_note": "A broad integration layer helps teams automate repetitive cross-app tasks without custom engineering.", "impact_note": "Reduces manual handoffs for lead routing, notifications, enrichment, reporting, and back-office workflows.", "rating": 5},
    {"collection_id": "dept-operations", "tool_name": "Make", "tool_url": "https://www.make.com/", "short_description": "Visual automation platform for building multi-step app and data workflows.", "department": "Operations", "primary_role": "Automation Specialist", "audience_roles": ["Ops Manager", "Automation Specialist", "Data Ops"], "importance_note": "Visual scenarios make complex automations easier to inspect and maintain than many script-heavy workflows.", "impact_note": "Automates approvals, data sync, notifications, spreadsheet work, and operational process handoffs.", "rating": 4},
    {"collection_id": "dept-operations", "tool_name": "Notion AI", "tool_url": "https://www.notion.com/product/ai", "short_description": "AI-assisted docs, wiki, project notes, summaries, and knowledge workspace features.", "department": "Operations", "primary_role": "Team Lead", "audience_roles": ["Ops Manager", "Project Manager", "Team Lead"], "importance_note": "Adds AI summarization and drafting inside a workspace where team knowledge already lives.", "impact_note": "Speeds meeting notes, project briefs, policy drafts, and knowledge base maintenance.", "rating": 4},
    {"collection_id": "dept-operations", "tool_name": "Linear", "tool_url": "https://linear.app/", "short_description": "Project and issue tracking tool for fast-moving product and engineering teams.", "department": "Operations", "primary_role": "Project Manager", "audience_roles": ["Ops Manager", "Project Manager", "Engineering Lead"], "importance_note": "Lightweight issue tracking keeps execution moving without heavy configuration overhead.", "impact_note": "Improves sprint planning, backlog management, and team velocity visibility.", "rating": 5},
    # Developers
    {"collection_id": "dept-developer", "tool_name": "GitHub Copilot", "tool_url": "https://github.com/features/copilot", "short_description": "AI coding assistant integrated into editors, GitHub, and developer workflows.", "department": "Developers", "primary_role": "Software Engineer", "audience_roles": ["Engineer", "QA Engineer", "Tech Lead"], "importance_note": "Brings code completion, chat, refactoring, and test suggestions directly into the development loop.", "impact_note": "Speeds repetitive coding tasks, scaffolding, test generation, and code navigation.", "rating": 5},
    {"collection_id": "dept-developer", "tool_name": "Cursor", "tool_url": "https://www.cursor.com/", "short_description": "AI-first code editor for codebase chat, edits, refactors, and agentic development.", "department": "Developers", "primary_role": "Software Engineer", "audience_roles": ["Engineer", "Tech Lead", "Founder"], "importance_note": "Codebase-aware editing helps teams make larger changes while staying close to project context.", "impact_note": "Accelerates multi-file edits, code explanations, debugging, and refactoring workflows.", "rating": 5},
    {"collection_id": "dept-developer", "tool_name": "Claude", "tool_url": "https://claude.ai/", "short_description": "AI assistant known for long-context reasoning, writing, analysis, and coding workflows.", "department": "Developers", "primary_role": "Software Engineer", "audience_roles": ["Engineer", "Researcher", "Technical Writer", "Product Manager"], "importance_note": "Long-context reasoning helps with codebase understanding, specifications, research synthesis, and careful writing.", "impact_note": "Supports deeper analysis of large documents, design tradeoffs, code reviews, and implementation planning.", "rating": 5},
    {"collection_id": "dept-developer", "tool_name": "ChatGPT", "tool_url": "https://chatgpt.com/", "short_description": "General AI assistant for coding, writing, analysis, brainstorming, and workflow support.", "department": "Developers", "primary_role": "Software Engineer", "audience_roles": ["Engineer", "Product Manager", "Analyst", "Support Lead"], "importance_note": "A flexible assistant is useful across coding, documentation, debugging, research, and planning tasks.", "impact_note": "Improves first drafts, code explanations, test planning, data analysis, and exploratory problem solving.", "rating": 5},
    # Frontend
    {"collection_id": "dept-frontend", "tool_name": "Figma", "tool_url": "https://www.figma.com/", "short_description": "Collaborative interface design platform with AI-assisted design and handoff features.", "department": "Frontend", "primary_role": "Product Designer", "audience_roles": ["Designer", "Frontend Engineer", "Product Manager"], "importance_note": "Centralizes interface design, prototypes, design systems, and engineering handoff.", "impact_note": "Improves collaboration on product UI, reusable components, specs, and visual QA.", "rating": 5},
    {"collection_id": "dept-frontend", "tool_name": "v0 by Vercel", "tool_url": "https://v0.dev/", "short_description": "AI UI generation tool for React, Tailwind, and frontend component prototyping.", "department": "Frontend", "primary_role": "Frontend Engineer", "audience_roles": ["Frontend Engineer", "Designer", "Product Manager"], "importance_note": "Useful for quickly exploring interface variants and turning product ideas into editable UI code.", "impact_note": "Speeds prototype creation, component exploration, and handoff between design and implementation.", "rating": 4},
    {"collection_id": "dept-frontend", "tool_name": "Storybook", "tool_url": "https://storybook.js.org/", "short_description": "UI component workshop for building, testing, and documenting component libraries.", "department": "Frontend", "primary_role": "Frontend Engineer", "audience_roles": ["Frontend Engineer", "Designer", "QA Engineer"], "importance_note": "Isolated component development reduces coupling and improves visual regression testing.", "impact_note": "Helps teams build consistent design systems, document components, and catch UI bugs earlier.", "rating": 4},
    {"collection_id": "dept-frontend", "tool_name": "Framer", "tool_url": "https://www.framer.com/", "short_description": "Visual website builder for responsive marketing sites, prototypes, and production pages.", "department": "Frontend", "primary_role": "Web Designer", "audience_roles": ["Designer", "Marketing", "Frontend Engineer"], "importance_note": "Helps design and marketing teams ship polished web pages without waiting on every engineering cycle.", "impact_note": "Speeds landing page iteration, portfolio pages, campaign pages, and interactive prototypes.", "rating": 4},
    # Backend
    {"collection_id": "dept-backend", "tool_name": "Postman", "tool_url": "https://www.postman.com/", "short_description": "API collaboration platform for designing, testing, documenting, and monitoring APIs.", "department": "Backend", "primary_role": "Backend Engineer", "audience_roles": ["Backend Engineer", "QA Engineer", "Solutions Engineer"], "importance_note": "API teams need a shared place to verify contracts, examples, authentication, and regression checks.", "impact_note": "Improves API testing, documentation, onboarding, and collaboration across backend and client teams.", "rating": 5},
    {"collection_id": "dept-backend", "tool_name": "Datadog", "tool_url": "https://www.datadoghq.com/", "short_description": "Observability platform for metrics, logs, traces, incident response, and cloud monitoring.", "department": "Backend", "primary_role": "Platform Engineer", "audience_roles": ["Backend Engineer", "SRE", "Platform Engineer"], "importance_note": "Production systems require unified observability to detect, investigate, and prevent reliability issues.", "impact_note": "Improves incident triage, performance debugging, service health visibility, and operational alerting.", "rating": 5},
    {"collection_id": "dept-backend", "tool_name": "Supabase", "tool_url": "https://supabase.com/", "short_description": "Open-source Firebase alternative with Postgres, auth, storage, realtime, and edge functions.", "department": "Backend", "primary_role": "Backend Engineer", "audience_roles": ["Backend Engineer", "Full-Stack Engineer", "Founder"], "importance_note": "A managed Postgres backend with auth and storage reduces the infrastructure to build and maintain.", "impact_note": "Speeds backend setup for new products, APIs, user auth, and file storage workflows.", "rating": 5},
    {"collection_id": "dept-backend", "tool_name": "LangSmith", "tool_url": "https://www.langchain.com/langsmith", "short_description": "LLM application observability, evaluation, tracing, and prompt testing platform.", "department": "Backend", "primary_role": "AI Engineer", "audience_roles": ["AI Engineer", "Backend Engineer", "ML Engineer"], "importance_note": "LLM applications need traces, evaluations, and datasets to improve quality beyond ad hoc prompting.", "impact_note": "Helps debug chains and agents, run evaluations, compare prompts, and monitor production behavior.", "rating": 4},
    # QA & Testing
    {"collection_id": "dept-tester", "tool_name": "Playwright", "tool_url": "https://playwright.dev/", "short_description": "End-to-end browser automation and testing framework for modern web applications.", "department": "QA & Testing", "primary_role": "QA Engineer", "audience_roles": ["QA Engineer", "Frontend Engineer", "SDET"], "importance_note": "Reliable browser automation is foundational for regression coverage across complex user flows.", "impact_note": "Improves cross-browser testing, UI regression checks, trace debugging, and release confidence.", "rating": 5},
    {"collection_id": "dept-tester", "tool_name": "BrowserStack", "tool_url": "https://www.browserstack.com/", "short_description": "Cloud testing platform for browsers, real devices, automation, and visual testing.", "department": "QA & Testing", "primary_role": "QA Engineer", "audience_roles": ["QA Engineer", "Frontend Engineer", "Release Manager"], "importance_note": "Real device and browser coverage is hard to maintain locally, especially for distributed teams.", "impact_note": "Expands test coverage across devices, operating systems, browsers, and automated release pipelines.", "rating": 5},
    {"collection_id": "dept-tester", "tool_name": "Mabl", "tool_url": "https://www.mabl.com/", "short_description": "Low-code intelligent test automation platform for web app quality teams.", "department": "QA & Testing", "primary_role": "QA Lead", "audience_roles": ["QA Lead", "SDET", "Product Manager"], "importance_note": "Low-code testing helps QA teams broaden coverage when engineering bandwidth is limited.", "impact_note": "Supports automated journey testing, regression suites, and faster feedback on product changes.", "rating": 4},
    {"collection_id": "dept-tester", "tool_name": "Checkly", "tool_url": "https://www.checklyhq.com/", "short_description": "Monitoring-as-code platform for API and browser checks, alerting, and synthetic monitoring.", "department": "QA & Testing", "primary_role": "QA Engineer", "audience_roles": ["QA Engineer", "SRE", "Backend Engineer"], "importance_note": "Production monitoring using the same scripts as development tests reduces blind spots in quality coverage.", "impact_note": "Catches regressions in production APIs and user flows before users report them.", "rating": 4},
    # Architecture
    {"collection_id": "dept-architect", "tool_name": "Miro", "tool_url": "https://miro.com/", "short_description": "Collaborative whiteboard for workshops, architecture diagrams, planning, and visual thinking.", "department": "Architecture", "primary_role": "Solution Architect", "audience_roles": ["Architect", "Product Manager", "Engineering Lead"], "importance_note": "Shared visual modeling helps teams align on systems, workflows, dependencies, and tradeoffs.", "impact_note": "Improves architecture workshops, journey maps, system diagrams, and cross-functional planning sessions.", "rating": 4},
    {"collection_id": "dept-architect", "tool_name": "Perplexity", "tool_url": "https://www.perplexity.ai/", "short_description": "AI answer engine for cited research, market scanning, and technical discovery.", "department": "Architecture", "primary_role": "Solution Architect", "audience_roles": ["Architect", "Researcher", "Product Manager"], "importance_note": "Architecture decisions benefit from fast cited research across documentation, vendor pages, and current references.", "impact_note": "Speeds technology comparison, discovery notes, risk review, and source-backed decision preparation.", "rating": 5},
    {"collection_id": "dept-architect", "tool_name": "Structurizr", "tool_url": "https://structurizr.com/", "short_description": "C4 model architecture diagramming tool for documenting software systems as code.", "department": "Architecture", "primary_role": "Solution Architect", "audience_roles": ["Architect", "Tech Lead", "Engineering Manager"], "importance_note": "Architecture documentation that lives in version control stays consistent with the codebase over time.", "impact_note": "Enables teams to produce and maintain system context, container, and component diagrams from a shared model.", "rating": 4},
    {"collection_id": "dept-architect", "tool_name": "AWS Well-Architected Tool", "tool_url": "https://aws.amazon.com/well-architected-tool/", "short_description": "Framework and guided review tool for evaluating cloud architectures against AWS best practices.", "department": "Architecture", "primary_role": "Cloud Architect", "audience_roles": ["Cloud Architect", "Platform Engineer", "CTO"], "importance_note": "Cloud systems need regular review against reliability, security, cost, and operational excellence pillars.", "impact_note": "Surfaces architectural risks, improvement areas, and compliance gaps in AWS workloads.", "rating": 4},
]


async def _seed_default_tools(qdrant: AsyncQdrantClient) -> None:
    async with AsyncSessionLocal() as session:
        existing_names = {
            name.strip().lower()
            for (name,) in (
                await session.execute(
                    select(DocumentDB.tool_name).where(DocumentDB.record_kind == "tool")
                )
            ).all()
            if name
        }
        collection_ids = {
            cid for (cid,) in (await session.execute(select(CollectionDB.id))).all()
        }

        to_add: list[tuple[str, str]] = []
        for item in DEFAULT_TOOLS:
            if item["collection_id"] not in collection_ids:
                continue
            if item["tool_name"].strip().lower() in existing_names:
                continue
            doc = DocumentDB(
                id=str(uuid.uuid4()),
                org_id=settings.default_org_id,
                collection_id=item["collection_id"],
                filename="Tool record",
                file_size=0,
                file_path="",
                status="queued",
                quality="tool",
                chunk_count=0,
                record_kind="tool",
                tool_name=item["tool_name"],
                tool_url=item["tool_url"],
                short_description=item["short_description"],
                department=item["department"],
                primary_role=item["primary_role"],
                audience_roles=",".join(sorted(set(item["audience_roles"]))),
                importance_note=item["importance_note"],
                impact_note=item["impact_note"],
                rating=item["rating"],
            )
            session.add(doc)
            await session.flush()
            to_add.append((doc.id, item["collection_id"]))
            existing_names.add(item["tool_name"].strip().lower())

        await session.commit()

    for doc_id, collection_id in to_add:
        await index_tool_record(
            doc_id=doc_id,
            collection_id=collection_id,
            org_id=settings.default_org_id,
            qdrant_client=qdrant,
        )

    if to_add:
        logger.info("Seeded %d default tools", len(to_add))


LEGACY_COLLECTION_UPDATES = {
    "col-general": {
        "name": "Shared Knowledge",
        "section": "Company Library",
        "description": "General internal references and cross-functional AI tool notes.",
        "color": "#10a37f",
    },
    "col-research": {
        "name": "Research",
        "section": "Company Library",
        "description": "Research papers, benchmarks, and deeper reference material.",
        "color": "#8b5cf6",
    },
    "col-notes": {
        "name": "Meeting Notes",
        "section": "Company Library",
        "description": "Meeting notes, discoveries, and shared team learnings.",
        "color": "#f59e0b",
    },
}


def _create_qdrant_client() -> AsyncQdrantClient:
    if settings.qdrant_url.lower() in {"", "local"}:
        path = Path(settings.qdrant_path).resolve()
        path.mkdir(parents=True, exist_ok=True)
        try:
            return AsyncQdrantClient(path=str(path))
        except RuntimeError as exc:
            message = str(exc)
            if "already accessed by another instance of Qdrant client" not in message:
                raise
            raise RuntimeError(
                f"Embedded Qdrant storage at {path} is already in use. "
                "Stop any other backend process using this repo and restart. "
                "The local Qdrant mode is single-process, so multiple uvicorn instances "
                "or `--reload` against the same data directory can trigger this lock."
            ) from exc
    if settings.qdrant_url == ":memory:":
        return AsyncQdrantClient(location=":memory:")
    return AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.strip() or None,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_tables()
    logger.info("Database ready")

    qdrant = _create_qdrant_client()
    await init_collections(qdrant)
    app.state.qdrant = qdrant
    logger.info("Vector store ready")

    app.state.storage = ensure_storage_ready()
    logger.info("Local storage ready")

    async with AsyncSessionLocal() as session:
        existing_ids = {row[0] for row in (await session.execute(select(CollectionDB.id))).all()}
        for collection_id, attrs in LEGACY_COLLECTION_UPDATES.items():
            if collection_id not in existing_ids:
                continue
            await session.execute(
                update(CollectionDB).where(CollectionDB.id == collection_id).values(**attrs)
            )

        added = 0
        for collection in DEFAULT_COLLECTIONS:
            if collection["id"] in existing_ids:
                continue
            session.add(
                CollectionDB(
                    id=collection["id"],
                    org_id=settings.default_org_id,
                    name=collection["name"],
                    description=collection["description"],
                    color=collection["color"],
                    section=collection["section"],
                    embedding_profile=resolve_embedding_profile(None),
                )
            )
            added += 1

        if added:
            logger.info("Seeded %d default collections", added)
        await session.commit()

    try:
        await _seed_default_tools(qdrant)
    except Exception as exc:
        logger.warning("Default tool seeding skipped: %s", exc)

    yield

    await qdrant.close()
    logger.info("Shutdown complete")


app = FastAPI(title="Tool Knowledge RAG API", version="3.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(upload_router)
app.include_router(collections_router)
app.include_router(events_router)
app.include_router(auth_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
