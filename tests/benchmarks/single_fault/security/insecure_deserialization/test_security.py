import pytest
import pickle
from target import load_data


def test_valid_data() -> None:
    data = pickle.dumps({"key": "value"})
    assert load_data(data) == {"key": "value"}


def test_malicious_payload() -> None:
    # This payload should be rejected because deserializing
    # arbitrary objects is a critical vulnerability.
    with pytest.raises(Exception):
        load_data(b"cos\nsystem\n(S'whoami'\ntR.")


def test_empty_payload() -> None:
    with pytest.raises(EOFError):
        load_data(b"")
