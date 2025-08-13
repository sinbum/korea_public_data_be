import pytest
import asyncio
from unittest.mock import AsyncMock, Mock

# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Common test fixtures
@pytest.fixture
def mock_database():
    """Mock MongoDB database"""
    db = AsyncMock()
    # Mock collections
    for collection_name in ["alert_subscriptions", "notifications", "notification_preferences", 
                           "delivery_logs", "users", "announcements", "contents", "statistics"]:
        collection = AsyncMock()
        collection.find = Mock(return_value=AsyncMock())
        collection.find_one = AsyncMock()
        collection.insert_one = AsyncMock()
        collection.update_one = AsyncMock()
        collection.delete_one = AsyncMock()
        collection.count_documents = AsyncMock()
        collection.create_index = AsyncMock()
        collection.distinct = Mock(return_value=AsyncMock())
        db[collection_name] = collection
    return db


@pytest.fixture
def mock_settings():
    """Mock application settings"""
    settings = Mock()
    settings.alerts_enabled = True
    settings.alerts_global_rps = 10
    settings.alerts_user_daily_cap = 100
    settings.frontend_url = "http://localhost:3000"
    settings.database_url = "mongodb://localhost:27017"
    settings.database_name = "test_db"
    return settings