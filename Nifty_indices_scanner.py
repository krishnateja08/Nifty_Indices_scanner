"""
MarketIntel — Stock Technical & Fundamental Analysis
Supports: Nifty 50 (India) + S&P Top 50 (US) + Indian Indices
Timeframes: 15m, 1H, 1D, 1W
Output: Interactive HTML dashboard
"""

import yfinance as yf
import pandas as pd
import ta
import numpy as np
import json
import os
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─────────────────────────────────────────────
# STOCK UNIVERSE
# ─────────────────────────────────────────────

STOCKS = {
    "IN": {
        "Financials": [
            ("HDFCBANK.NS",   "HDFC Bank"),
            ("ICICIBANK.NS",  "ICICI Bank"),
            ("SBIN.NS",       "State Bank of India"),
            ("BAJFINANCE.NS", "Bajaj Finance"),
            ("KOTAKBANK.NS",  "Kotak Mahindra Bank"),
            ("AXISBANK.NS",   "Axis Bank"),
            ("BAJAJFINSV.NS", "Bajaj Finserv"),
            ("INDUSINDBK.NS", "IndusInd Bank"),
            ("SHRIRAMFIN.NS", "Shriram Finance"),
            ("SBILIFE.NS",    "SBI Life"),
            ("HDFCLIFE.NS",   "HDFC Life"),
        ],
        "Technology": [
            ("TCS.NS",       "TCS"),
            ("INFY.NS",      "Infosys"),
            ("WIPRO.NS",     "Wipro"),
            ("HCLTECH.NS",   "HCL Tech"),
            ("TECHM.NS",     "Tech Mahindra"),
            ("LTIM.NS",      "LTIMindtree"),
        ],
        "Energy": [
            ("RELIANCE.NS",  "Reliance Industries"),
            ("ONGC.NS",      "ONGC"),
            ("BPCL.NS",      "BPCL"),
            ("POWERGRID.NS", "Power Grid"),
            ("NTPC.NS",      "NTPC"),
            ("ADANIENT.NS",  "Adani Enterprises"),
        ],
        "Consumer": [
            ("HINDUNILVR.NS",  "Hindustan Unilever"),
            ("ITC.NS",         "ITC"),
            ("NESTLEIND.NS",   "Nestle India"),
            ("TITAN.NS",       "Titan Company"),
            ("ASIANPAINT.NS",  "Asian Paints"),
            ("MARUTI.NS",      "Maruti Suzuki"),
            ("BRITANNIA.NS",   "Britannia"),
            ("TATACONSUM.NS",  "Tata Consumer"),
        ],
        "Automobile": [
            ("TATAMOTORS.NS", "Tata Motors"),
            ("M&M.NS",        "M&M"),
            ("HEROMOTOCO.NS", "Hero MotoCorp"),
            ("EICHERMOT.NS",  "Eicher Motors"),
            ("BAJAJ-AUTO.NS", "Bajaj Auto"),
        ],
        "Healthcare": [
            ("SUNPHARMA.NS", "Sun Pharma"),
            ("DRREDDY.NS",   "Dr Reddy"),
            ("CIPLA.NS",     "Cipla"),
            ("DIVISLAB.NS",  "Divi's Lab"),
            ("APOLLOHOSP.NS","Apollo Hospital"),
        ],
        "Industrials": [
            ("LT.NS",          "L&T"),
            ("SIEMENS.NS",     "Siemens India"),
            ("ADANIPORTS.NS",  "Adani Ports"),
        ],
        "Metals & Mining": [
            ("TATASTEEL.NS", "Tata Steel"),
            ("JSWSTEEL.NS",  "JSW Steel"),
            ("HINDALCO.NS",  "Hindalco"),
            ("COALINDIA.NS", "Coal India"),
        ],
        "Cement": [
            ("ULTRACEMCO.NS", "UltraTech Cement"),
            ("GRASIM.NS",     "Grasim"),
        ],
        "Telecom": [
            ("BHARTIARTL.NS", "Bharti Airtel"),
        ],
    },
    "US": {
        "Technology": [
            ("NVDA",  "NVIDIA"),
            ("AAPL",  "Apple Inc."),
            ("MSFT",  "Microsoft"),
            ("AMZN",  "Amazon"),
            ("GOOGL", "Alphabet (Class A)"),
            ("GOOG",  "Alphabet (Class C)"),
            ("META",  "Meta Platforms"),
            ("TSLA",  "Tesla"),
            ("AVGO",  "Broadcom"),
            ("ORCL",  "Oracle Corporation"),
            ("AMD",   "Advanced Micro Devices"),
            ("MU",    "Micron Technology"),
            ("NFLX",  "Netflix"),
            ("PLTR",  "Palantir Technologies"),
            ("CSCO",  "Cisco Systems"),
            ("LRCX",  "Lam Research"),
            ("AMAT",  "Applied Materials"),
            ("IBM",   "IBM"),
            ("INTC",  "Intel"),
        ],
        "Financials": [
            ("JPM",   "JPMorgan Chase"),
            ("BRK-B", "Berkshire Hathaway"),
            ("V",     "Visa Inc."),
            ("MA",    "Mastercard"),
            ("BAC",   "Bank of America"),
            ("GS",    "Goldman Sachs"),
            ("MS",    "Morgan Stanley"),
            ("WFC",   "Wells Fargo"),
            ("AXP",   "American Express"),
        ],
        "Energy": [
            ("XOM",   "ExxonMobil"),
            ("CVX",   "Chevron Corporation"),
        ],
        "Healthcare": [
            ("LLY",   "Eli Lilly"),
            ("JNJ",   "Johnson & Johnson"),
            ("ABBV",  "AbbVie"),
            ("MRK",   "Merck & Co."),
            ("UNH",   "UnitedHealth Group"),
        ],
        "Consumer": [
            ("WMT",   "Walmart"),
            ("COST",  "Costco"),
            ("HD",    "Home Depot"),
            ("MCD",   "McDonald's"),
            ("KO",    "Coca-Cola Company"),
            ("PG",    "Procter & Gamble"),
            ("PEP",   "PepsiCo"),
            ("PM",    "Philip Morris International"),
        ],
        "Telecom": [
            ("TMUS",  "T-Mobile US"),
            ("VZ",    "Verizon"),
        ],
        "Industrials": [
            ("CAT",   "Caterpillar Inc."),
            ("GE",    "GE Aerospace"),
            ("GEV",   "GE Vernova"),
            ("RTX",   "RTX Corporation"),
            ("LIN",   "Linde plc"),
        ],
    }
}

# ─────────────────────────────────────────────
# INDIAN INDICES
# ─────────────────────────────────────────────

INDICES = {
    "IN": {
        "^NSEI":   "Nifty 50",
        "^NSEBANK":"Bank Nifty",
        "NIFTY_FIN_SERVICE.NS": "Fin Nifty",
    }
}

# ─────────────────────────────────────────────
# TIMEFRAME CONFIG
# ─────────────────────────────────────────────

TF_CONFIG = {
    "15m": {"interval": "15m",  "period": "5d",  "label": "15 Minute"},
    "1H":  {"interval": "1h",   "period": "30d", "label": "1 Hour"},
    "1D":  {"interval": "1d",   "period": "1y",  "label": "1 Day"},
    "1W":  {"interval": "1wk",  "period": "5y",  "label": "1 Week"},
}

# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_ohlcv(ticker: str, tf: str):
    cfg = TF_CONFIG[tf]
    try:
        df = yf.download(
            ticker,
            interval=cfg["interval"],
            period=cfg["period"],
            progress=False,
            auto_adjust=True,
        )
        if df is None or df.empty or len(df) < 30:
            return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
        df = df.rename(columns=str.lower)
        df = df.dropna()
        return df
    except Exception as e:
        print(f"  [WARN] {ticker} fetch failed: {e}")
        return None


def fetch_fundamentals(ticker: str, is_india: bool, is_index: bool = False) -> dict:
    currency = "₹" if is_india else "$"
    defaults = {
        "pe": "N/A", "eps": "N/A", "eps_trend": "neutral",
        "market_cap": "N/A", "week52_high": "N/A", "week52_low": "N/A",
        "dividend_yield": "N/A", "currency": currency,
        "beta": "N/A", "sector": "Index" if is_index else "N/A",
    }
    if is_index:
        return defaults
    try:
        info = yf.Ticker(ticker).info
        pe  = info.get("trailingPE") or info.get("forwardPE")
        eps = info.get("trailingEps")
        mkt = info.get("marketCap")
        w52h = info.get("fiftyTwoWeekHigh")
        w52l = info.get("fiftyTwoWeekLow")
        dy   = info.get("dividendYield")
        beta = info.get("beta")
        sector = info.get("sector", "N/A")

        fwd_eps = info.get("forwardEps")
        if eps and fwd_eps:
            if fwd_eps > eps:   eps_trend = "up"
            elif fwd_eps < eps: eps_trend = "down"
            else:               eps_trend = "flat"
        else:
            eps_trend = "flat"

        def fmt_large(n):
            if n is None: return "N/A"
            if n >= 1e12: return f"{currency}{n/1e12:.2f}T"
            if n >= 1e9:  return f"{currency}{n/1e9:.2f}B"
            if n >= 1e6:  return f"{currency}{n/1e6:.2f}M"
            return f"{currency}{n:,.0f}"

        return {
            "pe":            f"{pe:.1f}x" if pe else "N/A",
            "eps":           f"{currency}{eps:.2f}" if eps else "N/A",
            "eps_trend":     eps_trend,
            "market_cap":    fmt_large(mkt),
            "week52_high":   f"{currency}{w52h:,.2f}" if w52h else "N/A",
            "week52_low":    f"{currency}{w52l:,.2f}" if w52l else "N/A",
            "dividend_yield":f"{dy*100:.2f}%" if dy else "N/A",
            "currency":      currency,
            "beta":          f"{beta:.2f}" if beta else "N/A",
            "sector":        sector,
        }
    except Exception as e:
        print(f"  [WARN] {ticker} fundamentals failed: {e}")
        return defaults

