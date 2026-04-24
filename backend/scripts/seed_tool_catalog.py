from __future__ import annotations

import asyncio
import uuid

from qdrant_client import AsyncQdrantClient
from sqlalchemy import select

from app.config import settings
from app.db import AsyncSessionLocal, CollectionDB, DocumentDB, create_tables
from app.ingestion.pipeline import index_tool_record
from app.retrieval.qdrant import init_collections


TOOLS = [
    {
        "collection_id": "dept-hr",
        "tool_name": "Rippling",
        "tool_url": "https://www.rippling.com/",
        "short_description": "Unified HR, IT, payroll, benefits, and workforce automation platform.",
        "department": "HR",
        "primary_role": "People Operations",
        "audience_roles": ["HR Manager", "IT Admin", "Finance Ops"],
        "importance_note": "Centralizes employee lifecycle work that normally spans HR, IT, payroll, and compliance systems.",
        "impact_note": "Reduces manual onboarding and offboarding steps, improves policy consistency, and keeps employee data synchronized.",
        "rating": 5,
    },
    {
        "collection_id": "dept-hr",
        "tool_name": "Deel",
        "tool_url": "https://www.deel.com/",
        "short_description": "Global hiring, payroll, contractor management, and compliance platform.",
        "department": "HR",
        "primary_role": "Global HR",
        "audience_roles": ["HR Manager", "Finance Ops", "Founder"],
        "importance_note": "Useful for teams hiring across countries without building local legal and payroll infrastructure.",
        "impact_note": "Speeds international onboarding while helping teams manage contracts, payroll, and compliance in one place.",
        "rating": 5,
    },
    {
        "collection_id": "dept-hr",
        "tool_name": "Greenhouse",
        "tool_url": "https://www.greenhouse.com/",
        "short_description": "Applicant tracking and structured hiring platform for recruiting teams.",
        "department": "HR",
        "primary_role": "Recruiter",
        "audience_roles": ["Recruiter", "Hiring Manager", "People Ops"],
        "importance_note": "Structured hiring workflows help growing teams evaluate candidates more consistently.",
        "impact_note": "Improves pipeline visibility, interview coordination, and candidate feedback loops.",
        "rating": 4,
    },
    {
        "collection_id": "dept-marketing",
        "tool_name": "Jasper",
        "tool_url": "https://www.jasper.ai/",
        "short_description": "AI writing and campaign content platform for brand-aligned marketing teams.",
        "department": "Marketing",
        "primary_role": "Content Marketer",
        "audience_roles": ["Content Marketer", "Demand Gen", "Brand Manager"],
        "importance_note": "Helps teams draft campaign assets while maintaining reusable brand voice and messaging patterns.",
        "impact_note": "Accelerates blog, ad, email, and landing page drafts for human editing and approval.",
        "rating": 4,
    },
    {
        "collection_id": "dept-marketing",
        "tool_name": "Canva",
        "tool_url": "https://www.canva.com/",
        "short_description": "Visual design platform with AI-assisted creative production for teams.",
        "department": "Marketing",
        "primary_role": "Designer",
        "audience_roles": ["Designer", "Social Media Manager", "Marketing Generalist"],
        "importance_note": "Gives non-designers a fast way to produce on-brand graphics, decks, and campaign assets.",
        "impact_note": "Reduces creative bottlenecks for social posts, presentations, ads, and lightweight collateral.",
        "rating": 5,
    },
    {
        "collection_id": "dept-marketing",
        "tool_name": "Surfer SEO",
        "tool_url": "https://surferseo.com/",
        "short_description": "SEO content planning and optimization platform for search-driven teams.",
        "department": "Marketing",
        "primary_role": "SEO Specialist",
        "audience_roles": ["SEO Specialist", "Content Marketer", "Growth Marketer"],
        "importance_note": "Connects content production with search intent, keyword coverage, and competitive page structure.",
        "impact_note": "Helps prioritize content briefs, improve existing articles, and make SEO recommendations more repeatable.",
        "rating": 4,
    },
    {
        "collection_id": "dept-marketing",
        "tool_name": "HubSpot Marketing Hub",
        "tool_url": "https://www.hubspot.com/products/marketing",
        "short_description": "Marketing automation, email, landing page, lead capture, and campaign reporting platform.",
        "department": "Marketing",
        "primary_role": "Marketing Operations",
        "audience_roles": ["Marketing Ops", "Demand Gen", "Sales Ops"],
        "importance_note": "Connects campaign execution with CRM data so teams can attribute leads and nurture prospects.",
        "impact_note": "Improves lead capture, segmentation, email automation, and campaign reporting across the funnel.",
        "rating": 5,
    },
    {
        "collection_id": "dept-sales",
        "tool_name": "Salesforce Einstein",
        "tool_url": "https://www.salesforce.com/artificial-intelligence/",
        "short_description": "AI features across Salesforce for sales forecasting, recommendations, and CRM workflows.",
        "department": "Sales",
        "primary_role": "Sales Operations",
        "audience_roles": ["Account Executive", "Sales Manager", "RevOps"],
        "importance_note": "Adds AI assistance to the CRM system many revenue teams already use daily.",
        "impact_note": "Supports forecasting, account prioritization, next-best actions, and customer interaction summaries.",
        "rating": 5,
    },
    {
        "collection_id": "dept-sales",
        "tool_name": "Gong",
        "tool_url": "https://www.gong.io/",
        "short_description": "Revenue intelligence platform for call recording, deal insights, coaching, and forecasting.",
        "department": "Sales",
        "primary_role": "Sales Manager",
        "audience_roles": ["Account Executive", "Sales Manager", "Customer Success"],
        "importance_note": "Turns sales conversations into searchable signals for coaching, deal risk, and pipeline inspection.",
        "impact_note": "Improves rep coaching, follow-up quality, objection tracking, and forecast confidence.",
        "rating": 5,
    },
    {
        "collection_id": "dept-sales",
        "tool_name": "Apollo.io",
        "tool_url": "https://www.apollo.io/",
        "short_description": "B2B prospecting, enrichment, sequencing, and sales engagement platform.",
        "department": "Sales",
        "primary_role": "Sales Development",
        "audience_roles": ["SDR", "Account Executive", "Growth Marketer"],
        "importance_note": "Combines contact discovery and outreach workflows for outbound revenue teams.",
        "impact_note": "Helps build targeted prospect lists, enrich records, and run sequenced outreach campaigns.",
        "rating": 4,
    },
    {
        "collection_id": "dept-operations",
        "tool_name": "Zapier",
        "tool_url": "https://zapier.com/",
        "short_description": "No-code automation platform connecting apps, data, and AI-assisted workflows.",
        "department": "Operations",
        "primary_role": "Operations Manager",
        "audience_roles": ["Ops Manager", "RevOps", "Support Ops", "Founder"],
        "importance_note": "A broad integration layer helps teams automate repetitive cross-app tasks without custom engineering.",
        "impact_note": "Reduces manual handoffs for lead routing, notifications, enrichment, reporting, and back-office workflows.",
        "rating": 5,
    },
    {
        "collection_id": "dept-operations",
        "tool_name": "Make",
        "tool_url": "https://www.make.com/",
        "short_description": "Visual automation platform for building multi-step app and data workflows.",
        "department": "Operations",
        "primary_role": "Automation Specialist",
        "audience_roles": ["Ops Manager", "Automation Specialist", "Data Ops"],
        "importance_note": "Visual scenarios make complex automations easier to inspect and maintain than many script-heavy workflows.",
        "impact_note": "Automates approvals, data sync, notifications, spreadsheet work, and operational process handoffs.",
        "rating": 4,
    },
    {
        "collection_id": "dept-operations",
        "tool_name": "Notion AI",
        "tool_url": "https://www.notion.com/product/ai",
        "short_description": "AI-assisted docs, wiki, project notes, summaries, and knowledge workspace features.",
        "department": "Operations",
        "primary_role": "Team Lead",
        "audience_roles": ["Ops Manager", "Project Manager", "Team Lead"],
        "importance_note": "Adds AI summarization and drafting inside a workspace where team knowledge already lives.",
        "impact_note": "Speeds meeting notes, project briefs, policy drafts, and knowledge base maintenance.",
        "rating": 4,
    },
    {
        "collection_id": "dept-operations",
        "tool_name": "Airtable AI",
        "tool_url": "https://www.airtable.com/platform/ai",
        "short_description": "AI features inside Airtable for operational databases, workflows, and lightweight apps.",
        "department": "Operations",
        "primary_role": "Operations Manager",
        "audience_roles": ["Ops Manager", "Project Manager", "Data Ops"],
        "importance_note": "Useful when teams manage structured operational data but need AI-assisted classification and generation.",
        "impact_note": "Helps summarize records, categorize requests, generate content, and build team-specific workflows.",
        "rating": 4,
    },
    {
        "collection_id": "dept-developer",
        "tool_name": "ChatGPT",
        "tool_url": "https://chatgpt.com/",
        "short_description": "General AI assistant for coding, writing, analysis, brainstorming, and workflow support.",
        "department": "Developers",
        "primary_role": "Software Engineer",
        "audience_roles": ["Engineer", "Product Manager", "Analyst", "Support Lead"],
        "importance_note": "A flexible assistant is useful across coding, documentation, debugging, research, and planning tasks.",
        "impact_note": "Improves first drafts, code explanations, test planning, data analysis, and exploratory problem solving.",
        "rating": 5,
    },
    {
        "collection_id": "dept-developer",
        "tool_name": "Claude",
        "tool_url": "https://claude.ai/",
        "short_description": "AI assistant known for long-context reasoning, writing, analysis, and coding workflows.",
        "department": "Developers",
        "primary_role": "Software Engineer",
        "audience_roles": ["Engineer", "Researcher", "Technical Writer", "Product Manager"],
        "importance_note": "Long-context reasoning helps with codebase understanding, specifications, research synthesis, and careful writing.",
        "impact_note": "Supports deeper analysis of large documents, design tradeoffs, code reviews, and implementation planning.",
        "rating": 5,
    },
    {
        "collection_id": "dept-developer",
        "tool_name": "GitHub Copilot",
        "tool_url": "https://github.com/features/copilot",
        "short_description": "AI coding assistant integrated into editors, GitHub, and developer workflows.",
        "department": "Developers",
        "primary_role": "Software Engineer",
        "audience_roles": ["Engineer", "QA Engineer", "Tech Lead"],
        "importance_note": "Brings code completion, chat, refactoring, and test suggestions directly into the development loop.",
        "impact_note": "Speeds repetitive coding tasks, scaffolding, test generation, and code navigation.",
        "rating": 5,
    },
    {
        "collection_id": "dept-developer",
        "tool_name": "Cursor",
        "tool_url": "https://www.cursor.com/",
        "short_description": "AI-first code editor for codebase chat, edits, refactors, and agentic development.",
        "department": "Developers",
        "primary_role": "Software Engineer",
        "audience_roles": ["Engineer", "Tech Lead", "Founder"],
        "importance_note": "Codebase-aware editing helps teams make larger changes while staying close to project context.",
        "impact_note": "Accelerates multi-file edits, code explanations, debugging, and refactoring workflows.",
        "rating": 5,
    },
    {
        "collection_id": "dept-frontend",
        "tool_name": "v0 by Vercel",
        "tool_url": "https://v0.dev/",
        "short_description": "AI UI generation tool for React, Tailwind, and frontend component prototyping.",
        "department": "Frontend",
        "primary_role": "Frontend Engineer",
        "audience_roles": ["Frontend Engineer", "Designer", "Product Manager"],
        "importance_note": "Useful for quickly exploring interface variants and turning product ideas into editable UI code.",
        "impact_note": "Speeds prototype creation, component exploration, and handoff between design and implementation.",
        "rating": 4,
    },
    {
        "collection_id": "dept-frontend",
        "tool_name": "Figma",
        "tool_url": "https://www.figma.com/",
        "short_description": "Collaborative interface design platform with AI-assisted design and handoff features.",
        "department": "Frontend",
        "primary_role": "Product Designer",
        "audience_roles": ["Designer", "Frontend Engineer", "Product Manager"],
        "importance_note": "Centralizes interface design, prototypes, design systems, and engineering handoff.",
        "impact_note": "Improves collaboration on product UI, reusable components, specs, and visual QA.",
        "rating": 5,
    },
    {
        "collection_id": "dept-frontend",
        "tool_name": "Framer",
        "tool_url": "https://www.framer.com/",
        "short_description": "Visual website builder for responsive marketing sites, prototypes, and production pages.",
        "department": "Frontend",
        "primary_role": "Web Designer",
        "audience_roles": ["Designer", "Marketing", "Frontend Engineer"],
        "importance_note": "Helps design and marketing teams ship polished web pages without waiting on every engineering cycle.",
        "impact_note": "Speeds landing page iteration, portfolio pages, campaign pages, and interactive prototypes.",
        "rating": 4,
    },
    {
        "collection_id": "dept-frontend",
        "tool_name": "Lovable",
        "tool_url": "https://lovable.dev/",
        "short_description": "AI app builder for generating full-stack web app prototypes from natural language.",
        "department": "Frontend",
        "primary_role": "Product Builder",
        "audience_roles": ["Founder", "Product Manager", "Frontend Engineer"],
        "importance_note": "Helps teams turn early product ideas into working prototypes quickly enough to validate direction.",
        "impact_note": "Compresses idea-to-demo cycles for MVPs, internal tools, and product experiments.",
        "rating": 4,
    },
    {
        "collection_id": "dept-backend",
        "tool_name": "Postman",
        "tool_url": "https://www.postman.com/",
        "short_description": "API collaboration platform for designing, testing, documenting, and monitoring APIs.",
        "department": "Backend",
        "primary_role": "Backend Engineer",
        "audience_roles": ["Backend Engineer", "QA Engineer", "Solutions Engineer"],
        "importance_note": "API teams need a shared place to verify contracts, examples, authentication, and regression checks.",
        "impact_note": "Improves API testing, documentation, onboarding, and collaboration across backend and client teams.",
        "rating": 5,
    },
    {
        "collection_id": "dept-backend",
        "tool_name": "Datadog",
        "tool_url": "https://www.datadoghq.com/",
        "short_description": "Observability platform for metrics, logs, traces, incident response, and cloud monitoring.",
        "department": "Backend",
        "primary_role": "Platform Engineer",
        "audience_roles": ["Backend Engineer", "SRE", "Platform Engineer"],
        "importance_note": "Production systems require unified observability to detect, investigate, and prevent reliability issues.",
        "impact_note": "Improves incident triage, performance debugging, service health visibility, and operational alerting.",
        "rating": 5,
    },
    {
        "collection_id": "dept-backend",
        "tool_name": "LangSmith",
        "tool_url": "https://www.langchain.com/langsmith",
        "short_description": "LLM application observability, evaluation, tracing, and prompt testing platform.",
        "department": "Backend",
        "primary_role": "AI Engineer",
        "audience_roles": ["AI Engineer", "Backend Engineer", "ML Engineer"],
        "importance_note": "LLM applications need traces, evaluations, and datasets to improve quality beyond ad hoc prompting.",
        "impact_note": "Helps debug chains and agents, run evaluations, compare prompts, and monitor production behavior.",
        "rating": 4,
    },
    {
        "collection_id": "dept-tester",
        "tool_name": "Playwright",
        "tool_url": "https://playwright.dev/",
        "short_description": "End-to-end browser automation and testing framework for modern web applications.",
        "department": "QA & Testing",
        "primary_role": "QA Engineer",
        "audience_roles": ["QA Engineer", "Frontend Engineer", "SDET"],
        "importance_note": "Reliable browser automation is foundational for regression coverage across complex user flows.",
        "impact_note": "Improves cross-browser testing, UI regression checks, trace debugging, and release confidence.",
        "rating": 5,
    },
    {
        "collection_id": "dept-tester",
        "tool_name": "BrowserStack",
        "tool_url": "https://www.browserstack.com/",
        "short_description": "Cloud testing platform for browsers, real devices, automation, and visual testing.",
        "department": "QA & Testing",
        "primary_role": "QA Engineer",
        "audience_roles": ["QA Engineer", "Frontend Engineer", "Release Manager"],
        "importance_note": "Real device and browser coverage is hard to maintain locally, especially for distributed teams.",
        "impact_note": "Expands test coverage across devices, operating systems, browsers, and automated release pipelines.",
        "rating": 5,
    },
    {
        "collection_id": "dept-tester",
        "tool_name": "Mabl",
        "tool_url": "https://www.mabl.com/",
        "short_description": "Low-code intelligent test automation platform for web app quality teams.",
        "department": "QA & Testing",
        "primary_role": "QA Lead",
        "audience_roles": ["QA Lead", "SDET", "Product Manager"],
        "importance_note": "Low-code testing helps QA teams broaden coverage when engineering bandwidth is limited.",
        "impact_note": "Supports automated journey testing, regression suites, and faster feedback on product changes.",
        "rating": 4,
    },
    {
        "collection_id": "dept-architect",
        "tool_name": "Perplexity",
        "tool_url": "https://www.perplexity.ai/",
        "short_description": "AI answer engine for cited research, market scanning, and technical discovery.",
        "department": "Architecture",
        "primary_role": "Solution Architect",
        "audience_roles": ["Architect", "Researcher", "Product Manager"],
        "importance_note": "Architecture decisions benefit from fast cited research across documentation, vendor pages, and current references.",
        "impact_note": "Speeds technology comparison, discovery notes, risk review, and source-backed decision preparation.",
        "rating": 5,
    },
    {
        "collection_id": "dept-architect",
        "tool_name": "Miro",
        "tool_url": "https://miro.com/",
        "short_description": "Collaborative whiteboard for workshops, architecture diagrams, planning, and visual thinking.",
        "department": "Architecture",
        "primary_role": "Solution Architect",
        "audience_roles": ["Architect", "Product Manager", "Engineering Lead"],
        "importance_note": "Shared visual modeling helps teams align on systems, workflows, dependencies, and tradeoffs.",
        "impact_note": "Improves architecture workshops, journey maps, system diagrams, and cross-functional planning sessions.",
        "rating": 4,
    },
]


