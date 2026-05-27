# Jarvis Maincoin Private / Hermes Mi

Private repository for the Hermes Mi maincoin perpetual strategy.

Scope:
- Dedicated OKX subaccount: Hermes Mi
- Instruments: BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP, BNB-USDT-SWAP
- v0.1: minimal safe live bootstrap with UID guard, one position max, 20x, 5-8% margin, structure stop, guardian, ledgers.

Secrets are never committed. Runtime credentials live in `/root/.hermes/.env` using `HERMES_MI_OKX_*` variables.
