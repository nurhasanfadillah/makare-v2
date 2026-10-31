import os
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

os.environ.setdefault("JWT_SECRET", "unit-test-signing-key-not-used-for-real-tokens")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from routes_admin import UserIn, UserPatch  # noqa: E402


def test_user_password_accepts_bcrypt_byte_limit():
    payload = UserIn(username="operator1", full_name="Operator", role="operator", password="P" * 72)

    assert len(payload.password.encode("utf-8")) == 72


@pytest.mark.parametrize("password", ["short", "P" * 11, "\u00e9" * 37])
def test_user_create_rejects_password_outside_bcrypt_byte_bounds(password):
    with pytest.raises(ValidationError):
        UserIn(username="operator1", full_name="Operator", role="operator", password=password)


def test_user_patch_allows_omitted_password():
    assert UserPatch(active=False).password is None
