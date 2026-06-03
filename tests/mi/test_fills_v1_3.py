import json
import sys
from pathlib import Path

sys.path.insert(0, "/root/jarvis-mi")

from jarvis_mi.config_mi import MiConfig
from jarvis_mi import fills


class DummyClient:
    def request(self, method, path, params):
        return {"data": [
            {"tradeId": "t1", "instId": "BTC-USDT-SWAP", "fillPx": "100", "fillSz": "1"},
            {"tradeId": "t1", "instId": "BTC-USDT-SWAP", "fillPx": "100", "fillSz": "1"},
            {"tradeId": "t2", "instId": "ETH-USDT-SWAP", "fillPx": "10", "fillSz": "1"},
        ]}


def _cfg():
    return MiConfig(api_key="x", secret_key="x", passphrase="x", simulated="0", expected_uid="u", expected_main_uid="m", allowed_insts=("BTC-USDT-SWAP", "ETH-USDT-SWAP"))


def test_sync_fills_dedupes_trade_ids(tmp_path, monkeypatch):
    ledger = tmp_path / "fills.jsonl"
    seen = tmp_path / "fill_sync_seen.json"

    def fake_append(name, rec):
        with ledger.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    monkeypatch.setattr(fills, "SEEN_FILLS_PATH", seen)
    monkeypatch.setattr(fills, "append_jsonl", fake_append)
    first = fills.sync_fills(DummyClient(), _cfg())
    second = fills.sync_fills(DummyClient(), _cfg())
    assert first["new"] == 2
    assert first["skipped_duplicates"] == 1
    assert second["new"] == 0
    assert second["skipped_duplicates"] == 3
    assert len(ledger.read_text().splitlines()) == 2

def test_seen_state_trims_oldest_not_lexicographic(tmp_path, monkeypatch):
    seen_path = tmp_path / "fill_sync_seen.json"
    monkeypatch.setattr(fills, "SEEN_FILLS_PATH", seen_path)
    # Lexicographically large key is oldest and must be trimmed first.
    fills._save_seen({"z-old": 1.0, "a-new": 2.0, "m-newer": 3.0}, max_keys=2)
    raw = json.loads(seen_path.read_text())
    assert raw["keys"] == ["a-new", "m-newer"]
    assert "z-old" not in raw["seen_at"]


def test_package_version_matches_v1_4():
    import jarvis_mi
    assert jarvis_mi.__version__ == "1.4.1"

