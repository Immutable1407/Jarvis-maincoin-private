from __future__ import annotations
import json
from jarvis_mi.account_guard import assert_mi_account, assert_allowed_inst
from jarvis_mi.config_mi import MiConfig, ensure_dirs
from jarvis_mi.execution import reduce_only_close, reduce_only_fraction
from jarvis_mi.indicators import atr
from jarvis_mi.ledger import append_jsonl
from jarvis_mi.okx_mi_client import OKXMiClient
from jarvis_mi.exits import plan_exit_actions
from jarvis_mi.state import load_json, save_json


def _direction(p: dict) -> str:
    if p.get("posSide") in {"long", "short"}:
        return str(p.get("posSide"))
    return "long" if float(p.get("pos") or 0) > 0 else "short"


def run_guardian() -> dict:
    ensure_dirs()
    cfg = MiConfig.from_env()
    client = OKXMiClient(cfg)
    acct = assert_mi_account(client, cfg)
    positions = client.open_positions()
    events = []
    for p in positions:
        inst_id = p.get("instId")
        assert_allowed_inst(inst_id, cfg)
        pos = float(p.get("pos") or 0)
        direction = _direction(p)
        avg_px = float(p.get("avgPx") or p.get("bePx") or 0)
        mark = float(p.get("markPx") or p.get("last") or 0)
        m15 = client.candles(inst_id, "15m", 60)
        if not m15 or not mark:
            continue
        recent_low = min(x["l"] for x in m15[-8:-1])
        recent_high = max(x["h"] for x in m15[-8:-1])
        a = atr(m15, 14)[-1]
        reason = None
        if direction == "long":
            local_stop = min(recent_low, avg_px - 1.2 * a) if avg_px else recent_low
            if mark <= local_stop:
                reason = f"guardian_local_stop_long mark={mark} stop={local_stop}"
        else:
            local_stop = max(recent_high, avg_px + 1.2 * a) if avg_px else recent_high
            if mark >= local_stop:
                reason = f"guardian_local_stop_short mark={mark} stop={local_stop}"
        if reason:
            events.append(reduce_only_close(client, cfg, p, reason))
            continue

        state_name = f"exit_state_{inst_id}_{direction}_{avg_px:.8f}.json"
        state = load_json(state_name, {})
        instruments = client.instruments()
        inst_meta = instruments.get(inst_id, {})
        min_sz = float(inst_meta.get("minSz") or 0.0)
        lot_sz = inst_meta.get("lotSz")
        if avg_px and local_stop:
            actions = plan_exit_actions(p, avg_px, local_stop, mark, state, min_size=min_sz)
            for action in actions:
                try:
                    if action.kind == "move_stop_breakeven" and cfg.enable_breakeven:
                        state["breakeven_done"] = True
                        state["breakeven_px"] = action.trigger_price
                        events.append({"event": "EXIT_STATE", "kind": action.kind, "instId": inst_id, "reason": action.reason, "trigger_price": action.trigger_price})
                    elif action.kind == "partial_tp_1" and cfg.enable_partial_tp:
                        events.append(reduce_only_fraction(client, cfg, p, action.fraction, action.reason, lot_sz=lot_sz, min_sz=str(min_sz)))
                        state["partial_tp_1"] = True
                    elif action.kind == "partial_tp_2" and cfg.enable_partial_tp:
                        events.append(reduce_only_fraction(client, cfg, p, action.fraction, action.reason, lot_sz=lot_sz, min_sz=str(min_sz)))
                        state["partial_tp_2"] = True
                    elif action.kind == "trailing_stop" and cfg.enable_trailing:
                        state["trailing_px"] = action.trigger_price
                        events.append({"event": "EXIT_STATE", "kind": action.kind, "instId": inst_id, "reason": action.reason, "trigger_price": action.trigger_price})
                except Exception as action_error:
                    events.append({"event": "EXIT_ACTION_ERROR", "kind": action.kind, "instId": inst_id, "error": str(action_error)})
            # Enforce local breakeven/trailing close via guardian instead of modifying OKX algos blindly.
            be = state.get("breakeven_px")
            trail = state.get("trailing_px")
            if direction == "long":
                if be and mark <= float(be):
                    events.append(reduce_only_close(client, cfg, p, f"guardian_breakeven_stop mark={mark} be={be}"))
                elif trail and mark <= float(trail):
                    events.append(reduce_only_close(client, cfg, p, f"guardian_trailing_stop mark={mark} trail={trail}"))
            else:
                if be and mark >= float(be):
                    events.append(reduce_only_close(client, cfg, p, f"guardian_breakeven_stop mark={mark} be={be}"))
                elif trail and mark >= float(trail):
                    events.append(reduce_only_close(client, cfg, p, f"guardian_trailing_stop mark={mark} trail={trail}"))
            save_json(state_name, state)
    rec = {"event": "GUARDIAN", "account": acct, "positions": len(positions), "actions": events}
    append_jsonl("guardian.jsonl", rec)
    return rec


if __name__ == "__main__":
    try:
        r = run_guardian()
        if r.get("actions"):
            print(json.dumps(r, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"event": "ERROR", "where": "mi_guardian", "error": str(e)}, ensure_ascii=False))
        raise
