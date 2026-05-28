from __future__ import annotations
from datetime import datetime, timezone, timedelta
from pathlib import Path
from .config_mi import REPORT_DIR, ensure_dirs, LEDGER_DIR

def daily_brief() -> str:
    ensure_dirs()
    day = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')
    dec = LEDGER_DIR / 'decisions.jsonl'
    fills = LEDGER_DIR / 'fills.jsonl'
    trades = LEDGER_DIR / 'trades.jsonl'
    text = [f'# Hermes Mi 主流币策略简报 {day}', '', '- 状态：v1.0.0-initial-complete 运行中。']
    for name, path in [('决策记录', dec), ('成交同步', fills), ('交易记录', trades)]:
        count = len(path.read_text(encoding='utf-8').splitlines()) if path.exists() else 0
        text.append(f'- {name}: {count} 条')
    text += ['', '简要结论：请重点看是否有新成交、guardian 动作、以及 market_state 是否长期 pause/chop。']
    out = '\n'.join(text) + '\n'
    p = REPORT_DIR / 'daily' / f'{day}.md'
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(out, encoding='utf-8')
    return out
