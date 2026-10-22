import uuid
import pytest
import pytest_asyncio
from agent.core.database import AsyncSessionLocal
from agent.models import Website, Recommendation
from agent.automation.scheduler import continuous_loop

@pytest.mark.asyncio
async def test_run_site_cycle_idempotence():
    # Setup test website
    domain = f"cycle_{uuid.uuid4().hex[:8]}.org"
    async with AsyncSessionLocal() as db:
        site = Website(domain=domain, name="Cycle Test Site", automation_mode="recommendation")
        db.add(site)
        await db.commit()
        await db.refresh(site)
        site_id = site.id

        # Insert pre-existing duplicate recommendations to simulate legacy dirty database state
        for _ in range(2):
            rec = Recommendation(
                website_id=site_id,
                url=f"https://{domain}/page1",
                issue_title="missing_meta_description",
                severity="high",
                proposed_fix="Add meta description",
                status="suggested"
            )
            db.add(rec)
        await db.commit()

    # Now execute run_site_cycle - it must succeed cleanly without MultipleResultsFound or MissingGreenlet
    await continuous_loop.run_site_cycle(site_id)

    # Execute a second time to ensure complete idempotency
    await continuous_loop.run_site_cycle(site_id)
