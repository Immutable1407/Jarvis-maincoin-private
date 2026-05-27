# Hermes Mi v0.1 Live Bootstrap Design

## Purpose

Hermes Mi is a dedicated maincoin perpetual strategy isolated from BTC-AHR999 and Jarvis v4 altcoin trading. v0.1 prioritizes a minimal safe live loop over strategy richness.

## Account isolation

- Expected OKX UID: `845800098641991226`
- Expected mainUid: `621655308511150593`
- Credential prefix: `HERMES_MI_OKX_*`
- Forbidden credential prefixes in this project: `OKX_*`, `OKX_SUB_*`
- Account guard runs before private read/write actions.
- Non-whitelisted SWAP positions trigger failure/alert behavior.

## Instruments

Only these instruments are allowed:

- `BTC-USDT-SWAP`
- `ETH-USDT-SWAP`
- `SOL-USDT-SWAP`
- `BNB-USDT-SWAP`

## v0.1 strategy loop

1. Verify Hermes Mi UID/mainUid.
2. Read USDT equity and open SWAP positions.
3. Refuse new entries when `max_positions=1` is reached.
4. Read 1h and 15m candles for the four whitelisted instruments.
5. Compute BTC 1h bias.
6. Score each instrument using:
   - 1h EMA20/EMA50 trend direction
   - 15m EMA20 trigger / local high-low trigger
   - ATR-derived structure stop
   - BTC alignment penalty/bonus
7. Select highest valid candidate.
8. Size using `sz = notional / (ctVal * price)` with margin/risk caps.
9. Set 20x leverage.
10. Submit market order and standalone reduce-only stop algo.
11. Write structured decision/trade ledgers.

## v0.1 risk limits

- `max_positions=1`
- `td_mode=cross`
- `default_leverage=20`
- `margin_pct=0.06`
- `max_margin_pct=0.08`
- `max_loss_pct=0.012`
- no range trading
- no rotation
- no partial TP
- no pyramiding
- no LLM hot-path decisioning

## Guardian

The guardian runs every 5m and:

- verifies account UID/mainUid;
- checks only whitelisted positions;
- computes recent 15m structure and ATR;
- reduce-only closes if local structure stop is breached;
- writes `guardian.jsonl`.

## Healthcheck

The healthcheck runs every 120m and:

- verifies UID/mainUid;
- checks USDT equity;
- checks open positions;
- checks whitelist violations;
- checks all four instruments are available;
- writes `healthcheck.jsonl`.

## Cron jobs

- `bc97ef299d9f` — live cycle, every 15m, local delivery.
- `dcb5a389e2d4` — guardian, every 5m, local delivery.
- `4d7fbee50ff9` — healthcheck, every 120m, local delivery.

Normal no-trade / no-action states are silent to avoid notification noise.

## GitHub sync

Remote:

```bash
git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git
```

Use the `github.com-jarvis` SSH alias. This is the same pattern used by the Jarvis altcoin private backup workflow.
