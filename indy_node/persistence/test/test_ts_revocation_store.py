import pytest
from plenum.common.util import randomString
from indy_node.persistence.timestamp_revocation_storage import TimestampRevocationStorage
from plenum.test.conftest import tdir


@pytest.fixture(scope="module")
def storage_with_ts_root_hashes(tdir):
    storage = TimestampRevocationStorage("test", tdir, "test_db")
    ts_list = {
        2: "aaaa",
        4: "bbbb",
        5: "cccc",
        100: "ffff",
    }
    for k, v in ts_list.items():
        storage.set(k, v)
    return storage, ts_list


def test_none_if_key_less_then_minimal_key(storage_with_ts_root_hashes):
    storage, _ = storage_with_ts_root_hashes
    assert storage.get_equal_or_prev(1) is None


def test_previous_key_for_given(storage_with_ts_root_hashes):
    storage, ts_list = storage_with_ts_root_hashes
    assert storage.get_equal_or_prev(3).decode("utf-8") == ts_list[2]
    assert storage.get_equal_or_prev(101).decode("utf-8") == ts_list[100]