import pytest
import pytest_asyncio
from agent.core.database import init_db

@pytest_asyncio.fixture(autouse=True)
async def setup_test_database():
    await init_db()
    yield
