import pytest

from tests.fakes import FakeSupabase


@pytest.fixture
def db():
    return FakeSupabase()
