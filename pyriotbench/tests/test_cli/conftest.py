"""Test configuration for CLI tests."""

import pytest


@pytest.fixture(autouse=True)
def register_tasks():
    """Auto-register tasks for all tests in this module."""
    # Import tasks to trigger registration
    import pyriotbench.tasks.noop  # noqa: F401
    import pyriotbench.tasks.parse.senml_parse  # noqa: F401
