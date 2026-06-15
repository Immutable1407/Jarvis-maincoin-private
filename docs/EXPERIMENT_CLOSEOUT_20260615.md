# Hermes Mi Maincoin Experiment Closeout — 2026-06-15

## Status

Hermes Mi maincoin strategy is now an archived experiment. Sir transferred its remaining capital into the Unified / Matrix account. The dedicated OKX subaccount UID `845800098641991226` is no longer an active Jarvis trading venue and can be removed from the OKX app/API side after this archive is verified.

## Final operating state

- Strategy family: maincoin-only BTC/ETH/SOL/BNB perpetuals.
- Final live code lineage: v2.0.x regime-adaptive maincoin foundation, with v2.0.2 TrendWearGovernor exit-loss-only patch in the live tree.
- Final manual checks on 2026-06-15:
  - fill sync ran successfully: 100 fills seen, 0 new, 100 duplicates skipped.
  - healthcheck reached the correct UID but equity was `0.0` after fund transfer.
  - open positions: none.
- Hermes cron jobs paused:
  - live cycle `bc97ef299d9f`
  - guardian `dcb5a389e2d4`
  - healthcheck `4d7fbee50ff9`
  - fill sync `aded3c6554f3`
  - daily brief `65b8d9feb0b3`

## Runtime data archive

Runtime/private data was archived locally, not committed to GitHub:

- `/root/jarvis-archives/hermes-mi-runtime-20260615_0245.tar.gz`
- SHA256: `6872e4f89ebef66ac971a272dc8f06ff0b0b15f5f9703033ed5bef61db13410b`

The archive may contain private account/fill/runtime information and must stay local.

## Lessons preserved for Matrix Account

- Maincoin needs structure-first routing and trend-wear feedback; it should not be treated as a reduced altcoin universe.
- OKX hedge-mode fill attribution must use `posSide` and explicit entry/exit roles.
- Trend-wear governors must count closed trade losses, not entry fee-only fills.
- The future active system is Matrix Account v1.0.0, where maincoin long and maincoin short are separate sleeves under the unified 2×2 router.

## GitHub boundary

This closeout document is safe to commit. Runtime `data/`, `reports/`, fills, account snapshots, and secrets remain excluded.
