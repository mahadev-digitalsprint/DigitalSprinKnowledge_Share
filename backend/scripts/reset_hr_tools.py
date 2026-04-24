from __future__ import annotations

import asyncio
import uuid

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sqlalchemy import delete, func, select, update

from app.config import settings
from app.core.registry import list_document_embedding_profiles
from app.db import AsyncSessionLocal, CollectionDB, DocumentDB, create_tables
from app.ingestion.pipeline import index_tool_record
from app.retrieval.qdrant import init_collections


HR_TOOLS = [
    ("Rippling", "https://www.rippling.com/", "Unified HR, IT, payroll, benefits, and workforce automation for fast-growing teams.", "HR Operations", "HRIS Manager", "Automates employee lifecycle workflows across HR, IT, finance, identity, and device management.", "Best for companies that want onboarding, payroll, app access, and compliance tasks coordinated from one workforce platform.", 5),
    ("Deel", "https://www.deel.com/", "Global HR, contractor management, employer-of-record, payroll, and compliance platform.", "Global HR", "Global Mobility Lead", "Helps distributed teams hire and pay employees or contractors across countries with less local infrastructure.", "Best for international hiring, localized contracts, global payroll, immigration support, and compliance workflows.", 5),
    ("BambooHR", "https://www.bamboohr.com/", "SMB-friendly HRIS for employee records, hiring, onboarding, time off, reporting, and performance.", "Core HR", "HR Manager", "Gives growing HR teams a clean system of record without enterprise implementation weight.", "Best for centralizing employee data, PTO, onboarding documents, lightweight hiring, and people reports.", 5),
    ("Gusto", "https://gusto.com/", "Payroll-first HR platform for small businesses with benefits, onboarding, and compliance support.", "Payroll & Benefits", "Payroll Manager", "Combines payroll, tax filings, benefits, and basic HR workflows for small teams.", "Best for US SMBs that need reliable payroll plus simple employee self-service and benefits administration.", 5),
    ("Workday HCM", "https://www.workday.com/en-us/products/human-capital-management/overview.html", "Enterprise human capital management suite for workforce planning, payroll, talent, and analytics.", "Enterprise HR", "HR Director", "Provides a deep system of record and analytics layer for complex, global organizations.", "Best for enterprise HR teams managing workforce data, talent processes, compensation, and compliance at scale.", 5),
    ("SAP SuccessFactors", "https://www.sap.com/products/hcm.html", "Cloud HCM suite for core HR, payroll, talent, learning, workforce planning, and enterprise compliance.", "Enterprise HR", "HR Transformation Lead", "Supports large organizations that need configurable HR processes across regions and business units.", "Best for enterprise talent management, global HR operations, performance, learning, and workforce analytics.", 4),
    ("UKG Ready", "https://www.ukg.com/solutions/ukg-ready", "HR, payroll, time, attendance, scheduling, and workforce management platform for SMB and mid-market teams.", "Workforce Management", "HR Operations Manager", "Connects people operations with timekeeping and scheduling, especially for hourly or shift-based workforces.", "Best for organizations that need payroll, compliance, scheduling, and workforce visibility in one platform.", 4),
    ("HiBob", "https://www.hibob.com/", "Modern HR platform for employee engagement, culture, performance, compensation, and hybrid teams.", "Employee Experience", "People Partner", "Focuses on employee experience while still covering core HR workflows and people analytics.", "Best for scaling companies that want stronger engagement, manager visibility, and modern self-service HR.", 4),
    ("Personio", "https://www.personio.com/", "European HR software for recruiting, core HR, payroll preparation, time tracking, and workflows.", "Core HR", "HR Generalist", "Fits European SMB and mid-market companies that need localized HR process coverage.", "Best for employee records, hiring, absence management, payroll preparation, and HR workflow automation.", 4),
    ("Sage HR", "https://www.sage.com/en-us/products/sage-hr/", "Modular HR system for leave management, performance, timesheets, recruitment, and employee self-service.", "Core HR", "HR Administrator", "Offers a straightforward HR stack for small and midsize teams that prefer modular adoption.", "Best for leave tracking, employee records, performance workflows, and simple HR administration.", 4),
    ("Factorial", "https://factorialhr.com/", "HR platform for SMBs covering time, talent, documents, finance workflows, and HR automation.", "HR Operations", "People Operations Manager", "Combines everyday HR administration with automation and reporting for lean people teams.", "Best for onboarding, document management, time tracking, performance reviews, and HR process coordination.", 4),
    ("Zoho People", "https://www.zoho.com/people/", "HR management platform for employee records, attendance, leave, performance, learning, and workflows.", "Core HR", "HR Generalist", "Works well for teams already using Zoho or needing configurable HR workflows at SMB cost.", "Best for employee self-service, attendance, leave workflows, case tracking, and basic people operations.", 4),
    ("ADP Workforce Now", "https://www.adp.com/what-we-offer/products/adp-workforce-now.aspx", "Payroll, HR, benefits, talent, time, and compliance platform for mid-sized businesses.", "Payroll & Benefits", "Payroll Director", "ADP's payroll depth and compliance coverage make it useful for regulated, payroll-heavy teams.", "Best for payroll operations, benefits administration, tax compliance, time tracking, and HR reporting.", 5),
    ("Paycor", "https://www.paycor.com/", "HCM platform for payroll, HR, talent, workforce management, analytics, and employee experience.", "Payroll & Benefits", "HR Operations Manager", "Combines payroll and talent workflows for SMB and mid-market organizations.", "Best for payroll processing, recruiting, onboarding, scheduling, performance, and analytics.", 4),
    ("Paylocity", "https://www.paylocity.com/", "HR and payroll platform with employee experience, time, talent, benefits, and workforce analytics.", "Payroll & Benefits", "Payroll Manager", "Blends payroll operations with employee communication and engagement capabilities.", "Best for payroll, benefits, workforce management, employee self-service, and internal communications.", 4),
    ("Greenhouse", "https://www.greenhouse.com/", "Applicant tracking system for structured hiring, interview plans, reporting, and recruiting operations.", "Recruiting", "Recruiting Lead", "Brings process consistency and analytics to high-growth recruiting teams.", "Best for structured interviews, scorecards, candidate pipelines, hiring team coordination, and recruiting reports.", 5),
    ("Lever", "https://www.lever.co/", "Talent acquisition suite combining ATS and CRM workflows for sourcing-heavy recruiting teams.", "Recruiting", "Talent Acquisition Manager", "Helps recruiters manage both active applicants and long-term candidate relationship pipelines.", "Best for sourcing, nurturing candidates, interview coordination, and recruiting pipeline visibility.", 4),
    ("Workable", "https://www.workable.com/", "Recruiting software for job posting, candidate sourcing, applicant tracking, and hiring workflows.", "Recruiting", "Recruiter", "Gives lean recruiting teams broad hiring functionality without a complex ATS rollout.", "Best for posting roles, screening applicants, managing interviews, and moving candidates through hiring stages.", 4),
    ("SmartRecruiters", "https://www.smartrecruiters.com/", "Enterprise talent acquisition platform for recruitment marketing, applicant tracking, and hiring collaboration.", "Recruiting", "Talent Acquisition Director", "Supports large recruiting teams that need scalable hiring workflows and marketplace integrations.", "Best for high-volume recruiting, hiring collaboration, candidate experience, and recruitment analytics.", 4),
    ("Ashby", "https://www.ashbyhq.com/", "Recruiting platform for ATS, scheduling, sourcing, CRM, analytics, and headcount planning.", "Recruiting", "Recruiting Operations", "Combines modern recruiting workflows with strong analytics for data-driven hiring teams.", "Best for fast-growing companies that want pipeline analytics, structured hiring, and recruiting operations in one system.", 4),
    ("Paradox", "https://www.paradox.ai/", "Conversational recruiting assistant for candidate screening, scheduling, communication, and high-volume hiring.", "Recruiting Automation", "Recruiting Operations", "Automates repetitive candidate communication and scheduling tasks that slow recruiting teams down.", "Best for hourly hiring, high-volume recruiting, interview scheduling, and candidate FAQ automation.", 4),
    ("Eightfold AI", "https://eightfold.ai/", "Talent intelligence platform for matching candidates and employees to roles, skills, and opportunities.", "Talent Intelligence", "Talent Strategy Lead", "Uses skills and career data to support recruiting, internal mobility, and workforce planning.", "Best for enterprises improving talent matching, diversity pipelines, internal mobility, and skills-based planning.", 4),
    ("Phenom", "https://www.phenom.com/", "Talent experience platform covering career sites, CRM, recruiting automation, and employee experience.", "Talent Experience", "Talent Acquisition Director", "Connects candidate experience, recruiter productivity, and employee mobility workflows.", "Best for personalized career sites, candidate engagement, recruitment marketing, and internal talent marketplaces.", 4),
    ("Beamery", "https://beamery.com/", "Talent lifecycle management platform for skills intelligence, workforce planning, CRM, and internal mobility.", "Talent Management", "Workforce Planning Lead", "Helps enterprises understand skills supply and connect people to future business needs.", "Best for strategic workforce planning, talent CRM, skills mapping, succession planning, and redeployment.", 4),
    ("HireVue", "https://www.hirevue.com/", "Video interviewing and assessment platform for structured screening and hiring decision support.", "Interviewing", "Recruiting Lead", "Standardizes early-stage interviews and assessments for distributed or high-volume hiring teams.", "Best for video interviews, job-relevant assessments, structured screening, and candidate evaluation consistency.", 4),
    ("Textio", "https://textio.com/", "Augmented writing platform for inclusive job posts, recruiting emails, and HR communications.", "Recruiting Content", "Recruiter", "Improves the clarity, inclusivity, and effectiveness of job descriptions and candidate outreach.", "Best for reducing biased language, improving job post performance, and standardizing recruiting communication quality.", 4),
    ("Lattice", "https://lattice.com/", "People management platform for performance reviews, goals, engagement, compensation, and growth.", "Performance Management", "People Partner", "Connects manager feedback, goals, engagement, and compensation conversations in one people platform.", "Best for performance cycles, OKRs, 1:1s, engagement surveys, career growth, and compensation planning.", 5),
    ("Culture Amp", "https://www.cultureamp.com/", "Employee experience platform for engagement surveys, performance, development, and people analytics.", "Employee Engagement", "Employee Experience Lead", "Turns employee feedback into insights and action plans for managers and HR leaders.", "Best for engagement surveys, lifecycle surveys, performance feedback, development planning, and culture analytics.", 5),
    ("15Five", "https://www.15five.com/", "Performance management platform for check-ins, goals, feedback, recognition, and manager effectiveness.", "Performance Management", "People Manager", "Promotes continuous feedback habits instead of relying only on annual review cycles.", "Best for weekly check-ins, manager coaching, objectives, recognition, and lightweight performance conversations.", 4),
    ("Leapsome", "https://www.leapsome.com/", "People enablement platform for performance, engagement, learning, goals, and compensation workflows.", "People Enablement", "People Operations Manager", "Brings performance, engagement, and development workflows together for growing organizations.", "Best for review cycles, employee engagement, learning paths, goals, feedback, and compensation calibration.", 4),
]


