"""
Integration tests for the Legal Lens API.
"""

import pytest
from fastapi.testclient import TestClient


class TestAPIIntegration:
    """End-to-end API tests."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        from backend.api.main import app
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test the root endpoint returns OK."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_login_valid_credentials(self, client):
        """Test login with valid demo credentials."""
        response = client.post(
            "/login",
            json={"username": "practitioner_demo", "password": "demo123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "practitioner"
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials returns 401."""
        response = client.post(
            "/login",
            json={"username": "invalid", "password": "invalid"},
        )
        assert response.status_code == 401
    
    def test_search_requires_auth(self, client):
        """Test that search endpoint requires authentication."""
        response = client.post(
            "/search",
            json={"query": "test query"},
        )
        assert response.status_code == 403  # Forbidden without token
    
    def test_search_with_auth(self, client):
        """Test search with valid authentication."""
        # First, login
        login_response = client.post(
            "/login",
            json={"username": "student_demo", "password": "demo123"},
        )
        token = login_response.json()["access_token"]
        
        # Then, search
        response = client.post(
            "/search",
            json={"query": "medical negligence"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "llm_response" in data
