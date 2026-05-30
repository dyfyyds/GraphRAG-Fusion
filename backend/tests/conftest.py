import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def client():
    from httpx import Client, ASGITransport
    transport = ASGITransport(app=app)
    with Client(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
