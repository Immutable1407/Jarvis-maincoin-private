from __future__ import annotations
from typing import Sequence


def ema(values: Sequence[float], period: int) -> list[float]:
    if not values:
        return []
    k = 2 / (period + 1)
    out = [float(values[0])]
    for v in values[1:]:
        out.append(float(v) * k + out[-1] * (1 - k))
    return out


def atr(candles: list[dict[str, float]], period: int = 14) -> list[float]:
    if not candles:
        return []
    trs = []
    prev = candles[0]["c"]
    for c in candles:
        tr = max(c["h"] - c["l"], abs(c["h"] - prev), abs(c["l"] - prev))
        trs.append(tr)
        prev = c["c"]
    return ema(trs, period)


def round_step(x: float, step: float) -> float:
    if step <= 0:
        return x
    return int(x / step) * step


def decimals_from_step(step_s: str) -> int:
    if "." not in step_s:
        return 0
    return len(step_s.rstrip("0").split(".")[-1])


def fmt_step(x: float, step_s: str) -> str:
    d = decimals_from_step(step_s)
    y = round_step(x, float(step_s))
    return f"{y:.{d}f}" if d else str(int(y))