async def main() -> None:
    await create_tables()
    qdrant = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.strip() or None,
    )
    await init_collections(qdrant)

    added: list[tuple[str, str]] = []
    skipped: list[str] = []

    async with AsyncSessionLocal() as session:
        existing = {
            name.strip().lower()
            for (name,) in (
                await session.execute(
                    select(DocumentDB.tool_name).where(DocumentDB.record_kind == "tool")
                )
            ).all()
            if name
        }
        collection_ids = {
            cid
            for (cid,) in (await session.execute(select(CollectionDB.id))).all()
        }

        for item in TOOLS:
            if item["collection_id"] not in collection_ids:
                raise RuntimeError(f"Missing collection: {item['collection_id']}")
            if item["tool_name"].strip().lower() in existing:
                skipped.append(item["tool_name"])
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
            added.append((doc.id, doc.tool_name))
            existing.add(item["tool_name"].strip().lower())

        await session.commit()

    for doc_id, _tool_name in added:
        await index_tool_record(
            doc_id=doc_id,
            collection_id=next(item["collection_id"] for item in TOOLS if item["tool_name"] == _tool_name),
            org_id=settings.default_org_id,
            qdrant_client=qdrant,
        )

    await qdrant.close()
    print(f"Added {len(added)} tools")
    if skipped:
        print(f"Skipped {len(skipped)} existing tools: {', '.join(skipped)}")


if __name__ == "__main__":
    asyncio.run(main())
