from __future__ import annotations
from .config_mi import MiConfig
from .okx_mi_client import OKXMiClient

FORBIDDEN_UIDS = {
    "621655308511150593": "main_btc_ahr999_manual_account",
    "833659597537129752": "jarvis_v4_altcoin_account",
}


class AccountGuardError(RuntimeError):
    pass


def assert_mi_account(client: OKXMiClient, cfg: MiConfig) -> dict[str, str]:
    uid, main_uid, pos_mode = client.uid_tuple()
    if not uid:
        raise AccountGuardError("OKX uid missing; fail closed")
    if uid in FORBIDDEN_UIDS:
        raise AccountGuardError(f"forbidden OKX uid {uid}: {FORBIDDEN_UIDS[uid]}")
    if uid != cfg.expected_uid:
        raise AccountGuardError(f"uid mismatch: got {uid}, expected {cfg.expected_uid}")
    if main_uid != cfg.expected_main_uid:
        raise AccountGuardError(f"mainUid mismatch: got {main_uid}, expected {cfg.expected_main_uid}")
    return {"uid": uid, "mainUid": main_uid, "posMode": pos_mode}


def assert_allowed_inst(inst_id: str, cfg: MiConfig) -> None:
    if inst_id not in cfg.allowed_insts:
        raise AccountGuardError(f"instrument not allowed for Hermes Mi: {inst_id}")