# ─────────────────────────────────────────────
# SUPPORT & RESISTANCE
# ─────────────────────────────────────────────

def calculate_sr(df: pd.DataFrame, n_levels: int = 3) -> dict:
    close = df["close"].values
    high  = df["high"].values
    low   = df["low"].values
    current_price = float(close[-1])

    window = min(20, len(df) - 1)
    recent_high = float(np.max(high[-window:]))
    recent_low  = float(np.min(low[-window:]))
    pivot       = (recent_high + recent_low + float(close[-window])) / 3

    r_pivot = [
        round(2 * pivot - recent_low, 2),
        round(pivot + (recent_high - recent_low), 2),
        round(recent_high + 2 * (pivot - recent_low), 2),
    ]
    s_pivot = [
        round(2 * pivot - recent_high, 2),
        round(pivot - (recent_high - recent_low), 2),
        round(recent_low - 2 * (recent_high - pivot), 2),
    ]

    swing_highs, swing_lows = [], []
    for i in range(2, len(high) - 2):
        if high[i] > high[i-1] and high[i] > high[i-2] and high[i] > high[i+1] and high[i] > high[i+2]:
            swing_highs.append(float(high[i]))
        if low[i] < low[i-1] and low[i] < low[i-2] and low[i] < low[i+1] and low[i] < low[i+2]:
            swing_lows.append(float(low[i]))

    def cluster(levels, tol=0.005):
        if not levels: return []
        levels = sorted(set(levels))
        clusters, grp = [], [levels[0]]
        for l in levels[1:]:
            if (l - grp[-1]) / grp[-1] < tol:
                grp.append(l)
            else:
                clusters.append(round(np.mean(grp), 2))
                grp = [l]
        clusters.append(round(np.mean(grp), 2))
        return clusters

    swing_h_clusters = cluster(swing_highs)
    swing_l_clusters = cluster(swing_lows)

    resistance = sorted([x for x in swing_h_clusters + r_pivot if x > current_price])[:n_levels]
    support    = sorted([x for x in swing_l_clusters + s_pivot if x < current_price], reverse=True)[:n_levels]

    while len(resistance) < n_levels:
        last = resistance[-1] if resistance else current_price
        resistance.append(round(last * 1.02, 2))
    while len(support) < n_levels:
        last = support[-1] if support else current_price
        support.append(round(last * 0.98, 2))

    return {
        "resistance": resistance[:n_levels],
        "support":    support[:n_levels],
        "pivot":      round(pivot, 2),
    }

# ─────────────────────────────────────────────
# TECHNICAL INDICATORS
# ─────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> dict:
    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]
    result = {}

    def safe_last(series):
        try:
            v = series.dropna()
            return float(v.iloc[-1]) if len(v) > 0 else None
        except:
            return None

    # RSI
    try:
        rsi = ta.momentum.RSIIndicator(close=close, window=14).rsi()
        v = safe_last(rsi)
        result["rsi"] = round(v, 2) if v is not None else None
    except:
        result["rsi"] = None

    # MACD
    try:
        macd_ind  = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
        macd_val  = safe_last(macd_ind.macd())
        macd_sig  = safe_last(macd_ind.macd_signal())
        macd_hist = safe_last(macd_ind.macd_diff())
        result["macd"]        = round(macd_val,  3) if macd_val  is not None else None
        result["macd_signal"] = round(macd_sig,  3) if macd_sig  is not None else None
        result["macd_hist"]   = round(macd_hist, 3) if macd_hist is not None else None
        result["macd_bull"]   = (macd_val > macd_sig) if (macd_val and macd_sig) else False
    except:
        result.update({"macd": None, "macd_signal": None, "macd_hist": None, "macd_bull": False})

    # ATR
    try:
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range()
        v = safe_last(atr)
        result["atr"] = round(v, 2) if v is not None else None
    except:
        result["atr"] = None

    # EMA 20 / 50 / 200
    try:
        ema20  = safe_last(ta.trend.EMAIndicator(close=close, window=20).ema_indicator())
        ema50  = safe_last(ta.trend.EMAIndicator(close=close, window=50).ema_indicator())
        ema200 = safe_last(ta.trend.EMAIndicator(close=close, window=200).ema_indicator())
        curr   = float(close.iloc[-1])
        result["ema20"]  = round(ema20,  2) if ema20  is not None else None
        result["ema50"]  = round(ema50,  2) if ema50  is not None else None
        result["ema200"] = round(ema200, 2) if ema200 is not None else None
        if ema50 and ema200:
            if ema50 > ema200 and curr > ema50:
                result["ema_signal"] = "Golden Cross"
                result["ema_bull"]   = True
            elif ema50 < ema200:
                result["ema_signal"] = "Death Cross"
                result["ema_bull"]   = False
            elif curr > ema50:
                result["ema_signal"] = "Above 50 EMA"
                result["ema_bull"]   = True
            else:
                result["ema_signal"] = "Below 50 EMA"
                result["ema_bull"]   = False
        else:
            result["ema_signal"] = "N/A"
            result["ema_bull"]   = False
    except:
        result.update({"ema20": None, "ema50": None, "ema200": None, "ema_signal": "N/A", "ema_bull": False})

    # Volume ratio
    try:
        avg_vol = float(volume.rolling(20).mean().iloc[-1])
        cur_vol = float(volume.iloc[-1])
        ratio   = cur_vol / avg_vol if avg_vol > 0 else 1.0
        result["volume_ratio"] = round(ratio, 2)
        result["volume_bull"]  = ratio > 1.2
    except:
        result["volume_ratio"] = 1.0
        result["volume_bull"]  = False

    # Stochastic
    try:
        stoch   = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        stoch_k = safe_last(stoch.stoch())
        result["stoch_k"]    = round(stoch_k, 2) if stoch_k is not None else None
        result["stoch_bull"] = (20 < stoch_k < 80) if stoch_k is not None else False
    except:
        result["stoch_k"]    = None
        result["stoch_bull"] = False

    # Bollinger Bands
    try:
        bb   = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
        bbl  = safe_last(bb.bollinger_lband())
        bbu  = safe_last(bb.bollinger_hband())
        bbm  = safe_last(bb.bollinger_mavg())
        curr = float(close.iloc[-1])
        result["bb_lower"] = round(bbl, 2) if bbl is not None else None
        result["bb_upper"] = round(bbu, 2) if bbu is not None else None
        result["bb_mid"]   = round(bbm, 2) if bbm is not None else None
        if bbl and bbu:
            if curr <= bbl:
                result["bb_signal"] = "At Lower Band"
                result["bb_bull"]   = True
            elif curr >= bbu:
                result["bb_signal"] = "At Upper Band"
                result["bb_bull"]   = False
            else:
                result["bb_signal"] = "Mid Band"
                result["bb_bull"]   = True
        else:
            result["bb_signal"] = "N/A"
            result["bb_bull"]   = False
    except:
        result.update({"bb_lower": None, "bb_upper": None, "bb_mid": None, "bb_signal": "N/A", "bb_bull": False})

    return result


# ─────────────────────────────────────────────
# SIGNAL SCORING
# ─────────────────────────────────────────────

