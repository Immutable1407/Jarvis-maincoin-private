# Hermes Mi v1.0.0 Maincoin Strategy Architecture

## Purpose

Hermes Mi is a dedicated OKX maincoin perpetual strategy isolated from BTC-AHR999 and Jarvis v4 altcoin trading. v1.0.0 is the first complete guarded loop for BTC/ETH/SOL/BNB only.

## Account and instrument boundaries

- Expected OKX UID: `845800098641991226`
- Expected mainUid: `621655308511150593`
- Credential prefix: `HERMES_MI_OKX_*`
- Forbidden credential prefixes in this project: `OKX_*`, `OKX_SUB_*`
- Allowed instruments:
  - `BTC-USDT-SWAP`
  - `ETH-USDT-SWAP`
  - `SOL-USDT-SWAP`
  - `BNB-USDT-SWAP`

Every private read/write path must verify UID/mainUid before acting. Non-whitelisted SWAP positions are abnormal and should fail/alert.

## Live gates

- `strategy_tag = mi_v1_0_0_initial_complete`
- `active_max_positions = 1`
- `enable_second_position = False`
- `enable_rotation = False`
- margin mode: cross
- hot path: deterministic Python only, no LLM order decisioning

The codebase contains portfolio and rotation modules, but live risk remains one active position until enough data justifies opening the next gate.

## Live cycle data flow

`python3 scripts/mi/mi_live_cycle.py`:

1. Load config and verify Hermes Mi UID/mainUid.
2. Read USDT equity and open positions.
3. Reject non-whitelisted SWAP positions.
4. Load whitelisted instrument metadata.
5. Read 1h and 15m candles for all four instruments.
6. Compute BTC bias.
7. Classify market state:
   - `btc_regime`
   - `maincoin_regime`
   - `direction_bias`
   - `frequency_mode`
   - `risk_budget`
8. Compute four-maincoin resonance:
   - aligned long/short
   - BTC/alt divergence
   - mixed state
9. Score layered signals with observe/setup/trigger reason codes.
10. Apply market-state direction gate.
11. Apply portfolio gate.
12. Compute dynamic risk decision.
13. Submit market entry and standalone reduce-only stop only if all gates pass.
14. Save local snapshot and decision ledger.

## Guardian and exits

`python3 scripts/mi/mi_guardian.py` runs every 5m and manages open positions:

- account guard and instrument whitelist guard;
- local ATR/structure hard stop;
- breakeven state after sufficient MFE;
- partial take profit with reduce-only orders;
- trailing state after profits mature;
- per-action error isolation so one failed partial TP does not stop guardian protection;
- exit state keyed by instrument, direction, and average price to avoid stale state reuse.

The entry path still places an exchange-side standalone hard stop. Breakeven/trailing are local guardian-enforced in v1.0.0; exchange-side cancel/replace hardening is future work.

## Fill sync and reports

- `scripts/mi/mi_sync_fills.py`: syncs OKX fills every 10m to local ledgers.
- `scripts/mi/mi_daily_review.py`: emits a concise daily maincoin brief.
- Runtime data lives under `/root/jarvis-mi/data/` and `/root/jarvis-mi/reports/` and must never be committed.

## Cron jobs

- `bc97ef299d9f` — live cycle, every 15m, local delivery.
- `dcb5a389e2d4` — guardian, every 5m, local delivery.
- `4d7fbee50ff9` — healthcheck, every 120m, local delivery.
- `aded3c6554f3` — fill sync, every 10m, local delivery.
- `65b8d9feb0b3` — daily maincoin brief, 21:00 UTC+8, delivered to origin chat.

## Verification

```bash
cd /root/jarvis-mi
export PYTHONPATH=/root/jarvis-mi
python3 -m compileall -q jarvis_mi scripts/mi tests/mi
python3 -m unittest discover -s tests/mi -v
python3 scripts/mi/mi_healthcheck.py
python3 scripts/mi/mi_guardian.py
python3 scripts/mi/mi_live_cycle.py
python3 scripts/mi/mi_sync_fills.py
python3 scripts/mi/mi_daily_review.py
```

`mi_live_cycle.py` can place a live order if a strict signal passes. Pause the live-cycle cron before manual testing if no new entries are desired.

## GitHub release

- Private repo: `Immutable1407/Jarvis-maincoin-private`
- Remote: `git@github.com-jarvis:Immutable1407/Jarvis-maincoin-private.git`
- Release tag: `v1.0.0`

Before pushing, scan staged files for secrets and confirm no `/data/`, `/reports/`, `.env*`, `.jsonl`, account snapshots, fills, or ledgers are committed.
