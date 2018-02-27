import pytest
import time
from plenum.common.util import randomString
from indy_common.constants import REVOC_REG_ENTRY, REVOC_REG_DEF_ID, ISSUED, \
    REVOKED, PREV_ACCUM, ACCUM, TYPE, REVOC_REG_DEF, ISSUANCE_BY_DEFAULT, \
    CRED_DEF_ID, VALUE, TAG
from indy_common.types import Request
from indy_common.state import domain
from plenum.test.helper import sdk_sign_request_from_dict
from plenum.common.txn_util import reqToTxn
from plenum.common.types import f
from plenum.common.constants import TXN_TIME
from plenum.test.helper import create_new_test_node
from plenum.common.exceptions import InvalidClientRequest


@pytest.fixture(scope="module")
def create_node_and_not_start(testNodeClass,
                              node_config_helper_class,
                              tconf,
                              tdir,
                              allPluginsPath,
                              looper,
                              tdirWithPoolTxns,
                              tdirWithDomainTxns,
                              tdirWithNodeKeepInited):
    node = create_new_test_node(testNodeClass,
                                node_config_helper_class,
                                "Alpha",
                                tconf,
                                tdir,
                                allPluginsPath)
    return node

@pytest.fixture(scope="module")
def add_revoc_def(create_node_and_not_start,
                  looper,
                  sdk_wallet_steward):
    node = create_node_and_not_start
    data = {
        "id": randomString(50),
        "type": REVOC_REG_DEF,
        "tag": randomString(5),
        "credDefId": randomString(50),
        "value":{
            "issuanceType": ISSUANCE_BY_DEFAULT,
            "maxCredNum": 1000000,
            "tailsHash": randomString(50),
            "tailsLocation": 'http://tails.location.com',
            "publicKeys": {},
        }
    }
    req = sdk_sign_request_from_dict(looper, sdk_wallet_steward, data)

    req_handler = node.getDomainReqHandler()
    req_handler.validate(Request(**req))
    txn = reqToTxn(Request(**req))
    txn[f.SEQ_NO.nm] = node.domainLedger.seqNo + 1
    txn[TXN_TIME] = int(time.time())
    req_handler._addRevocDef(txn)
    return req

@pytest.fixture(scope="module")
def build_txn_for_revoc_def_entry(looper,
                                  sdk_wallet_steward,
                                  add_revoc_def):
    revoc_def_txn = add_revoc_def
    revoc_def_txn = reqToTxn(revoc_def_txn)
    path = ":".join([revoc_def_txn[f.IDENTIFIER.nm],
                     domain.MARKER_REVOC_DEF,
                     revoc_def_txn[CRED_DEF_ID],
                     revoc_def_txn[TYPE],
                     revoc_def_txn[TAG]])
    data = {
        REVOC_REG_DEF_ID: path,
        TYPE: REVOC_REG_ENTRY,
        VALUE: {
            PREV_ACCUM: randomString(10),
            ACCUM: randomString(10),
            ISSUED: [],
            REVOKED: [],
        }
    }

    req = sdk_sign_request_from_dict(looper, sdk_wallet_steward, data)
    return req

def test_validation_with_unexpected_accum(build_txn_for_revoc_def_entry,
                     create_node_and_not_start):
    node = create_node_and_not_start
    req_entry = build_txn_for_revoc_def_entry
    req_handler = node.getDomainReqHandler()
    req_handler.apply(Request(**req_entry), int(time.time()))
    with pytest.raises(InvalidClientRequest):
        req_handler.validate(Request(**req_entry))

def test_validation_with_same_revoked(build_txn_for_revoc_def_entry,
                     create_node_and_not_start):
    node = create_node_and_not_start
    req_entry = build_txn_for_revoc_def_entry
    req_entry['operation'][VALUE][REVOKED] = [1, 2]
    req_handler = node.getDomainReqHandler()
    req_handler.apply(Request(**req_entry), int(time.time()))
    req_entry['operation'][VALUE][PREV_ACCUM] = req_entry['operation'][VALUE][ACCUM]
    with pytest.raises(InvalidClientRequest):
        req_handler.validate(Request(**req_entry))

def test_validation_with_issued_no_revoked_before(build_txn_for_revoc_def_entry,
                     create_node_and_not_start):
    node = create_node_and_not_start
    req_entry = build_txn_for_revoc_def_entry
    req_entry['operation'][VALUE][REVOKED] = [1, 2]
    req_handler = node.getDomainReqHandler()
    req_handler.apply(Request(**req_entry), int(time.time()))
    req_entry['operation'][VALUE][ISSUED] = [3, 4]
    req_entry['operation'][VALUE][REVOKED] = []
    req_entry['operation'][VALUE][PREV_ACCUM] = req_entry['operation'][VALUE][ACCUM]
    with pytest.raises(InvalidClientRequest):
        req_handler.validate(Request(**req_entry))

def test_validation_if_revoc_def_does_not_exist(build_txn_for_revoc_def_entry,
                                                create_node_and_not_start):
    path = ":".join([f.IDENTIFIER.nm,
                     domain.MARKER_REVOC_DEF,
                     CRED_DEF_ID,
                     TYPE,
                     TAG])
    node = create_node_and_not_start
    req_entry = build_txn_for_revoc_def_entry
    req_entry['operation'][REVOC_REG_DEF_ID] = path
    req_handler = node.getDomainReqHandler()
    with pytest.raises(InvalidClientRequest):
        req_handler.validate(Request(**req_entry))

def test_validation_if_issued_revoked_has_same_index(build_txn_for_revoc_def_entry,
                                                create_node_and_not_start):
    node = create_node_and_not_start
    req_entry = build_txn_for_revoc_def_entry
    req_entry['operation'][VALUE][REVOKED] = [1, 2]
    req_entry['operation'][VALUE][ISSUED] = [1, 2]
    req_handler = node.getDomainReqHandler()
    with pytest.raises(InvalidClientRequest):
        req_handler.validate(Request(**req_entry))
