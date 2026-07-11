import pytest

import os
import importlib
import target as target

def test_get_api_key():
    os.environ["API_KEY"] = "test-key"
    importlib.reload(target)
    assert target.get_api_key() == "test-key"


def test_no_hardcoded_secret():
    assert "123456789abcdef" not in target.__dict__.values()


def test_api_key_is_string():
    assert isinstance(target.get_api_key(), str)
