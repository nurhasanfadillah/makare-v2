import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from schema import default_settings, initial_admin_from_env  # noqa: E402


def test_empty_users_database_requires_explicit_bootstrap_credentials():
    assert initial_admin_from_env({}) is None


def test_initial_admin_configuration_is_normalized_and_validated():
    config = initial_admin_from_env({
        "INITIAL_ADMIN_USERNAME": "  Owner.Admin  ",
        "INITIAL_ADMIN_PASSWORD": "A" * 16,
        "INITIAL_ADMIN_FULL_NAME": "  First Admin  ",
    })

    assert config == ("owner.admin", "A" * 16, "First Admin")


@pytest.mark.parametrize("env", [
    {"INITIAL_ADMIN_USERNAME": "bad name", "INITIAL_ADMIN_PASSWORD": "A" * 16},
    {"INITIAL_ADMIN_USERNAME": "owner", "INITIAL_ADMIN_PASSWORD": "short"},
    {"INITIAL_ADMIN_USERNAME": "owner", "INITIAL_ADMIN_PASSWORD": "é" * 40},
    {"INITIAL_ADMIN_USERNAME": "owner", "INITIAL_ADMIN_PASSWORD": "A" * 16, "INITIAL_ADMIN_FULL_NAME": " "},
])
def test_initial_admin_configuration_rejects_invalid_values(env):
    with pytest.raises(RuntimeError):
        initial_admin_from_env(env)


def test_new_install_does_not_set_a_source_default_overtime_pin():
    assert default_settings()["overtime_pin_hash"] is None
