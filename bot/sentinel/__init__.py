"""BagHolderAI - Sentinel (Sprint 1, fast loop).

Sentinel watches external market data (BTC price + funding rate) and
produces a risk_score and opportunity_score (0-100). It does NOT decide
parameter changes - that's Sherpa's job. Sentinel writes scores to
sentinel_scores; Sherpa reads them.

Module layout:
    main.py             entry point (sync loop, every 60s)
    price_monitor.py    BTC price + rolling-window deltas + speed_of_fall
    funding_monitor.py  Binance futures funding rate, 8h cache
    score_engine.py     signal dict -> (risk, opportunity)
    inputs/binance_btc.py      ticker/24hr + klines wrappers
    inputs/binance_funding.py  fapi/v1/fundingRate wrapper
"""
