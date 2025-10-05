"""Pytest configuration and fixtures for test suite."""
import pytest
from typing import Generator
from adapters.api import deps


@pytest.fixture(autouse=True)
def reset_session_maker() -> Generator[None, None, None]:
    """Reset the global session maker between tests to avoid event loop issues."""
    # Clear the global session maker before each test
    deps._session_maker = None
    deps._db_config = None
    
    yield
    
    # Clean up after test
    deps._session_maker = None
    deps._db_config = None