def compute_signal(ind: dict, fund: dict) -> dict:
    score = 0
    details = []

    rsi = ind.get("rsi")
    if rsi is not None:
        if 40 <= rsi <= 60:
            score += 10; details.append(("RSI", "neutral", rsi))
        elif 30 <= rsi < 40:
            score += 13; details.append(("RSI", "bull", rsi))
        elif rsi < 30:
            score += 15; details.append(("RSI", "bull", rsi))
        elif 60 < rsi <= 70:
            score += 7;  details.append(("RSI", "neut", rsi))
        else:
            score += 2;  details.append(("RSI", "bear", rsi))

    if ind.get("macd_bull"):
        score += 15; details.append(("MACD", "bull", ind.get("macd")))
    elif ind.get("macd") is not None:
        score += 3;  details.append(("MACD", "bear", ind.get("macd")))

    if ind.get("ema_bull"):
        ema_sig = ind.get("ema_signal","")
        pts = 15 if "Golden" in ema_sig else 10
        score += pts; details.append(("EMA", "bull", ema_sig))
    elif ind.get("ema_signal") not in (None, "N/A"):
        score += 2;  details.append(("EMA", "bear", ind.get("ema_signal")))

    if ind.get("volume_bull"):
        score += 10; details.append(("Volume", "bull", ind.get("volume_ratio")))
    else:
        score += 4;  details.append(("Volume", "neut", ind.get("volume_ratio")))

    stoch = ind.get("stoch_k")
    if stoch is not None:
        if stoch < 20:
            score += 10; details.append(("Stochastic", "bull", stoch))
        elif stoch > 80:
            score += 2;  details.append(("Stochastic", "bear", stoch))
        else:
            score += 7;  details.append(("Stochastic", "neut", stoch))

    if ind.get("bb_bull"):
        score += 8; details.append(("Bollinger", "bull", ind.get("bb_signal")))
    else:
        score += 3; details.append(("Bollinger", "bear", ind.get("bb_signal")))

    pe_str = fund.get("pe", "N/A")
    try:
        pe_val = float(pe_str.replace("x",""))
        if pe_val < 20:    score += 10
        elif pe_val < 35:  score += 7
        else:              score += 3
    except:
        score += 5

    eps_trend = fund.get("eps_trend", "flat")
    if eps_trend == "up":     score += 10
    elif eps_trend == "flat": score += 5
    else:                     score += 0

    beta_str = fund.get("beta", "N/A")
    try:
        beta_val = float(beta_str)
        if 0.5 <= beta_val <= 1.5: score += 5
        elif beta_val < 0.5:       score += 3
        else:                      score += 1
    except:
        score += 3

    score = min(score, 100)

    if score >= 65:   signal = "BUY"
    elif score >= 50: signal = "WATCH"
    elif score >= 38: signal = "HOLD"
    else:             signal = "SELL"

    bull_count = sum(1 for _, cls, _ in details if cls == "bull")
    total_ind  = len(details)

    return {
        "score":      score,
        "signal":     signal,
        "bull_pct":   score,
        "bear_pct":   100 - score,
        "bull_count": bull_count,
        "total_ind":  total_ind,
        "details":    details,
    }

# ─────────────────────────────────────────────
# ANALYSE ONE STOCK / INDEX
# ─────────────────────────────────────────────

def analyse_stock(ticker: str, name: str, country: str, sector: str, tf: str, is_index: bool = False):
    is_india = (country == "IN")
    currency = "₹" if is_india else "$"
    print(f"  Analysing {ticker} ({name}) [{tf}] ...", end=" ", flush=True)

    df = fetch_ohlcv(ticker, tf)
    if df is None:
        print("SKIP (no data)")
        return None

    ind  = calculate_indicators(df)
    sr   = calculate_sr(df)
    fund = fetch_fundamentals(ticker, is_india, is_index)

    curr_price = float(df["close"].iloc[-1])
    prev_price = float(df["close"].iloc[-2]) if len(df) > 1 else curr_price
    change_pct = ((curr_price - prev_price) / prev_price * 100) if prev_price else 0

    atr_val = ind.get("atr")
    stop_loss = round(curr_price - 1.5 * atr_val, 2) if atr_val else None
    target    = round(curr_price + 2.0 * atr_val, 2)  if atr_val else None

    sig = compute_signal(ind, fund)

    def fmt_price(p):
        return f"{currency}{p:,.2f}" if p else "N/A"

    def fmt_sr_list(lst):
        return [fmt_price(x) for x in lst]

    result = {
        "ticker":      ticker,
        "name":        name,
        "country":     country,
        "country_flag":"🇮🇳" if is_india else "🇺🇸",
        "sector":      sector,
        "is_index":    is_index,
        "timeframe":   tf,
        "price":       fmt_price(curr_price),
        "price_raw":   curr_price,
        "change":      f"{change_pct:+.2f}%",
        "change_pos":  change_pct >= 0,
        "currency":    currency,

        "signal":      sig["signal"],
        "score":       sig["score"],
        "bull_pct":    sig["bull_pct"],
        "bear_pct":    sig["bear_pct"],
        "bull_count":  sig["bull_count"],
        "total_ind":   sig["total_ind"],

        "rsi":          ind.get("rsi"),
        "macd":         ind.get("macd"),
        "macd_signal":  ind.get("macd_signal"),
        "macd_hist":    ind.get("macd_hist"),
        "macd_bull":    ind.get("macd_bull", False),
        "ema_signal":   ind.get("ema_signal", "N/A"),
        "ema_bull":     ind.get("ema_bull", False),
        "ema50":        ind.get("ema50"),
        "ema200":       ind.get("ema200"),
        "volume_ratio": ind.get("volume_ratio"),
        "volume_bull":  ind.get("volume_bull", False),
        "stoch_k":      ind.get("stoch_k"),
        "stoch_bull":   ind.get("stoch_bull", False),
        "bb_signal":    ind.get("bb_signal", "N/A"),
        "bb_bull":      ind.get("bb_bull", False),
        "bb_upper":     ind.get("bb_upper"),
        "bb_lower":     ind.get("bb_lower"),

        "atr":        fmt_price(atr_val) if atr_val else "N/A",
        "stop_loss":  fmt_price(stop_loss),
        "target":     fmt_price(target),

        "resistance": fmt_sr_list(sr["resistance"]),
        "support":    fmt_sr_list(sr["support"]),
        "pivot":      fmt_price(sr["pivot"]),

        "pe":             fund.get("pe", "N/A"),
        "eps":            fund.get("eps", "N/A"),
        "eps_trend":      fund.get("eps_trend", "flat"),
        "market_cap":     fund.get("market_cap", "N/A"),
        "week52_high":    fund.get("week52_high", "N/A"),
        "week52_low":     fund.get("week52_low", "N/A"),
        "dividend_yield": fund.get("dividend_yield", "N/A"),
        "beta":           fund.get("beta", "N/A"),
    }
    print(f"DONE — {sig['signal']} ({sig['score']}/100)")
    return result

# ─────────────────────────────────────────────
# HTML GENERATION
# ─────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MarketIntel Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#04080f;
  --surface:#080e1a;
  --surface2:#0d1525;
  --border:#1a2e45;
  --ab:#00d4ff;
  --ag:#00ff88;
  --ar:#ff3d6b;
  --ay:#ffd600;
  --ap:#a855f7;
  --ao:#ff9500;
  --text:#c8d8ee;
  --text-bright:#eef6ff;
  --label:#7ab4d4;
  --sublabel:#5a8aaa;
  --muted:#4a6e90;
  --muted2:#3a5570;
  --dim:#0e1825;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;min-height:100vh;overflow-x:hidden;}
body::before{content:'';position:fixed;inset:0;background-image:linear-gradient(var(--dim) 1px,transparent 1px),linear-gradient(90deg,var(--dim) 1px,transparent 1px);background-size:40px 40px;opacity:.35;pointer-events:none;z-index:0;}
.wrap{position:relative;z-index:1;max-width:1340px;margin:0 auto;padding:20px 24px;}