def _audience_for(category: str) -> list[str]:
    defaults = ["HR Manager", "People Operations", "HR Business Partner"]
    by_category = {
        "Recruiting": ["Recruiter", "Hiring Manager", "Recruiting Operations"],
        "Recruiting Automation": ["Recruiter", "Recruiting Operations", "Hiring Manager"],
        "Recruiting Content": ["Recruiter", "Employer Brand", "DEI Lead"],
        "Payroll & Benefits": ["Payroll Manager", "Benefits Manager", "Finance Ops"],
        "Performance Management": ["People Partner", "Manager", "HR Director"],
        "Employee Engagement": ["Employee Experience Lead", "People Partner", "Manager"],
        "Enterprise HR": ["HR Director", "HRIS Manager", "People Analytics"],
    }
    return by_category.get(category, defaults)


async def _delete_tool_vectors(qdrant: AsyncQdrantClient) -> None:
    tool_filter = Filter(
        must=[
            FieldCondition(key="org_id", match=MatchValue(value=settings.default_org_id)),
            FieldCondition(key="record_kind", match=MatchValue(value="tool")),
        ]
    )
    for profile in list_document_embedding_profiles().values():
        if await qdrant.collection_exists(profile.qdrant_collection):
            await qdrant.delete(
                collection_name=profile.qdrant_collection,
                points_selector=tool_filter,
                wait=True,
            )


