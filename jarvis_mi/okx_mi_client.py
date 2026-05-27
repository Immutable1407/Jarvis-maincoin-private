from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any
from .config_mi import MiConfig

BASE_URL = "https://www.okx.com"


class OKXError(RuntimeError):
    pass


class OKXMiClient:
    def __init__(self, cfg: MiConfig):
        self.cfg = cfg
        self.pos_mode_cache: str | None = None

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        msg = (timestamp + method.upper() + request_path + body).encode()
        mac = hmac.new(self.cfg.secret_key.encode(), msg, hashlib.sha256).digest()
        return base64.b64encode(mac).decode()

    def request(self, method: str, path: str, params: dict[str, Any] | None = None, body: Any = None, auth: bool = True) -> dict[str, Any]:
        query = ""
        if params:
            query = "?" + urllib.parse.urlencode(params)
        request_path = path + query
        body_str = "" if body is None else json.dumps(body, separators=(",", ":"))
        headers = {"Content-Type": "application/json", "User-Agent": "Hermes-Mi/0.1"}
        if auth:
            ts = self._timestamp()
            headers.update({
                "OK-ACCESS-KEY": self.cfg.api_key,
                "OK-ACCESS-SIGN": self._sign(ts, method, request_path, body_str),
                "OK-ACCESS-TIMESTAMP": ts,
                "OK-ACCESS-PASSPHRASE": self.cfg.passphrase,
            })
            if self.cfg.simulated == "1":
                headers["x-simulated-trading"] = "1"
        req = urllib.request.Request(BASE_URL + request_path, data=(body_str.encode() if body_str else None), headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise OKXError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}") from e
        if data.get("code") != "0":
            raise OKXError(f"OKX {data.get('code')}: {data.get('msg')} data={data.get('data')}")
        return data

    def account_config(self) -> dict[str, Any]:
        return (self.request("GET", "/api/v5/account/config").get("data") or [{}])[0]

    def uid_tuple(self) -> tuple[str, str, str]:
        cfg = self.account_config()
        self.pos_mode_cache = cfg.get("posMode") or self.pos_mode_cache
        return str(cfg.get("uid") or ""), str(cfg.get("mainUid") or ""), str(cfg.get("posMode") or "")

    def balance(self) -> dict[str, Any]:
        return (self.request("GET", "/api/v5/account/balance", {"ccy": "USDT"}).get("data") or [{}])[0]

    def usdt_equity(self) -> float:
        d = self.balance()
        details = d.get("details") or []
        usdt = next((x for x in details if x.get("ccy") == "USDT"), {})
        return float(usdt.get("eq") or d.get("totalEq") or 0.0)

    def positions(self, inst_type: str = "SWAP") -> list[dict[str, Any]]:
        return self.request("GET", "/api/v5/account/positions", {"instType": inst_type}).get("data") or []

    def open_positions(self) -> list[dict[str, Any]]:
        out = []
        for p in self.positions():
            try:
                if abs(float(p.get("pos") or 0)) > 0:
                    out.append(p)
            except Exception:
                pass
        return out

    def instruments(self) -> dict[str, dict[str, Any]]:
        data = self.request("GET", "/api/v5/public/instruments", {"instType": "SWAP"}, auth=False).get("data") or []
        return {x["instId"]: x for x in data}

    def candles(self, inst_id: str, bar: str, limit: int = 200) -> list[dict[str, float]]:
        data = self.request("GET", "/api/v5/market/candles", {"instId": inst_id, "bar": bar, "limit": str(limit)}, auth=False).get("data") or []
        rows = []
        for r in reversed(data):
            rows.append({"ts": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]), "vol": float(r[5])})
        return rows

    def _pos_mode(self) -> str:
        if not self.pos_mode_cache:
            self.pos_mode_cache = self.account_config().get("posMode")
        return self.pos_mode_cache or "net_mode"

    def set_leverage(self, inst_id: str, lever: int, pos_side: str | None = None) -> dict[str, Any]:
        body = {"instId": inst_id, "lever": str(lever), "mgnMode": self.cfg.td_mode}
        if self._pos_mode() == "long_short_mode" and pos_side in {"long", "short"}:
            body["posSide"] = pos_side
        return self.request("POST", "/api/v5/account/set-leverage", body=body)

    def market_order(self, inst_id: str, side: str, sz: str, pos_side: str | None = None, reduce_only: bool = False, cl_ord_id: str | None = None) -> dict[str, Any]:
        body = {"instId": inst_id, "tdMode": self.cfg.td_mode, "side": side, "ordType": "market", "sz": sz}
        if self._pos_mode() == "long_short_mode" and pos_side in {"long", "short"}:
            body["posSide"] = pos_side
        if reduce_only:
            body["reduceOnly"] = "true"
        if cl_ord_id:
            body["clOrdId"] = cl_ord_id[:32]
        return self.request("POST", "/api/v5/trade/order", body=body)

    def place_stop_algo(self, inst_id: str, close_side: str, sz: str, trigger_px: str, pos_side: str | None = None) -> dict[str, Any]:
        body = {"instId": inst_id, "tdMode": self.cfg.td_mode, "side": close_side, "ordType": "conditional", "sz": sz, "triggerPx": trigger_px, "orderPx": "-1", "triggerPxType": "last", "reduceOnly": "true"}
        if self._pos_mode() == "long_short_mode" and pos_side in {"long", "short"}:
            body["posSide"] = pos_side
        return self.request("POST", "/api/v5/trade/order-algo", body=body)

    def cancel_algo(self, inst_id: str, algo_id: str) -> dict[str, Any]:
        return self.request("POST", "/api/v5/trade/cancel-algos", body=[{"instId": inst_id, "algoId": algo_id}])