/* ─── HEADER ─── */
.hdr{display:flex;align-items:center;justify-content:space-between;padding:16px 0 24px;border-bottom:1px solid var(--border);margin-bottom:28px;gap:16px;flex-wrap:wrap;}
.logo{display:flex;align-items:center;gap:14px;}
.logo-icon{width:46px;height:46px;background:linear-gradient(135deg,var(--ab),var(--ap));border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;}
.logo-title{font-size:22px;font-weight:800;letter-spacing:-.5px;color:var(--text-bright);}
.logo-title span{color:var(--ab);}
.logo-sub{font-family:'Space Mono',monospace;font-size:10px;color:#6aaace;margin-top:3px;letter-spacing:.5px;}
.hdr-right{text-align:right;}
.gen-block{display:inline-flex;flex-direction:column;gap:5px;background:rgba(0,212,255,.06);border:1px solid rgba(0,212,255,.2);border-radius:10px;padding:10px 16px;min-width:210px;}
.gen-label{font-family:'Space Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--ab);opacity:.7;}
.gen-time{font-family:'Space Mono',monospace;font-size:13px;font-weight:700;color:var(--ab);}
.gen-live{font-family:'Space Mono',monospace;font-size:11px;color:#5fa8c0;margin-top:2px;display:flex;align-items:center;gap:6px;justify-content:flex-end;}
.live{display:inline-block;width:6px;height:6px;background:var(--ag);border-radius:50%;animation:blink 1.4s infinite;flex-shrink:0;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.12}}

/* ─── MODE TOGGLE ─── */
.mode-toggle{
  display:flex;gap:0;background:rgba(0,0,0,.4);border:1px solid var(--border);
  border-radius:12px;overflow:hidden;margin-bottom:20px;
}
.mode-btn{
  flex:1;padding:14px 20px;border:none;background:transparent;
  color:#5a8aaa;font-family:'Syne',sans-serif;font-size:14px;font-weight:700;
  cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:10px;
  letter-spacing:.3px;position:relative;
}
.mode-btn.active-stocks{background:rgba(0,212,255,.12);color:var(--ab);box-shadow:inset 0 -2px 0 var(--ab);}
.mode-btn.active-indices{background:rgba(255,149,0,.12);color:var(--ao);box-shadow:inset 0 -2px 0 var(--ao);}
.mode-sep{width:1px;background:var(--border);}

/* ─── FILTER PANEL ─── */
.fp{background:rgba(8,18,34,.9);border:1px solid rgba(0,212,255,.15);border-radius:16px;padding:24px 28px;margin-bottom:28px;box-shadow:0 0 40px rgba(0,212,255,.04);}
.fp-title{font-size:10px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:#5a8aaa;margin-bottom:20px;display:flex;align-items:center;gap:10px;}
.fp-title::after{content:'';flex:1;height:1px;background:rgba(0,212,255,.12);}

/* Index filter panel — orange tint */
.fp-index{border-color:rgba(255,149,0,.2);box-shadow:0 0 40px rgba(255,149,0,.03);}
.fp-index .fp-title{color:#aa6600;}
.fp-index .fp-title::after{background:rgba(255,149,0,.15);}

.frow{display:flex;gap:16px;align-items:flex-end;flex-wrap:wrap;}
.fg{display:flex;flex-direction:column;gap:7px;min-width:0;}
.fl{font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;color:#7aaac8;}

/* Index label colours */
.fl-idx{color:#cc7700 !important;}
.fl-tf{color:#a855f7 !important;}

.btn-group{display:flex;gap:5px;flex-wrap:wrap;}

/* Timeframe buttons */
.btn-group .btn:nth-child(1){border-color:rgba(255,214,0,.25);color:#cc9900;}
.btn-group .btn:nth-child(2){border-color:rgba(168,85,247,.25);color:#9955cc;}
.btn-group .btn:nth-child(3){border-color:rgba(0,212,255,.25);color:#0099bb;}
.btn-group .btn:nth-child(4){border-color:rgba(0,255,136,.25);color:#009944;}
.btn-group .btn:nth-child(1):hover,.btn-group .btn:nth-child(1).active{background:rgba(255,214,0,.15);border-color:var(--ay);color:var(--ay);box-shadow:0 0 10px rgba(255,214,0,.2);}
.btn-group .btn:nth-child(2):hover,.btn-group .btn:nth-child(2).active{background:rgba(168,85,247,.15);border-color:var(--ap);color:var(--ap);box-shadow:0 0 10px rgba(168,85,247,.2);}
.btn-group .btn:nth-child(3):hover,.btn-group .btn:nth-child(3).active{background:rgba(0,212,255,.15);border-color:var(--ab);color:var(--ab);box-shadow:0 0 10px rgba(0,212,255,.2);}
.btn-group .btn:nth-child(4):hover,.btn-group .btn:nth-child(4).active{background:rgba(0,255,136,.15);border-color:var(--ag);color:var(--ag);box-shadow:0 0 10px rgba(0,255,136,.2);}

/* Country buttons */
.btn-country .btn:nth-child(1){border-color:rgba(0,255,136,.25);color:#009944;}
.btn-country .btn:nth-child(2){border-color:rgba(0,212,255,.25);color:#0099bb;}

.btn{padding:9px 16px;border-radius:8px;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.06);color:#90bcd4;font-family:'Space Mono',monospace;font-size:11px;cursor:pointer;transition:all .2s;white-space:nowrap;letter-spacing:.3px;}
.btn:hover{border-color:var(--ab);color:#d0eeff;background:rgba(0,212,255,.08);}
.btn.active{background:rgba(0,212,255,.18);border-color:var(--ab);color:#fff;font-weight:700;box-shadow:0 0 12px rgba(0,212,255,.2);}
.btn.c-in{background:rgba(0,255,136,.12);border-color:rgba(0,255,136,.4);color:#00ee77;font-weight:700;box-shadow:0 0 10px rgba(0,255,136,.12);}
.btn.c-us{background:rgba(0,212,255,.12);border-color:rgba(0,212,255,.4);color:#00d4ff;font-weight:700;box-shadow:0 0 10px rgba(0,212,255,.12);}

/* Index buttons */
.idx-btn{
  padding:11px 22px;border-radius:10px;
  border:1px solid rgba(255,149,0,.25);
  background:rgba(255,149,0,.06);
  color:#cc7700;
  font-family:'Space Mono',monospace;font-size:12px;
  cursor:pointer;transition:all .2s;white-space:nowrap;font-weight:700;
}
.idx-btn:hover{border-color:var(--ao);color:var(--ao);background:rgba(255,149,0,.14);}
.idx-btn.active{background:rgba(255,149,0,.2);border-color:var(--ao);color:#ffaa22;box-shadow:0 0 14px rgba(255,149,0,.25);font-weight:800;}

.sel-wrap{position:relative;}
.sel-wrap::after{content:'▾';position:absolute;right:12px;top:50%;transform:translateY(-50%);color:#5a8aaa;font-size:11px;pointer-events:none;}
select{padding:9px 32px 9px 13px;border-radius:8px;border:1px solid rgba(0,212,255,.25);background:rgba(0,20,40,.7);color:#c8e8ff;font-family:'Space Mono',monospace;font-size:11px;cursor:pointer;outline:none;appearance:none;min-width:190px;transition:all .2s;width:100%;box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
select:focus{border-color:var(--ab);box-shadow:0 0 0 2px rgba(0,212,255,.15),inset 0 1px 0 rgba(255,255,255,.04);}
select:disabled{opacity:.3;cursor:not-allowed;border-color:var(--border);}
select option{background:#061020;color:#c8e8ff;}

.run-btn{padding:10px 28px;border-radius:10px;background:linear-gradient(135deg,var(--ab),var(--ap));border:none;color:#000;font-family:'Syne',sans-serif;font-weight:800;font-size:13px;cursor:pointer;letter-spacing:.5px;transition:transform .15s,box-shadow .15s;white-space:nowrap;}
.run-btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,212,255,.28);}
.run-btn:disabled{opacity:.35;cursor:not-allowed;transform:none;box-shadow:none;}

.run-btn-idx{background:linear-gradient(135deg,var(--ao),#ff6600);}
.run-btn-idx:hover{box-shadow:0 8px 24px rgba(255,149,0,.28);}

/* ─── FLOW BAR ─── */
.flow{display:flex;margin-top:20px;background:rgba(0,10,25,.6);border:1px solid rgba(0,212,255,.15);border-radius:10px;overflow:hidden;}
.fs{flex:1;padding:10px 14px;display:flex;align-items:center;gap:9px;font-size:11px;border-right:1px solid rgba(0,212,255,.08);transition:all .3s;min-width:0;}
.fs:last-child{border-right:none;}
.fs.done{background:rgba(0,255,136,.07);border-right-color:rgba(0,255,136,.1);}
.fs.cur{background:rgba(0,212,255,.09);border-right-color:rgba(0,212,255,.15);}
.fn{width:22px;height:22px;border-radius:50%;border:1.5px solid rgba(255,255,255,.12);display:flex;align-items:center;justify-content:center;font-family:'Space Mono',monospace;font-size:9px;font-weight:700;flex-shrink:0;color:#4a6a88;}
.fs.done .fn{background:var(--ag);border-color:var(--ag);color:#000;box-shadow:0 0 8px rgba(0,255,136,.4);}
.fs.cur .fn{background:rgba(0,212,255,.2);border-color:var(--ab);color:var(--ab);box-shadow:0 0 8px rgba(0,212,255,.3);}
.ftext{display:flex;flex-direction:column;gap:2px;min-width:0;}
.fname{font-size:8px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:#5a8aaa;}
.fs.done .fname{color:rgba(0,255,136,.7);}
.fs.cur .fname{color:rgba(0,212,255,.7);}
.fval{font-size:12px;font-weight:700;color:#a8d0e8;font-family:'Space Mono',monospace;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.fs.done .fval{color:var(--ag);text-shadow:0 0 8px rgba(0,255,136,.3);}
.fs.cur .fval{color:var(--ab);text-shadow:0 0 8px rgba(0,212,255,.3);}

/* ─── PLACEHOLDER ─── */
.ph{text-align:center;padding:70px 40px;background:var(--surface);border:1px dashed var(--border);border-radius:16px;animation:fu .4s ease;}
.ph-icon{font-size:50px;margin-bottom:14px;opacity:.3;}
.ph-text{font-size:17px;font-weight:700;color:var(--muted);margin-bottom:7px;}
.ph-sub{font-family:'Space Mono',monospace;font-size:11px;color:var(--muted2);}
@keyframes fu{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}

/* ─── ANALYSIS CARD ─── */
.ac{background:var(--surface);border:1px solid var(--border);border-radius:16px;overflow:hidden;}
.ac.idx-card{border-color:rgba(255,149,0,.25);}
.ac-hdr{padding:22px 26px;border-bottom:1px solid var(--border);background:linear-gradient(135deg,rgba(0,212,255,.03),rgba(168,85,247,.03));display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:14px;}
.ac.idx-card .ac-hdr{background:linear-gradient(135deg,rgba(255,149,0,.04),rgba(255,100,0,.02));}
.ac-name{font-size:26px;font-weight:800;letter-spacing:-.4px;color:#f0f8ff;}
.ac-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:7px;}
.mtag{padding:3px 10px;border-radius:6px;font-size:10px;font-weight:700;font-family:'Space Mono',monospace;border:1px solid;}
.mc{background:rgba(0,255,136,.12);color:#00ee77;border-color:rgba(0,255,136,.35);font-size:11px;}
.ms{background:rgba(168,85,247,.12);color:#cc88ff;border-color:rgba(168,85,247,.35);font-size:11px;}
.mt{background:rgba(0,212,255,.12);color:#00e0ff;border-color:rgba(0,212,255,.35);font-size:11px;}
.mi{background:rgba(255,149,0,.12);color:#ffaa22;border-color:rgba(255,149,0,.35);font-size:11px;}
.ticker-tag{font-family:'Space Mono',monospace;font-size:11px;color:#88aac8;font-weight:600;}
.ac-pb{text-align:right;}
.ac-price{font-family:'Space Mono',monospace;font-size:34px;font-weight:800;color:#00e5ff;}
.ac.idx-card .ac-price{color:var(--ao);}
.chg-p{color:#00ff88;font-family:'Space Mono',monospace;font-size:14px;margin-top:4px;font-weight:700;}
.chg-n{color:#ff5577;font-family:'Space Mono',monospace;font-size:14px;margin-top:4px;font-weight:700;}
.sig{padding:7px 18px;border-radius:8px;font-weight:800;font-size:12px;letter-spacing:.5px;display:inline-block;margin-top:9px;}
.sig-buy{background:rgba(0,255,136,.1);color:var(--ag);border:1px solid rgba(0,255,136,.28);}
.sig-sell{background:rgba(255,61,107,.1);color:var(--ar);border:1px solid rgba(255,61,107,.28);}
.sig-hold{background:rgba(255,214,0,.07);color:var(--ay);border:1px solid rgba(255,214,0,.2);}
.sig-watch{background:rgba(0,212,255,.07);color:var(--ab);border:1px solid rgba(0,212,255,.2);}

.ac-body{padding:22px 26px;display:flex;flex-direction:column;gap:26px;background:rgba(4,10,20,.5);}
.sec-lbl{font-size:10px;font-weight:800;letter-spacing:2.5px;text-transform:uppercase;color:#a8d8f8;margin-bottom:14px;display:flex;align-items:center;gap:10px;}
.sec-lbl::after{content:'';flex:1;height:1px;background:rgba(120,180,220,.25);}

/* ─── TOW ─── */
.tow-lbls{display:flex;justify-content:space-between;margin-bottom:9px;}
.tow-bear-l{font-size:12px;font-weight:800;color:#ff5577;}
.tow-bull-l{font-size:12px;font-weight:800;color:#00ff88;}
.tow-bar{height:30px;border-radius:15px;overflow:hidden;display:flex;position:relative;background:var(--border);}
.tow-bf{height:100%;background:linear-gradient(90deg,#cc1540,#ff4060);}
.tow-bull{height:100%;background:linear-gradient(90deg,#00bb60,#00ff88);flex:1;}
.tow-div{position:absolute;left:50%;top:-4px;bottom:-4px;width:2px;background:rgba(255,255,255,.1);border-radius:2px;}
.tow-sr{display:flex;justify-content:space-between;align-items:center;margin-top:9px;}
.tow-st{font-family:'Space Mono',monospace;font-size:11px;color:#7aaabb;}
.tow-sn{font-size:20px;font-weight:800;}
.tow-sn.buy{color:var(--ag);}
.tow-sn.sell{color:var(--ar);}
.tow-sn.hold{color:var(--ay);}
.tow-sn.watch{color:var(--ab);}

/* ─── INDICATOR GRID ─── */
.ig{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;}
.ic{background:rgba(12,22,40,.95);border:1px solid rgba(255,255,255,.1);border-radius:11px;padding:14px;display:flex;flex-direction:column;gap:7px;position:relative;overflow:hidden;}
.ic.bull{border-color:rgba(0,255,136,.2);}
.ic.bear{border-color:rgba(255,61,107,.2);}
.ic.neut{border-color:rgba(255,214,0,.2);}
.ic::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;}
.ic.bull::before{background:var(--ag);}
.ic.bear::before{background:var(--ar);}
.ic.neut::before{background:var(--ay);}
.in{font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#a8d0e8;}
.iv{font-family:'Space Mono',monospace;font-size:18px;font-weight:800;}
.iv.bull{color:var(--ag);}
.iv.bear{color:var(--ar);}
.iv.neut{color:var(--ay);}
.ist{font-size:10px;font-weight:700;}
.ist.bull{color:var(--ag);}
.ist.bear{color:var(--ar);}
.ist.neut{color:var(--ay);}
.rsi-bar{height:3px;background:var(--border);border-radius:2px;margin-top:3px;}
.rsi-fill{height:100%;border-radius:2px;}

/* ─── ATR ─── */
.atr-block{background:rgba(255,214,0,.06);border:1px solid rgba(255,214,0,.22);border-radius:11px;padding:16px 20px;display:grid;grid-template-columns:auto 1px 1fr 1fr;gap:18px;align-items:center;}
.atr-lbl{font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#ffcc00;}
.atr-v{font-family:'Space Mono',monospace;font-size:26px;font-weight:800;color:#ffd600;}
.atr-d{background:rgba(255,214,0,.12);align-self:stretch;}
.atr-det{display:flex;flex-direction:column;gap:7px;}
.atr-rl{font-size:10px;font-weight:800;letter-spacing:1.5px;text-transform:uppercase;color:#a8d0e8;}
.atr-rv{font-family:'Space Mono',monospace;font-size:15px;font-weight:800;}
.stop{color:var(--ar);}
.tgt{color:var(--ag);}

/* ─── S&R ─── */
.srg{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
.src{background:rgba(8,15,30,.98);border:1px solid rgba(255,255,255,.15);border-radius:12px;padding:18px;}
.srh{font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;}
.srh.r{color:#ff6688;}
.srh.s{color:#00ff99;}
.srl{display:flex;flex-direction:column;gap:7px;}
.srv{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-radius:7px;}
.srv.r{background:rgba(255,61,107,.09);border:1px solid rgba(255,61,107,.25);}
.srv.s{background:rgba(0,255,136,.07);border:1px solid rgba(0,255,136,.22);}
.srvl{font-size:10px;color:#a8d0e8;font-family:'Space Mono',monospace;font-weight:700;}
.srvp{font-family:'Space Mono',monospace;font-size:14px;font-weight:800;}
.srvp.r{color:var(--ar);}
.srvp.s{color:var(--ag);}
.sr-note{font-family:'Space Mono',monospace;font-size:10px;color:#7aaabb;margin-top:9px;text-align:center;}

/* ─── FUNDAMENTALS ─── */
.fundg{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}
.fc{background:rgba(80,30,160,.12);border:1px solid rgba(168,85,247,.3);border-radius:12px;padding:16px;}
.fl2{font-size:10px;font-weight:800;letter-spacing:2px;text-transform:uppercase;color:#c090ff;margin-bottom:8px;}
.fv{font-family:'Space Mono',monospace;font-size:16px;font-weight:800;color:#dd99ff;}
.fsb{font-size:10px;color:#8ab8d8;margin-top:4px;font-weight:500;}
.eps-u{color:var(--ag);}
.eps-d{color:var(--ar);}
.eps-f{color:var(--ay);}

/* Index — no fundamentals notice */
.idx-notice{
  background:rgba(255,149,0,.06);border:1px solid rgba(255,149,0,.2);
  border-radius:10px;padding:14px 18px;
  font-family:'Space Mono',monospace;font-size:11px;color:#aa7700;
  text-align:center;
}

/* ─── FOOTER ─── */
footer{text-align:center;padding:24px 0 10px;color:#4a6a88;font-size:9px;font-family:'Space Mono',monospace;border-top:1px solid var(--border);margin-top:36px;line-height:2.2;}
footer span{color:#6a8aaa;}

/* ─── RESPONSIVE ─── */
@media(max-width:1100px){.ig{grid-template-columns:repeat(3,1fr);}.fundg{grid-template-columns:repeat(3,1fr);}}
@media(max-width:800px){
  .wrap{padding:14px 16px;}.hdr{flex-direction:column;align-items:flex-start;}.hdr-right{width:100%;}
  .gen-block{width:100%;box-sizing:border-box;min-width:unset;}.gen-live{justify-content:flex-start;}
  .frow{flex-direction:column;gap:14px;}.fg{width:100%;}.sel-wrap{width:100%;}
  select{min-width:unset;width:100%;}.btn-group{width:100%;}
  .run-btn{width:100%;text-align:center;padding:12px 28px;}
  .flow{flex-direction:column;}.fs{border-right:none;border-bottom:1px solid var(--border);}.fs:last-child{border-bottom:none;}
  .ig{grid-template-columns:repeat(2,1fr);}.fundg{grid-template-columns:repeat(2,1fr);}
  .atr-block{grid-template-columns:1fr;gap:12px;}.atr-d{display:none;}.srg{grid-template-columns:1fr;}
  .ac-hdr{flex-direction:column;}.ac-pb{text-align:left;}.ac-price{font-size:26px;}.ac-name{font-size:20px;}
  .mode-toggle{flex-direction:column;}
}
@media(max-width:480px){
  .ig{grid-template-columns:1fr 1fr;}.fundg{grid-template-columns:1fr 1fr;}
  .logo-title{font-size:19px;}.tow-bear-l,.tow-bull-l{font-size:10px;}
  .ac-body{padding:16px;}.ac-hdr{padding:16px;}
}
</style>
</head>
<body>
<div class="wrap">

<!-- HEADER -->
<div class="hdr">
  <div class="logo">
    <div class="logo-icon">📈</div>
    <div>
      <div class="logo-title">Market<span>Intel</span></div>
      <div class="logo-sub">NIFTY 50 · S&P TOP 50 · INDICES · MULTI-TIMEFRAME</div>
    </div>
  </div>
  <div class="hdr-right">
    <div class="gen-block">
      <div class="gen-label">Generated (IST)</div>
      <div class="gen-time">__GENERATED_IST__</div>
      <div class="gen-live"><span class="live"></span><span id="liveClk">--:--:-- IST</span></div>
    </div>
  </div>
</div>

<!-- MODE TOGGLE -->
<div class="mode-toggle">
  <button class="mode-btn active-stocks" id="modeStocks" onclick="setMode('stocks',this)">
    📊 &nbsp;Stock Analysis &nbsp;<small style="opacity:.6;font-weight:400;font-size:12px;">India · USA</small>
  </button>
  <div class="mode-sep"></div>
  <button class="mode-btn" id="modeIndices" onclick="setMode('indices',this)">
    🏦 &nbsp;Index Analysis &nbsp;<small style="opacity:.6;font-weight:400;font-size:12px;">Nifty 50 · Bank Nifty · Fin Nifty</small>
  </button>
</div>

<!-- ════════════════════════════════════ STOCK FILTER PANEL ════════════════════════════════════ -->
<div class="fp" id="panelStocks">
  <div class="fp-title">🎛️ Stock Selection Filters</div>
  <div class="frow">

    <div class="fg">
      <div class="fl">① Country</div>
      <div class="btn-group btn-country">
        <button class="btn c-in" id="btn-IN" onclick="selCountry('IN',this)">🇮🇳 India</button>
        <button class="btn"      id="btn-US" onclick="selCountry('US',this)">🇺🇸 United States</button>
      </div>
    </div>

    <div class="fg">
      <div class="fl">② Sector</div>
      <div class="sel-wrap">
        <select id="secSel" onchange="loadStocks()">
          <option value="">— Select Sector —</option>
        </select>
      </div>
    </div>

    <div class="fg">
      <div class="fl">③ Stock / Company</div>
      <div class="sel-wrap">
        <select id="stkSel" disabled onchange="stkChosen()">
          <option value="">— Select Sector First —</option>
        </select>
      </div>
    </div>

    <div class="fg">
      <div class="fl">④ Timeframe</div>
      <div class="btn-group" id="tfBtns">
        <button class="btn" onclick="setTF('15m',this)">15m</button>
        <button class="btn" onclick="setTF('1H',this)">1H</button>
        <button class="btn active" onclick="setTF('1D',this)">1D</button>
        <button class="btn" onclick="setTF('1W',this)">1W</button>
      </div>
    </div>

    <div class="fg">
      <div class="fl">&nbsp;</div>
      <button class="run-btn" id="runBtn" disabled onclick="showCard()">⚡ Analyze</button>
    </div>
  </div>

  <!-- FLOW BAR -->
  <div class="flow">
    <div class="fs done" id="s1"><div class="fn">✓</div><div class="ftext"><div class="fname">Country</div><div class="fval" id="s1v">🇮🇳 India</div></div></div>
    <div class="fs" id="s2"><div class="fn">2</div><div class="ftext"><div class="fname">Sector</div><div class="fval" id="s2v">Pending</div></div></div>
    <div class="fs" id="s3"><div class="fn">3</div><div class="ftext"><div class="fname">Stock</div><div class="fval" id="s3v">Pending</div></div></div>
    <div class="fs done" id="s4"><div class="fn">✓</div><div class="ftext"><div class="fname">Timeframe</div><div class="fval" id="s4v">1D</div></div></div>
    <div class="fs cur" id="s5"><div class="fn">5</div><div class="ftext"><div class="fname">Analysis</div><div class="fval" id="s5v">Waiting...</div></div></div>
  </div>
</div>

<!-- ════════════════════════════════════ INDEX FILTER PANEL ════════════════════════════════════ -->
<div class="fp fp-index" id="panelIndices" style="display:none;">
  <div class="fp-title">🏦 Indian Index Selection</div>
  <div class="frow">

    <div class="fg">
      <div class="fl fl-idx">① Select Index</div>
      <div class="btn-group" id="idxBtns">
        <button class="idx-btn active" onclick="selIndex('^NSEI','Nifty 50',this)">📈 Nifty 50</button>
        <button class="idx-btn" onclick="selIndex('^NSEBANK','Bank Nifty',this)">🏦 Bank Nifty</button>
        <button class="idx-btn" onclick="selIndex('NIFTY_FIN_SERVICE.NS','Fin Nifty',this)">💳 Fin Nifty</button>
      </div>
    </div>

    <div class="fg">
      <div class="fl fl-tf">② Timeframe</div>
      <div class="btn-group" id="idxTfBtns">
        <button class="btn" onclick="setIdxTF('15m',this)">15m</button>
        <button class="btn" onclick="setIdxTF('1H',this)">1H</button>
        <button class="btn active" onclick="setIdxTF('1D',this)">1D</button>
        <button class="btn" onclick="setIdxTF('1W',this)">1W</button>
      </div>
    </div>

    <div class="fg">
      <div class="fl">&nbsp;</div>
      <button class="run-btn run-btn-idx" id="runIdxBtn" onclick="showIndexCard()">📊 Analyze Index</button>
    </div>

  </div>
</div>

<!-- OUTPUT -->
<div id="out">
  <div class="ph">
    <div class="ph-icon">🔍</div>
    <div class="ph-text">Select a mode above to get started</div>
    <div class="ph-sub">Stock Analysis → Country → Sector → Stock &nbsp;|&nbsp; Index Analysis → Pick Index</div>
  </div>
</div>

<footer>
  <span>MarketIntel</span> · Python + yfinance + pandas-ta · Automated Daily Analysis<br>
  <span>Data is for informational purposes only — Not financial advice.</span>
</footer>
</div>

<script>
const DATA    = __DATA_JSON__;
const IDX_DATA = __IDX_JSON__;

let curCountry = 'IN', curTF = '1D', curTicker = '';
let curIdxTicker = '^NSEI', curIdxName = 'Nifty 50', curIdxTF = '1D';
let curMode = 'stocks';
let _refreshCard = null;

/* ── Live IST Clock ── */
function updateClock(){
  const now=new Date();
  const ist=new Date(now.toLocaleString('en-US',{timeZone:'Asia/Kolkata'}));
  const hh=String(ist.getHours()).padStart(2,'0');
  const mm=String(ist.getMinutes()).padStart(2,'0');
  const ss=String(ist.getSeconds()).padStart(2,'0');
  const el=document.getElementById('liveClk');
  if(el) el.textContent=`${hh}:${mm}:${ss} IST`;
}
updateClock(); setInterval(updateClock,1000);
setInterval(()=>{if(_refreshCard)_refreshCard();},60000);

/* ── Mode toggle ── */
function setMode(mode, btn){
  curMode = mode;
  document.getElementById('modeStocks').className  = 'mode-btn' + (mode==='stocks'?' active-stocks':'');
  document.getElementById('modeIndices').className = 'mode-btn' + (mode==='indices'?' active-indices':'');
  document.getElementById('panelStocks').style.display  = mode==='stocks'  ? '' : 'none';
  document.getElementById('panelIndices').style.display = mode==='indices' ? '' : 'none';
  resetOut();
  _refreshCard = null;
}

/* ─────────────── STOCK MODE ─────────────── */
function selCountry(code, btn){
  curCountry=code;
  ['IN','US'].forEach(c=>document.getElementById('btn-'+c).className='btn');
  btn.className=code==='IN'?'btn c-in':'btn c-us';
  document.getElementById('s1v').textContent=code==='IN'?'🇮🇳 India':'🇺🇸 USA';
  mark('s1','done','✓');
  const sectors=Object.keys(DATA[code]||{});
  const secSel=document.getElementById('secSel');
  secSel.innerHTML='<option value="">— Select Sector —</option>'+sectors.map(s=>`<option value="${s}">${s}</option>`).join('');
  resetStock(); resetOut();
  mark('s2','','2'); document.getElementById('s2v').textContent='Pending';
  mark('s3','','3'); document.getElementById('s3v').textContent='Pending';
}

function loadStocks(){
  const sec=document.getElementById('secSel').value;
  const stkSel=document.getElementById('stkSel');
  if(!sec){
    stkSel.innerHTML='<option>— Select Sector First —</option>';
    stkSel.disabled=true;
    document.getElementById('runBtn').disabled=true;
    resetOut(); mark('s2','','2'); document.getElementById('s2v').textContent='Pending';
    return;
  }
  mark('s2','done','✓'); document.getElementById('s2v').textContent=sec;
  const stocks=DATA[curCountry][sec]||[];
  stkSel.innerHTML='<option value="">— Select Company —</option>'+stocks.map(s=>`<option value="${s.ticker}">${s.name} (${s.ticker})</option>`).join('');
  stkSel.disabled=false;
  mark('s3','','3'); document.getElementById('s3v').textContent='Pending';
  document.getElementById('runBtn').disabled=true; curTicker=''; resetOut();
}

function stkChosen(){
  curTicker=document.getElementById('stkSel').value;
  if(curTicker){
    mark('s3','done','✓'); document.getElementById('s3v').textContent=curTicker;
    document.getElementById('runBtn').disabled=false;
  }else{
    mark('s3','','3'); document.getElementById('s3v').textContent='Pending';
    document.getElementById('runBtn').disabled=true;
  }
  resetOut();
}

function setTF(tf,btn){
  curTF=tf;
  document.querySelectorAll('#tfBtns .btn').forEach(b=>b.className='btn');
  btn.className='btn active';
  document.getElementById('s4v').textContent=tf;
  mark('s4','done','✓');
  if(document.getElementById('out').querySelector('.ac:not(.idx-card)')) showCard(true);
}

function mark(id,cls,num){
  const el=document.getElementById(id);
  el.className='fs'+(cls?' '+cls:'');
  el.querySelector('.fn').textContent=num;
}

function resetStock(){
  const s=document.getElementById('stkSel');
  s.innerHTML='<option>— Select Sector First —</option>';
  s.disabled=true;
  document.getElementById('runBtn').disabled=true;
  curTicker=''; _refreshCard=null;
}

function resetOut(){
  document.getElementById('out').innerHTML=`<div class="ph"><div class="ph-icon">🔍</div><div class="ph-text">Select Country → Sector → Stock → Timeframe</div><div class="ph-sub">Then click ⚡ Analyze to see full technical + fundamental analysis</div></div>`;
  if(curMode==='indices'){
    document.getElementById('out').innerHTML=`<div class="ph"><div class="ph-icon">🏦</div><div class="ph-text">Pick an index and timeframe</div><div class="ph-sub">Then click 📊 Analyze Index</div></div>`;
  }
  mark('s5','cur','5'); document.getElementById('s5v').textContent='Waiting...';
  _refreshCard=null;
}

/* ─────────────── INDEX MODE ─────────────── */
function selIndex(ticker, name, btn){
  curIdxTicker=ticker; curIdxName=name;
  document.querySelectorAll('#idxBtns .idx-btn').forEach(b=>b.className='idx-btn');
  btn.className='idx-btn active';
}

function setIdxTF(tf,btn){
  curIdxTF=tf;
  document.querySelectorAll('#idxTfBtns .btn').forEach(b=>b.className='btn');
  btn.className='btn active';
  if(document.getElementById('out').querySelector('.idx-card')) showIndexCard(true);
}

function showIndexCard(silent=false){
  const entry=IDX_DATA[curIdxTicker];
  const d=entry?(entry[curIdxTF]||Object.values(entry)[0]):null;
  if(!d){
    if(!silent) document.getElementById('out').innerHTML=`<div class="ph"><div class="ph-icon">⚠️</div><div class="ph-text">No data for ${curIdxName} on ${curIdxTF}</div><div class="ph-sub">Try a different timeframe or re-run the script</div></div>`;
    return;
  }
  const html=buildCardHTML(d,true);
  if(silent){
    const outEl=document.getElementById('out');
    const existing=outEl.querySelector('.idx-card');
    if(!existing){outEl.innerHTML=html;return;}
    const priceEl=existing.querySelector('.ac-price');
    const chgEl=existing.querySelector('.chg-p,.chg-n');
    if(priceEl) priceEl.textContent=d.price;
    if(chgEl){chgEl.className=d.change_pos?'chg-p':'chg-n';chgEl.textContent=(d.change_pos?'▲ ':'▼ ')+d.change;}
  }else{
    document.getElementById('out').innerHTML=html;
  }
  _refreshCard=()=>showIndexCard(true);
}

/* ─────────────── BUILD CARD ─────────────── */
function buildCardHTML(d, isIndex=false){
  const sigCls={BUY:'sig-buy',SELL:'sig-sell',HOLD:'sig-hold',WATCH:'sig-watch'}[d.signal]||'sig-watch';
  const sigEmoji={BUY:'✅',SELL:'❌',HOLD:'⏸',WATCH:'👁'}[d.signal]||'⚠️';
  const scoreCls=d.score>=65?'buy':d.score<=40?'sell':d.score>=50?'watch':'hold';

  const rsiCls=r=>r>70?'bear':r<35?'bull':'neut';
  const rsiStat=r=>r>70?'● Overbought':r<35?'● Oversold — Opportunity':'● Neutral Zone';
  const rsiColor=r=>r>70?'var(--ar)':r<35?'var(--ag)':'var(--ay)';
  const rsiPct=Math.min(d.rsi||0,100);

  const volStr=d.volume_ratio!=null?`${d.volume_ratio}x Avg`:'N/A';
  const stochStr=d.stoch_k!=null?`${d.stoch_k}`:'N/A';
  const stochCls=d.stoch_bull?'bull':'bear';
  const stochStat=d.stoch_k>80?'● Overbought':d.stoch_k<20?'● Oversold':'● In Range';

  const tf=isIndex?curIdxTF:curTF;

  const atrSection=d.signal==='BUY'&&!isIndex?`
  <div>
    <div class="sec-lbl">⚡ ATR — Volatility &amp; Trade Sizing (${tf})</div>
    <div class="atr-block">
      <div>
        <div class="atr-lbl">ATR (14)</div>
        <div class="atr-v">${d.atr}</div>
        <div style="font-size:10px;color:#a8d0e8;font-weight:600;margin-top:4px;">Avg True Range<br>TF: ${tf}</div>
      </div>
      <div class="atr-d"></div>
      <div class="atr-det">
        <div><div class="atr-rl">🔴 Stop Loss (1.5× ATR)</div><div class="atr-rv stop">${d.stop_loss}</div></div>
        <div><div class="atr-rl">Risk Per Share</div><div class="atr-rv" style="color:#a8d0e8;font-size:12px;font-weight:700;">Entry − Stop Loss</div></div>
      </div>
      <div class="atr-det">
        <div><div class="atr-rl">🟢 Target (2× ATR)</div><div class="atr-rv tgt">${d.target}</div></div>
        <div><div class="atr-rl">Risk : Reward</div><div class="atr-rv" style="color:#ffd600;font-size:13px;font-weight:800;">1 : 2.0</div></div>
      </div>
    </div>
  </div>`:'';

  const epsCls=d.eps_trend==='up'?'eps-u':d.eps_trend==='down'?'eps-d':'eps-f';
  const epsTxt=d.eps_trend==='up'?'▲ Rising':d.eps_trend==='down'?'▼ Falling':'— Flat';

  const sectorTag=isIndex
    ?`<span class="mtag mi">📊 Index</span>`
    :`<span class="mtag ms">📂 ${d.sector}</span>`;

  const fundamentalsSection=isIndex
    ?`<div><div class="sec-lbl">📋 Index Info</div><div class="idx-notice">ℹ️ Fundamental metrics (P/E, EPS, Market Cap) are not applicable for indices. Technical analysis above reflects price action only.</div></div>`
    :`<div>
      <div class="sec-lbl">📈 Fundamental Overlay</div>
      <div class="fundg">
        <div class="fc"><div class="fl2">P/E Ratio</div><div class="fv">${d.pe}</div><div class="fsb" style="color:#9ab8d8;">Price-to-Earnings</div></div>
        <div class="fc"><div class="fl2">EPS Trend</div><div class="fv ${epsCls}">${epsTxt}</div><div class="fsb" style="color:#9ab8d8;">${d.eps} trailing EPS</div></div>
        <div class="fc"><div class="fl2">Market Cap</div><div class="fv">${d.market_cap}</div><div class="fsb" style="color:#9ab8d8;">Total Capitalization</div></div>
        <div class="fc"><div class="fl2">52-Week Range</div><div class="fv" style="font-size:14px;color:#dd99ff;font-weight:800;">${d.week52_low} – ${d.week52_high}</div><div class="fsb" style="color:#9ab8d8;">Low / High</div></div>
        <div class="fc"><div class="fl2">Beta</div><div class="fv">${d.beta}</div><div class="fsb" style="color:#9ab8d8;">Volatility vs Market</div></div>
        <div class="fc"><div class="fl2">Dividend Yield</div><div class="fv">${d.dividend_yield}</div><div class="fsb" style="color:#9ab8d8;">Annual Yield</div></div>
      </div>
    </div>`;

  return `
  <div class="ac${isIndex?' idx-card':''}">
    <div class="ac-hdr">
      <div>
        <div class="ac-name">${d.name}</div>
        <div class="ac-meta">
          <span class="mtag mc">${d.country_flag} ${d.country==='IN'?'India':'USA'}</span>
          ${sectorTag}
          <span class="mtag mt">⏱ ${tf} Timeframe</span>
          <span class="ticker-tag">${d.ticker}</span>
        </div>
      </div>
      <div class="ac-pb">
        <div class="ac-price">${d.price}</div>
        <div class="${d.change_pos?'chg-p':'chg-n'}">${d.change_pos?'▲':'▼'} ${d.change}</div>
        <div><span class="sig ${sigCls}">${sigEmoji} ${d.signal}</span></div>
      </div>
    </div>

    <div class="ac-body">

      <div>
        <div class="sec-lbl">⚔️ Tug of War — Bull vs Bear Pressure</div>
        <div class="tow-lbls">
          <span class="tow-bear-l">🐻 Bearish ${d.bear_pct}%</span>
          <span class="tow-bull-l">Bullish ${d.bull_pct}% 🐂</span>
        </div>
        <div class="tow-bar">
          <div class="tow-bf" style="width:${d.bear_pct}%"></div>
          <div class="tow-bull"></div>
          <div class="tow-div"></div>
        </div>
        <div class="tow-sr">
          <span class="tow-st">Score:</span>
          <span class="tow-sn ${scoreCls}">${d.score} / 100</span>
          <span class="tow-st">${d.bull_count} of ${d.total_ind} indicators bullish</span>
        </div>
      </div>

      <div>
        <div class="sec-lbl">📊 Technical Indicators — ${tf}</div>
        <div class="ig">
          <div class="ic ${rsiCls(d.rsi)}">
            <div class="in">RSI (14)</div>
            <div class="iv ${rsiCls(d.rsi)}">${d.rsi??'N/A'}</div>
            <div class="rsi-bar"><div class="rsi-fill" style="width:${rsiPct}%;background:${rsiColor(d.rsi)}"></div></div>
            <div class="ist ${rsiCls(d.rsi)}">${rsiStat(d.rsi)}</div>
          </div>
          <div class="ic ${d.macd_bull?'bull':'bear'}">
            <div class="in">MACD</div>
            <div class="iv ${d.macd_bull?'bull':'bear'}" style="font-size:16px;">${d.macd??'N/A'}</div>
            <div class="ist ${d.macd_bull?'bull':'bear'}">${d.macd_bull?'● Bullish Cross':'● Bearish Cross'}</div>
          </div>
          <div class="ic ${d.ema_bull?'bull':'bear'}">
            <div class="in">EMA 50/200</div>
            <div class="iv ${d.ema_bull?'bull':'bear'}" style="font-size:15px;">${d.ema_signal}</div>
            <div class="ist ${d.ema_bull?'bull':'bear'}">${d.ema_bull?'● Uptrend':'● Downtrend'}</div>
          </div>
          <div class="ic ${d.volume_bull?'bull':'neut'}">
            <div class="in">Volume</div>
            <div class="iv ${d.volume_bull?'bull':'neut'}">${volStr}</div>
            <div class="ist ${d.volume_bull?'bull':'neut'}">${d.volume_bull?'● Strong':'● Normal'}</div>
          </div>
          <div class="ic ${stochCls}">
            <div class="in">Stochastic</div>
            <div class="iv ${stochCls}">${stochStr}</div>
            <div class="ist ${stochCls}">${stochStat}</div>
          </div>
        </div>
      </div>

      ${atrSection}

      <div>
        <div class="sec-lbl">📍 Support &amp; Resistance — ${tf} Timeframe | Pivot: ${d.pivot}</div>
        <div class="srg">
          <div class="src">
            <div class="srh r">🔴 Resistance Levels</div>
            <div class="srl">
              <div class="srv r"><span class="srvl">R1 — Nearest</span><span class="srvp r">${d.resistance[0]||'N/A'}</span></div>
              <div class="srv r"><span class="srvl">R2 — Moderate</span><span class="srvp r">${d.resistance[1]||'N/A'}</span></div>
              <div class="srv r"><span class="srvl">R3 — Strong</span><span class="srvp r">${d.resistance[2]||'N/A'}</span></div>
            </div>
          </div>
          <div class="src">
            <div class="srh s">🟢 Support Levels</div>
            <div class="srl">
              <div class="srv s"><span class="srvl">S1 — Nearest</span><span class="srvp s">${d.support[0]||'N/A'}</span></div>
              <div class="srv s"><span class="srvl">S2 — Moderate</span><span class="srvp s">${d.support[1]||'N/A'}</span></div>
              <div class="srv s"><span class="srvl">S3 — Strong</span><span class="srvp s">${d.support[2]||'N/A'}</span></div>
            </div>
          </div>
        </div>
        <div class="sr-note">⚠️ S&amp;R levels dynamically calculated per selected timeframe (${tf})</div>
      </div>

      ${fundamentalsSection}

    </div>
  </div>`;
}

/* ── Show stock card ── */
function showCard(silent=false){
  if(!curTicker) return;
  const sec=document.getElementById('secSel').value;
  const stocks=DATA[curCountry][sec]||[];
  const stockEntry=stocks.find(s=>s.ticker===curTicker);
  const d=stockEntry?(stockEntry.timeframes[curTF]||Object.values(stockEntry.timeframes)[0]):null;

  if(!d){
    if(!silent) document.getElementById('out').innerHTML=`<div class="ph"><div class="ph-icon">⚠️</div><div class="ph-text">No data for ${curTicker} on ${curTF}</div><div class="ph-sub">Try a different timeframe or re-run the script</div></div>`;
    return;
  }

  if(silent){
    const outEl=document.getElementById('out');
    const existing=outEl.querySelector('.ac:not(.idx-card)');
    if(!existing){outEl.innerHTML=buildCardHTML(d);return;}
    const priceEl=existing.querySelector('.ac-price');
    const chgEl=existing.querySelector('.chg-p,.chg-n');
    const towBf=existing.querySelector('.tow-bf');
    const towSn=existing.querySelector('.tow-sn');
    if(priceEl) priceEl.textContent=d.price;
    if(chgEl){chgEl.className=d.change_pos?'chg-p':'chg-n';chgEl.textContent=(d.change_pos?'▲ ':'▼ ')+d.change;}
    if(towBf) towBf.style.width=d.bear_pct+'%';
    if(towSn) towSn.textContent=d.score+' / 100';
  }else{
    document.getElementById('out').innerHTML=buildCardHTML(d);
    mark('s5','done','✓'); document.getElementById('s5v').textContent='✅ Done';
  }
  _refreshCard=()=>showCard(true);
}

/* ── Bootstrap India sectors on load ── */
(function init(){
  const secSel=document.getElementById('secSel');
  secSel.innerHTML='<option value="">— Select Sector —</option>'+
    Object.keys(DATA['IN']||{}).map(s=>`<option value="${s}">${s}</option>`).join('');
})();
</script>
</body>
</html>
"""


def build_html(data: dict, idx_data: dict, generated_at_ist: str) -> str:
    html = HTML_TEMPLATE.replace("__GENERATED_IST__", generated_at_ist)
    html = html.replace("__DATA_JSON__",  json.dumps(data,     ensure_ascii=False))
    html = html.replace("__IDX_JSON__",   json.dumps(idx_data, ensure_ascii=False))
    return html


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MarketIntel Stock Analyser")
    parser.add_argument("--country",   choices=["IN","US","ALL"], default="ALL")
    parser.add_argument("--sector",    default=None)
    parser.add_argument("--ticker",    default=None)
    parser.add_argument("--timeframes",default="1D")
    parser.add_argument("--output",    default="docs/index.html")
    parser.add_argument("--no-indices", action="store_true", help="Skip index analysis")
    args = parser.parse_args()

    tfs = [t.strip() for t in args.timeframes.split(",") if t.strip() in TF_CONFIG]
    if not tfs:
        tfs = ["1D"]

    countries = ["IN","US"] if args.country == "ALL" else [args.country]

    ist_offset = timedelta(hours=5, minutes=30)
    now_ist = datetime.now(timezone.utc) + ist_offset
    generated_at_ist = now_ist.strftime("%Y-%m-%d %H:%M IST")

    print(f"\n{'='*60}")
    print(f"  MarketIntel Analysis — {generated_at_ist}")
    print(f"  Countries: {countries} | Timeframes: {tfs}")
    print(f"{'='*60}\n")

    # ── Stock Analysis ──
    output_data = {}
    for country in countries:
        output_data[country] = {}
        universe = STOCKS.get(country, {})
        for sector, stocks in universe.items():
            if args.sector and sector != args.sector:
                continue
            print(f"\n[{country}] {sector}")
            sector_dict = {}
            for ticker, name in stocks:
                if args.ticker and ticker != args.ticker:
                    continue
                for tf in tfs:
                    result = analyse_stock(ticker, name, country, sector, tf)
                    if result:
                        if ticker not in sector_dict:
                            sector_dict[ticker] = {
                                "ticker":       ticker,
                                "name":         name,
                                "country":      country,
                                "country_flag": result["country_flag"],
                                "sector":       sector,
                                "timeframes":   {}
                            }
                        sector_dict[ticker]["timeframes"][tf] = result
            if sector_dict:
                output_data[country][sector] = list(sector_dict.values())

    # ── Index Analysis ──
    idx_data = {}
    if not args.no_indices:
        print(f"\n{'='*60}")
        print("  Analysing Indian Indices ...")
        print(f"{'='*60}")
        for country, idx_map in INDICES.items():
            for ticker, name in idx_map.items():
                print(f"\n[INDEX] {name} ({ticker})")
                idx_data[ticker] = {}
                for tf in tfs:
                    result = analyse_stock(ticker, name, country, "Index", tf, is_index=True)
                    if result:
                        idx_data[ticker][tf] = result

    html = build_html(output_data, idx_data, generated_at_ist)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")

    total_stocks = sum(
        len(v) * len(list(v[0]["timeframes"].keys()))
        for country in output_data.values()
        for v in country.values() if v
    )
    total_idx = sum(len(tfs_dict) for tfs_dict in idx_data.values())

    print(f"\n{'='*60}")
    print(f"  ✅ Done!")
    print(f"  📊 Stocks analysed:  {total_stocks} stock-timeframe combinations")
    print(f"  🏦 Indices analysed: {total_idx} index-timeframe combinations")
    print(f"  📄 HTML saved to:    {out_path.resolve()}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