async def main() -> None:
    await create_tables()
    qdrant = AsyncQdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key.strip() or None,
    )
    await init_collections(qdrant)
    await _delete_tool_vectors(qdrant)

    async with AsyncSessionLocal() as session:
        hr_collection = await session.get(CollectionDB, "dept-hr")
        if hr_collection is None:
            raise RuntimeError("Missing HR collection: dept-hr")

        await session.execute(delete(DocumentDB).where(DocumentDB.record_kind == "tool"))
        await session.execute(update(CollectionDB).values(doc_count=0))
        await session.commit()

        docs: list[DocumentDB] = []
        for name, url, description, category, role, importance, impact, rating in HR_TOOLS:
            doc = DocumentDB(
                id=str(uuid.uuid4()),
                org_id=settings.default_org_id,
                collection_id=hr_collection.id,
                filename="Tool record",
                file_size=0,
                file_path="",
                status="queued",
                quality="tool",
                chunk_count=0,
                record_kind="tool",
                tool_name=name,
                tool_url=url,
                short_description=description,
                department=f"HR - {category}",
                primary_role=role,
                audience_roles=",".join(_audience_for(category)),
                importance_note=importance,
                impact_note=impact,
                rating=rating,
            )
            session.add(doc)
            docs.append(doc)
        await session.commit()

    for doc in docs:
        await index_tool_record(
            doc_id=doc.id,
            collection_id=doc.collection_id,
            org_id=settings.default_org_id,
            qdrant_client=qdrant,
        )

    async with AsyncSessionLocal() as session:
        for collection_id, count in (
            await session.execute(
                select(DocumentDB.collection_id, func.count(DocumentDB.id)).group_by(DocumentDB.collection_id)
            )
        ).all():
            await session.execute(
                update(CollectionDB).where(CollectionDB.id == collection_id).values(doc_count=count)
            )
        await session.commit()

    await qdrant.close()
    print(f"Reset catalog to {len(HR_TOOLS)} HR tools")


if __name__ == "__main__":
    asyncio.run(main())
