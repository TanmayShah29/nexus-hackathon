"""
test_routes.py — Tests for API Routes
"""

import pytest
from fastapi import HTTPException
from nexus.config import get_nexus_api_key

NEXUS_API_KEY = get_nexus_api_key()
AUTH_HEADER = f"Bearer {NEXUS_API_KEY}"


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_response(self):
        from nexus.routes.system import health

        response = await health(authorization=AUTH_HEADER)

        assert response.status in ["ok", "degraded"]
        assert response.version == "1.0.0"
        assert response.agents_loaded > 0


class TestAgentsEndpoint:
    @pytest.mark.asyncio
    async def test_get_agents(self):
        from nexus.routes.system import get_agents

        response = await get_agents(authorization=AUTH_HEADER)

        assert response.total > 0
        assert len(response.agents) == response.total

    @pytest.mark.asyncio
    async def test_get_agent_valid(self):
        from nexus.routes.system import get_agent

        response = await get_agent("atlas", authorization=AUTH_HEADER)

        assert response.name == "atlas"
        assert response.display_name == "Atlas"

    @pytest.mark.asyncio
    async def test_get_agent_invalid(self):
        from nexus.routes.system import get_agent

        with pytest.raises(HTTPException) as exc:
            await get_agent("nonexistent_agent", authorization=AUTH_HEADER)
        assert exc.value.status_code == 404


class TestSecurityUtils:
    def test_rate_limit_allows_first_requests(self):
        from nexus.utils.security import check_rate_limit
        import uuid

        client_id = f"test-{uuid.uuid4()}"
        result = check_rate_limit(client_id)

        assert result is True

    def test_rate_limit_tracks_requests(self):
        from nexus.utils.security import check_rate_limit
        import uuid

        client_id = f"test-{uuid.uuid4()}"

        for _ in range(20):
            result = check_rate_limit(client_id)
            assert result is True
