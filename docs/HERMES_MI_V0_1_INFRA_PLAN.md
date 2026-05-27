# Hermes Mi v0.1 Live Bootstrap Design

Status: implemented as minimal safe live bootstrap.

Hard boundaries:
- Dedicated OKX subaccount UID: `845800098641991226`.
- mainUid: `621655308511150593`.
- Credentials: only `HERMES_MI_OKX_*` from `/root/.hermes/.env`.
- Instruments: BTC/ETH/SOL/BNB USDT swaps only.
- No Feishu delivery for v0.x; local cron output only.

v0.1 limits:
- max_positions = 1
- leverage = 20x
- cross margin
- margin_pct = 6%, hard cap 8%
- max theoretical stop loss = 1.2% equity
- no rotation
- no partial TP
- no pyramiding
- no LLM in hot path
- no range trading

Cron plan:
- live cycle every 15m, local delivery, emits stdout only on order/error.
- guardian every 5m, local delivery, emits stdout only on close/error.
- healthcheck every 120m, local delivery, emits stdout only when abnormal.
