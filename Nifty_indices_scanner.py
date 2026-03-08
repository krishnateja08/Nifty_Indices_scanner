"""
NIFTY SECTOR SCANNER — Falling-Knife Filter + Progress Ring UI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CHANGES in v2 (logic borrowed from Nifty50_stocksanalyzer_v5.4):

  FIX-1  RSI → Wilder's smoothing (EMA com=period-1)
           Old: simple rolling mean — overstated RSI by 5-10 pts vs TradingView.
           New: matches TradingView exactly. A stock previously showing RSI 52
           (neutral/pass) may now correctly show 44 (weak-momentum penalty).

  FIX-2  Data fetch 6mo → 1y, min bars 50 → 200
           Old: 6mo data meant SMA200 was almost never calculated (only ~126
           bars available), so the MA-Bearish check in falling_knife_checks
           always defaulted to False — missing the long-term trend entirely.
           New: full year of data ensures SMA200 is always present.

  FIX-3  RSI Direction — Rising / Falling / Flat
           New helper calculate_rsi_direction() returns slope, direction, and
           a 'strong' flag (|slope|>8). Wired into the Trend Veto Gate below.
           Shows in terminal output next to RSI value.

  FIX-4  Trend Veto Gate (V54-1 from Stocks Analyzer)
           If 3+ of these bearish signals fire simultaneously:
             · SMA20 declining (today < 5 bars ago)
             · Death cross forming (SMA20 < SMA50)
             · MACD bearish crossover
             · RSI < 50 (momentum lost)
             · Price < SMA50
             · RSI falling sharply (direction=Falling AND |slope|>8)
           → Verdict is hard-capped to AVOID regardless of danger_score or
           reversal count. Prevents a stock in confirmed distribution from
           being labelled VALID just because it has 1 reversal candle.

UNCHANGED:
  ✅ Removed "v3" from title
  ✅ Explain box moved BELOW Sector Scorecard
  ✅ Email now uses dark background (no more white email)
  ✅ All sector configs, falling-knife checks, reversal confirmations,
     sector bullish gate, scoring, HTML/email generation — untouched.

REQUIREMENTS:
    pip install yfinance pandas numpy pytz
ENV VARS (optional):
    GMAIL_USER, GMAIL_APP_PASS, RECEIVER_EMAIL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime
import pytz
import contextlib
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import numpy as np

warnings.filterwarnings("ignore")

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
GMAIL_USER     = os.getenv('GMAIL_USER')
GMAIL_APP_PASS = os.getenv('GMAIL_APP_PASS')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL', 'krishnateja.sapbasis@gmail.com')

@contextlib.contextmanager
def suppress_stdout():
    with contextlib.redirect_stdout(io.StringIO()):
        yield

# ─── ANSI TERMINAL COLOURS ────────────────────────────────────────────────────
RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
CYAN = "\033[96m"; BLUE = "\033[94m"; MAGENTA = "\033[95m"; RESET = "\033[0m"

# ─── SECTOR ICONS ─────────────────────────────────────────────────────────────
SECTOR_ICONS = {
    "Nifty Bank":             "🏦",
    "Nifty IT":               "💻",
    "Nifty Pharma":           "💊",
    "Nifty Realty":           "🏢",
    "Nifty FMCG":             "🛒",
    "Nifty Metal":            "⚙️",
    "Nifty Auto":             "🚗",
    "Nifty Energy":           "⚡",
    "Nifty Consumer Durables":"📺",
    "Nifty Private Bank":     "🏛️",
}

# =============================================================================
#  SECTOR CONFIG
# =============================================================================
sectors_config = {
    "Nifty Bank": {
        "ticker": "^NSEBANK",
        "stocks": {
            "HDFCBANK.NS":   {"weight": 28.1, "industry": "Private Bank"},
            "ICICIBANK.NS":  {"weight": 19.3, "industry": "Private Bank"},
            "SBIN.NS":       {"weight": 18.9, "industry": "PSU Bank"},
            "AXISBANK.NS":   {"weight": 10.0, "industry": "Private Bank"},
            "KOTAKBANK.NS":  {"weight":  8.8, "industry": "Private Bank"},
            "INDUSINDBK.NS": {"weight":  5.0, "industry": "Private Bank"},
            "BANKBARODA.NS": {"weight":  3.5, "industry": "PSU Bank"},
            "PNB.NS":        {"weight":  2.5, "industry": "PSU Bank"},
        }
    },
    "Nifty IT": {
        "ticker": "^CNXIT",
        "stocks": {
            "INFY.NS":       {"weight": 27.0, "industry": "IT Services"},
            "TCS.NS":        {"weight": 22.0, "industry": "IT Services"},
            "HCLTECH.NS":    {"weight": 11.0, "industry": "IT Services"},
            "TECHM.NS":      {"weight": 10.0, "industry": "IT Services"},
            "WIPRO.NS":      {"weight":  7.0, "industry": "IT Services"},
            "LTIM.NS":       {"weight":  6.0, "industry": "IT Services"},
            "PERSISTENT.NS": {"weight":  4.0, "industry": "Product Engineering"},
            "COFORGE.NS":    {"weight":  3.0, "industry": "IT Consulting"},
        }
    },
    "Nifty Pharma": {
        "ticker": "^CNXPHARMA",
        "stocks": {
            "SUNPHARMA.NS":  {"weight": 21.3, "industry": "Pharma - Domestic"},
            "DIVISLAB.NS":   {"weight":  9.7, "industry": "Pharma - API"},
            "CIPLA.NS":      {"weight":  9.4, "industry": "Pharma - Domestic"},
            "DRREDDY.NS":    {"weight":  9.4, "industry": "Pharma - Global"},
            "LUPIN.NS":      {"weight":  6.6, "industry": "Pharma - Global"},
            "AUROPHARMA.NS": {"weight":  6.0, "industry": "Pharma - Global"},
            "BIOCON.NS":     {"weight":  5.5, "industry": "Biotech"},
            "ALKEM.NS":      {"weight":  4.5, "industry": "Pharma - Domestic"},
        }
    },
    "Nifty Realty": {
        "ticker": "^CNXREALTY",
        "stocks": {
            "DLF.NS":        {"weight": 21.1, "industry": "Real Estate - Commercial"},
            "PHOENIXLTD.NS": {"weight": 16.1, "industry": "Real Estate - Retail"},
            "LODHA.NS":      {"weight": 14.2, "industry": "Real Estate - Residential"},
            "PRESTIGE.NS":   {"weight": 12.8, "industry": "Real Estate - Mixed"},
            "GODREJPROP.NS": {"weight": 12.2, "industry": "Real Estate - Residential"},
            "OBEROIRLTY.NS": {"weight":  8.5, "industry": "Real Estate - Luxury"},
            "BRIGADE.NS":    {"weight":  6.0, "industry": "Real Estate - Mixed"},
        }
    },
    "Nifty FMCG": {
        "ticker": "^CNXFMCG",
        "stocks": {
            "ITC.NS":        {"weight": 33.0, "industry": "Diversified FMCG"},
            "HINDUNILVR.NS": {"weight": 18.0, "industry": "Personal Care"},
            "NESTLEIND.NS":  {"weight":  8.0, "industry": "Packaged Foods"},
            "TATACONSUM.NS": {"weight":  7.0, "industry": "Beverages"},
            "BRITANNIA.NS":  {"weight":  6.0, "industry": "Biscuits"},
            "DABUR.NS":      {"weight":  5.5, "industry": "Ayurvedic Products"},
            "MARICO.NS":     {"weight":  4.5, "industry": "Hair & Skin Care"},
            "GODREJCP.NS":   {"weight":  4.0, "industry": "Home Care"},
        }
    },
    "Nifty Metal": {
        "ticker": "^CNXMETAL",
        "stocks": {
            "TATASTEEL.NS":  {"weight": 17.0, "industry": "Steel"},
            "HINDALCO.NS":   {"weight": 15.0, "industry": "Aluminum"},
            "JSWSTEEL.NS":   {"weight": 14.0, "industry": "Steel"},
            "JINDALSTEL.NS": {"weight": 12.0, "industry": "Steel"},
            "NMDC.NS":       {"weight":  8.0, "industry": "Iron Ore"},
            "VEDL.NS":       {"weight":  7.5, "industry": "Diversified Metals"},
            "SAIL.NS":       {"weight":  6.5, "industry": "Steel - PSU"},
            "HINDZINC.NS":   {"weight":  6.0, "industry": "Zinc"},
        }
    },
    "Nifty Auto": {
        "ticker": "^CNXAUTO",
        "stocks": {
            "MARUTI.NS":     {"weight": 20.0, "industry": "Passenger Vehicles"},
            "M&M.NS":        {"weight": 12.0, "industry": "SUVs & Tractors"},
            "BAJAJ-AUTO.NS": {"weight": 10.0, "industry": "Two Wheelers"},
            "HEROMOTOCO.NS": {"weight":  9.0, "industry": "Two Wheelers"},
            "EICHERMOT.NS":  {"weight":  8.0, "industry": "Premium Two Wheelers"},
            "TVSMOTOR.NS":   {"weight":  6.0, "industry": "Two Wheelers"},
            "BOSCHLTD.NS":   {"weight":  5.0, "industry": "Auto Components"},
        }
    },
    "Nifty Energy": {
        "ticker": "^CNXENERGY",
        "stocks": {
            "RELIANCE.NS":   {"weight": 35.0, "industry": "Oil & Gas - Integrated"},
            "ONGC.NS":       {"weight": 15.0, "industry": "Oil & Gas - Upstream"},
            "NTPC.NS":       {"weight": 12.0, "industry": "Power Generation"},
            "POWERGRID.NS":  {"weight": 10.0, "industry": "Power Transmission"},
            "COALINDIA.NS":  {"weight":  8.0, "industry": "Coal Mining"},
            "ADANIGREEN.NS": {"weight":  7.0, "industry": "Renewable Energy"},
            "BPCL.NS":       {"weight":  6.0, "industry": "Oil Refining"},
            "IOC.NS":        {"weight":  5.0, "industry": "Oil Refining"},
        }
    },
    "Nifty Consumer Durables": {
        "ticker": "^CNXCONSUM",
        "stocks": {
            "TITAN.NS":      {"weight": 25.0, "industry": "Jewelry & Watches"},
            "VOLTAS.NS":     {"weight": 12.0, "industry": "Air Conditioners"},
            "HAVELLS.NS":    {"weight": 11.0, "industry": "Electrical Equipment"},
            "CROMPTON.NS":   {"weight":  8.0, "industry": "Consumer Electricals"},
            "WHIRLPOOL.NS":  {"weight":  7.0, "industry": "Home Appliances"},
            "BLUESTARCO.NS": {"weight":  6.0, "industry": "Air Conditioning"},
            "SYMPHONY.NS":   {"weight":  5.0, "industry": "Air Coolers"},
        }
    },
}

# =============================================================================
#  INDICATORS
# =============================================================================
def calculate_rsi(series, period=14):
    # Wilder's smoothing — matches TradingView exactly (fixes 5-10pt overstatement
    # vs the old simple rolling mean). Borrowed from Stocks Analyzer v5.4.
    delta    = series.diff()
    gain     = delta.where(delta > 0, 0)
    loss     = (-delta.where(delta < 0, 0))
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs       = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_rsi_direction(series, period=14, lookback=5):
    """
    RSI slope direction — Rising / Falling / Flat.
    Borrowed from Stocks Analyzer v5.4 (calculate_rsi_slope).
    Catches topping-out stocks that still have an OK RSI *value* but are
    actively rolling over (e.g. RSI was 71, now 46 = 'Falling Strong').
    Returns dict with keys: slope, direction, strong, rsi_5bar
    """
    try:
        delta    = series.diff()
        gain     = delta.where(delta > 0, 0)
        loss     = (-delta.where(delta < 0, 0))
        avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
        avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
        rsi_ser  = (100 - (100 / (1 + avg_gain / avg_loss))).dropna()

        if len(rsi_ser) < lookback + 2:
            return {'slope': 0, 'direction': 'Flat', 'strong': False,
                    'rsi_5bar': float(rsi_ser.iloc[-1]) if len(rsi_ser) else 50.0}

        rsi_now  = float(rsi_ser.iloc[-1])
        rsi_prev = float(rsi_ser.iloc[-(lookback + 1)])
        slope    = round(rsi_now - rsi_prev, 2)

        if slope > 3:
            direction = 'Rising'
        elif slope < -3:
            direction = 'Falling'
        else:
            direction = 'Flat'

        return {
            'slope':     slope,
            'direction': direction,
            'strong':    abs(slope) > 8,   # sharp move (e.g. 71→46)
            'rsi_5bar':  round(rsi_prev, 1),
        }
    except Exception:
        return {'slope': 0, 'direction': 'Flat', 'strong': False, 'rsi_5bar': 50.0}

def calculate_macd(series):
    ema12  = series.ewm(span=12, adjust=False).mean()
    ema26  = series.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist   = macd - signal
    return macd.iloc[-1], signal.iloc[-1], hist.iloc[-1]

def calculate_atr(df, period=14):
    high, low, close = df['High'], df['Low'], df['Close']
    tr = pd.concat([
        high - low,
        abs(high - close.shift(1)),
        abs(low  - close.shift(1))
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1/period, adjust=False).mean().iloc[-1]

# =============================================================================
#  FALLING-KNIFE DETECTION  (6 checks)
# =============================================================================
def falling_knife_checks(data):
    close  = data['Close']
    checks = {}
    flags  = []

    if len(close) >= 200:
        sma20  = close.rolling(20).mean().iloc[-1]
        sma50  = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        ma_bear = (sma20 < sma50) and (sma50 < sma200)
        checks['ma_bearish'] = ma_bear
        if ma_bear: flags.append("MA Bearish (20<50<200)")
    else:
        checks['ma_bearish'] = False

    if len(close) >= 50:
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        ltp   = close.iloc[-1]
        below = (ltp < sma20) and (ltp < sma50)
        checks['price_below_mas'] = below
        if below: flags.append("Price Below SMA20 & SMA50")
    else:
        checks['price_below_mas'] = False

    if len(close) >= 20:
        rsi_s   = calculate_rsi(close)
        rsi_now = rsi_s.iloc[-1]
        rsi_5ag = rsi_s.iloc[-6]
        falling = (rsi_now < rsi_5ag - 3)
        checks['rsi_falling'] = falling
        if falling: flags.append(f"RSI Falling ({rsi_5ag:.0f}→{rsi_now:.0f})")
    else:
        checks['rsi_falling'] = False

    if len(data) >= 10:
        recent    = data.tail(10)
        up_days   = recent[recent['Close'] >= recent['Open']]
        dn_days   = recent[recent['Close'] <  recent['Open']]
        avg_up    = up_days['Volume'].mean()   if len(up_days)  > 0 else 0
        avg_dn    = dn_days['Volume'].mean()   if len(dn_days)  > 0 else 0
        dist_bear = avg_dn > avg_up * 1.2
        checks['distribution'] = dist_bear
        if dist_bear: flags.append("Institutions Selling")
    else:
        checks['distribution'] = False

    if len(data) >= 5:
        last5     = data.tail(5)
        red_days  = (last5['Close'] < last5['Open']).sum()
        consec    = red_days >= 4
        checks['consecutive_red'] = consec
        if consec: flags.append(f"{red_days}/5 Days Red")
    else:
        checks['consecutive_red'] = False

    if len(close) >= 35:
        macd_v, sig_v, hist_v      = calculate_macd(close)
        _,      _,     hist_prev   = calculate_macd(close.iloc[:-1])
        macd_bear = (macd_v < sig_v) and (hist_v < 0) and (hist_v <= hist_prev)
        checks['macd_bearish'] = macd_bear
        if macd_bear: flags.append("MACD Bearish & Worsening")
    else:
        checks['macd_bearish'] = False

    danger_score = sum(checks.values())
    return checks, flags, danger_score


# =============================================================================
#  REVERSAL CONFIRMATIONS
# =============================================================================
def reversal_confirmations(data):
    confirms = []
    close    = data['Close']
    volume   = data['Volume']

    if len(close) >= 20:
        rsi_s   = calculate_rsi(close)
        rsi_now = rsi_s.iloc[-1]
        rsi_2ag = rsi_s.iloc[-3]
        if rsi_now < 40 and rsi_now > rsi_2ag + 1.5:
            confirms.append("RSI Turning Up")

    if len(data) >= 20:
        avg_vol  = volume.tail(20).mean()
        last_vol = volume.iloc[-1]
        last_red = data['Close'].iloc[-1] < data['Open'].iloc[-1]
        if last_red and last_vol > avg_vol * 2.0:
            confirms.append("Volume Climax")

    if len(data) >= 3:
        c1o, c1c = data['Open'].iloc[-3], data['Close'].iloc[-3]
        c0o, c0c = data['Open'].iloc[-1], data['Close'].iloc[-1]
        if c1c < c1o and c0c > c0o and c0c > c1o:
            confirms.append("Bullish Engulfing")

    if len(close) >= 252:
        low_52w = close.tail(252).min()
        if close.iloc[-1] <= low_52w * 1.03 and close.iloc[-1] > close.iloc[-2]:
            confirms.append("52W Low Bounce")

    if len(close) >= 35:
        _, _, h0 = calculate_macd(close)
        _, _, h1 = calculate_macd(close.iloc[:-1])
        _, _, h2 = calculate_macd(close.iloc[:-2])
        if h0 < 0 and h0 > h1 > h2:
            confirms.append("MACD Hist Improving")

    if len(close) >= 25:
        sma_now  = close.rolling(20).mean().iloc[-1]
        sma_3ago = close.rolling(20).mean().iloc[-4]
        if sma_now >= sma_3ago * 0.999:
            confirms.append("SMA20 Stabilizing")

    return confirms, len(confirms)


# =============================================================================
#  FETCH + ANALYZE
# =============================================================================
def fetch_and_analyze(ticker, period="1y"):
    # Period upgraded 6mo → 1y so SMA200 is always available for the
    # falling-knife MA-bearish check (borrowed from Stocks Analyzer v5.4).
    try:
        with suppress_stdout():
            data = yf.download(ticker, period=period, interval="1d",
                               progress=False, multi_level_index=False)
        if data.empty or len(data) < 200:
            return None

        close = data['Close']
        ltp   = float(close.iloc[-1])

        prev_close    = float(close.iloc[-2])
        day_chg_pct   = ((ltp - prev_close) / prev_close) * 100
        week_chg_pct  = ((ltp - float(close.iloc[-6]))  / float(close.iloc[-6]))  * 100 if len(close) >= 6  else 0.0
        month_chg_pct = ((ltp - float(close.iloc[-22])) / float(close.iloc[-22])) * 100 if len(close) >= 22 else 0.0

        high_52w = float(data['High'].tail(252).max() if len(data) >= 252 else data['High'].max())
        low_52w  = float(data['Low'].tail(252).min()  if len(data) >= 252 else data['Low'].min())

        sma20  = float(close.rolling(20).mean().iloc[-1])
        sma50  = float(close.rolling(50).mean().iloc[-1])  if len(close) >= 50  else None
        sma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None

        rsi_series    = calculate_rsi(close)
        rsi_now       = float(rsi_series.iloc[-1])
        rsi_5ago      = float(rsi_series.iloc[-6])
        rsi_slope     = rsi_now - rsi_5ago

        # FIX-3: RSI direction (Rising/Falling/Flat) — borrowed from Stocks Analyzer.
        # Catches stocks topping out even when RSI value still looks acceptable.
        rsi_dir_data  = calculate_rsi_direction(close)
        rsi_direction = rsi_dir_data['direction']    # 'Rising' | 'Falling' | 'Flat'
        rsi_slope_strong = rsi_dir_data['strong']    # True if |slope| > 8

        atr     = float(calculate_atr(data))
        atr_pct = (atr / ltp) * 100

        fk_checks, fk_flags, danger_score = falling_knife_checks(data)
        rev_confirms, rev_count           = reversal_confirmations(data)

        is_falling_knife = danger_score >= 3
        has_reversal     = rev_count >= 1

        # ── Trend Veto Gate (borrowed from Stocks Analyzer V54-1) ─────────────
        # Count active bearish signals across all dimensions.
        # If 3+ fire simultaneously the stock is in a CONFIRMED downtrend —
        # no reversal count can rescue it.  Cap verdict to AVOID.
        sma20_series    = close.rolling(20).mean()
        sma50_val       = float(close.rolling(50).mean().iloc[-1])
        sma20_val       = float(sma20_series.iloc[-1])
        sma20_5bar_ago  = float(sma20_series.iloc[-6]) if len(sma20_series) >= 6 else sma20_val
        sma20_declining = sma20_val < sma20_5bar_ago
        death_cross     = sma20_val < sma50_val
        macd_v, sig_v, _ = calculate_macd(close) if len(close) >= 35 else (0, 0, 0)
        macd_bearish    = macd_v < sig_v

        veto_signals = sum([
            bool(sma20_declining),                            # SMA20 rolling over
            bool(death_cross),                                # SMA20 < SMA50
            bool(macd_bearish),                               # MACD bearish crossover
            bool(rsi_now < 50),                               # momentum lost
            bool(ltp < sma50_val),                            # below medium trend
            bool(rsi_direction == 'Falling' and rsi_slope_strong),  # sharp RSI drop
        ])
        trend_veto_fired = veto_signals >= 3
        # ──────────────────────────────────────────────────────────────────────

        # Verdict — original logic preserved; veto gate applied on top
        if trend_veto_fired:
            verdict = "AVOID"          # hard cap regardless of danger_score
        elif is_falling_knife:
            verdict = "AVOID"
        elif danger_score == 2 and not has_reversal:
            verdict = "AVOID"
        elif danger_score <= 1 and has_reversal:
            verdict = "STRONG WATCH" if rsi_now < 35 else "VALID"
        elif danger_score <= 2 and has_reversal:
            verdict = "CAUTION"
        else:
            verdict = "WATCH"

        score = 0
        if not is_falling_knife:
            if rsi_now < 25:    score += 20
            elif rsi_now < 30:  score += 15
            elif rsi_now < 40:  score += 10
            if rsi_slope > 3:   score += 20
            elif rsi_slope > 0: score += 10
            score += rev_count * 10
            if not fk_checks.get('ma_bearish', False): score += 10
            dist_from_high = ((high_52w - ltp) / ltp) * 100
            if dist_from_high > 30:   score += 10
            elif dist_from_high > 15: score += 5
        score = min(score, 100)

        stop_loss   = ltp - (atr * 1.5)
        target_1    = ltp + (atr * 2.0)
        target_2    = ltp + (atr * 3.5)
        risk_reward = ((target_1 - ltp) / (ltp - stop_loss)) if (ltp - stop_loss) > 0 else 0.0

        return {
            "ltp":               ltp,
            "day_chg_pct":       day_chg_pct,
            "week_chg_pct":      week_chg_pct,
            "month_chg_pct":     month_chg_pct,
            "rsi":               rsi_now,
            "rsi_slope":         rsi_slope,
            "rsi_direction":     rsi_direction,        # NEW: Rising/Falling/Flat
            "rsi_slope_strong":  rsi_slope_strong,     # NEW: True if |slope|>8
            "sma20":             sma20,
            "sma50":             sma50,
            "sma200":            sma200,
            "high_52w":          high_52w,
            "low_52w":           low_52w,
            "atr":               atr,
            "atr_pct":           atr_pct,
            "danger_score":      danger_score,
            "fk_flags":          fk_flags,
            "rev_confirms":      rev_confirms,
            "rev_count":         rev_count,
            "is_falling_knife":  is_falling_knife,
            "veto_signals":      veto_signals,         # NEW: count of bearish signals
            "trend_veto_fired":  trend_veto_fired,     # NEW: True if hard-capped
            "verdict":           verdict,
            "score":             score,
            "stop_loss":         stop_loss,
            "target_1":          target_1,
            "target_2":          target_2,
            "risk_reward":       risk_reward,
        }
    except Exception:
        return None


# =============================================================================
#  SECTOR BULLISH CHECK
# =============================================================================
def is_sector_bullish(idx_data):
    if not idx_data:
        return False, []

    reasons = []
    passes  = 0

    rsi       = idx_data['rsi']
    rsi_slope = idx_data['rsi_slope']
    if rsi < 50 and rsi_slope > -2:
        passes += 1
        reasons.append(f"✅ RSI {rsi:.1f} — not overbought & slope OK")
    else:
        reasons.append(f"❌ RSI {rsi:.1f} slope {rsi_slope:+.1f} — trending down")

    if idx_data['danger_score'] <= 2:
        passes += 1
        reasons.append(f"✅ Danger Score {idx_data['danger_score']}/6 — acceptable")
    else:
        reasons.append(f"❌ Danger Score {idx_data['danger_score']}/6 — falling knife")

    wk = idx_data['week_chg_pct']
    if idx_data['rev_count'] >= 1 or (wk and wk > 0.5):
        passes += 1
        conf_str = ", ".join(idx_data['rev_confirms'][:2]) if idx_data['rev_confirms'] else f"week +{wk:.1f}%"
        reasons.append(f"✅ Reversal evidence: {conf_str}")
    else:
        reasons.append(f"❌ No reversal confirmation — week {wk:+.1f}%")

    return passes >= 2, reasons


# =============================================================================
#  SVG RING HELPER
# =============================================================================
def rsi_ring_svg(rsi_val, is_bull):
    circ   = 251.3
    offset = circ * (1 - min(max(rsi_val, 0), 100) / 100)
    color  = "#00ff95" if is_bull else "#ff6b9d"
    glow   = "0 0 8px #00ff95" if is_bull else "0 0 8px #ff6b9d"
    return f"""<svg width="74" height="74" viewBox="0 0 100 100" class="rsi-svg">
  <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="8"/>
  <circle cx="50" cy="50" r="40" fill="none"
    stroke="{color}" stroke-width="8" stroke-linecap="round"
    stroke-dasharray="{circ:.1f}"
    stroke-dashoffset="{offset:.1f}"
    transform="rotate(-90 50 50)"
    style="filter:drop-shadow({glow});transition:stroke-dashoffset 1s ease"/>
</svg>"""


# =============================================================================
#  EMAIL-SAFE SVG RING (no filter, inline style for email clients)
# =============================================================================
def rsi_ring_svg_email(rsi_val, is_bull):
    circ   = 251.3
    offset = circ * (1 - min(max(rsi_val, 0), 100) / 100)
    color  = "#00ff95" if is_bull else "#ff6b9d"
    return f"""<svg width="80" height="80" viewBox="0 0 100 100">
  <circle cx="50" cy="50" r="40" fill="none" stroke="#1a2a3a" stroke-width="8"/>
  <circle cx="50" cy="50" r="40" fill="none"
    stroke="{color}" stroke-width="8" stroke-linecap="round"
    stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}"
    transform="rotate(-90 50 50)"/>
  <text x="50" y="54" text-anchor="middle" fill="{color}"
    font-size="18" font-weight="bold" font-family="monospace">{rsi_val:.0f}</text>
</svg>"""


# =============================================================================
#  HTML GENERATOR  (web version — unchanged layout)
# =============================================================================
def generate_html(sector_analysis, bullish_sectors, ist_time):

    all_valid   = []
    all_avoided = []
    for sn, analysis in sector_analysis.items():
        for st in analysis['stocks']:
            st['sector'] = sn
            if st['verdict'] in ('VALID', 'STRONG WATCH') and sn in bullish_sectors:
                all_valid.append(st)
            if st['verdict'] == 'AVOID':
                all_avoided.append(st)

    top_picks   = sorted(all_valid,   key=lambda x: x['score'],        reverse=True)[:20]
    strong_buys = [s for s in all_valid if s['score'] >= 60 and s['rsi'] < 32]
    top_symbol  = top_picks[0]['symbol'] if top_picks else '—'

    total_sectors = len(sector_analysis)
    bullish_count = len(bullish_sectors)

    # ── Sector Cards ──────────────────────────────────────────
    sector_cards_html = ""
    for sn, analysis in sector_analysis.items():
        idx    = analysis['index_data']
        is_bull = sn in bullish_sectors
        icon   = SECTOR_ICONS.get(sn, "📊")
        ring   = rsi_ring_svg(idx['rsi'], is_bull)

        danger_pct   = (idx['danger_score'] / 6) * 100
        danger_color = "#00ff95" if idx['danger_score'] == 0 else \
                       "#ffa502" if idx['danger_score'] <= 2 else "#ff6b9d"

        slope_color = "#00ff95" if idx['rsi_slope'] > 0 else "#ff6b9d"
        week_color  = "#00ff95" if idx['week_chg_pct'] > 0 else "#ff6b9d"
        rsi_color   = "#00ff95" if is_bull else "#ff6b9d"

        badge_cls  = "badge-bull" if is_bull else "badge-bear"
        badge_text = "🟢 BULLISH" if is_bull else "🔴 BLOCKED"
        card_cls   = "s5-card bull" if is_bull else "s5-card bear"

        rev_short = idx['rev_confirms'][0] if idx['rev_confirms'] else \
                    (f"week {idx['week_chg_pct']:+.1f}%" if idx['week_chg_pct'] else "—")

        anchor_id  = sn.lower().replace(" ", "-")
        # Cards for bullish sectors scroll to their detail table;
        # blocked sectors scroll to the avoided table instead.
        if is_bull:
            click_js  = f"onclick=\"document.getElementById('sector-{anchor_id}').scrollIntoView({{behavior:'smooth',block:'start'}});this.classList.add('card-flash')\""
            click_tip = "title=\"Click to jump to sector detail ↓\""
        else:
            click_js  = "onclick=\"document.getElementById('avoided-section').scrollIntoView({behavior:'smooth',block:'start'})\""
            click_tip = "title=\"Click to see blocked stocks ↓\""

        sector_cards_html += f"""
        <div class="{card_cls} clickable-card" {click_js} {click_tip}>
          <div class="s5-header">
            <div class="s5-icon">{icon}</div>
            <div class="s5-name">{sn}</div>
          </div>
          <div class="s5-ring-wrap">{ring}
            <div class="s5-ring-label">
              <div class="s5-rsi-num" style="color:{rsi_color}">{idx['rsi']:.1f}</div>
              <div class="s5-rsi-sub">RSI</div>
            </div>
          </div>
          <div class="{badge_cls}">{badge_text}</div>
          <div class="s5-stats">
            <div class="s5-stat">
              <div class="s5-sl">Slope</div>
              <div class="s5-sv" style="color:{slope_color}">{idx['rsi_slope']:+.1f} {'↑' if idx['rsi_slope']>0 else '↓'}</div>
            </div>
            <div class="s5-stat">
              <div class="s5-sl">Week</div>
              <div class="s5-sv" style="color:{week_color}">{idx['week_chg_pct']:+.2f}%</div>
            </div>
            <div class="s5-stat" style="grid-column:span 2">
              <div class="s5-sl">Key Signal</div>
              <div class="s5-sv" style="font-size:.72rem;color:#80deea">{rev_short}</div>
            </div>
          </div>
          <div class="s5-danger-bar">
            <div class="s5-db-label">
              <span>Danger</span>
              <span style="color:{danger_color};font-weight:700">{idx['danger_score']}/6</span>
            </div>
            <div class="s5-db-track">
              <div class="s5-db-fill" style="width:{danger_pct:.0f}%;background:{danger_color}"></div>
            </div>
          </div>
        </div>"""

    # ── Verdict helpers ───────────────────────────────────────
    def verdict_tag(v):
        m = {
            'VALID':        ('#00ff95', '#000', '✅ VALID BUY'),
            'STRONG WATCH': ('#00d9ff', '#000', '🔥 STRONG WATCH'),
            'CAUTION':      ('#ffa502', '#000', '⚠️ CAUTION'),
            'WATCH':        ('#555555', '#fff', '👀 WATCH'),
            'AVOID':        ('#ff6b9d', '#000', '🚫 AVOID'),
        }
        bg, fg, lbl = m.get(v, ('#555','#fff', v))
        return f'<span class="vtag" style="background:{bg};color:{fg}">{lbl}</span>'

    def danger_chips(flags):
        if not flags:
            return '<span style="color:#00ff95;font-size:.68rem;font-weight:700">✅ No Flags</span>'
        return "".join([f'<span class="warn-chip">⛔ {f}</span>' for f in flags[:3]])

    def rev_chips(confirms):
        if not confirms:
            return '<span style="color:#555;font-size:.68rem">—</span>'
        return "".join([f'<span class="rev-chip">✅ {c}</span>' for c in confirms[:2]])

    # ── Buy table rows ────────────────────────────────────────
    buy_rows = ""
    for i, s in enumerate(top_picks, 1):
        dc  = "#00ff95" if s['day_chg_pct']  > 0 else "#ff6b9d"
        wc  = "#00ff95" if s['week_chg_pct'] > 0 else "#ff6b9d"
        rc  = "#ff6b9d" if s['rsi'] < 30 else ("#ffa502" if s['rsi'] < 50 else "#00ff95")
        sc  = "#00ff95" if s['score'] >= 60 else ("#ffa502" if s['score'] >= 40 else "#888")
        rr  = s['risk_reward']
        rrc = "#00ff95" if rr >= 2 else ("#ffa502" if rr >= 1 else "#ff6b9d")
        buy_rows += f"""
        <tr class="{'top-row' if s['score']>=60 else ''}">
          <td style="color:#2a5070;font-weight:700">{i}</td>
          <td>
            <div style="font-weight:800;color:#e0f2f1">{s['symbol']}</div>
            <div style="font-size:.68rem;color:#4a7a78">{s.get('sector','')}</div>
            <div style="font-size:.65rem;color:#2a5070">{s.get('industry','')}</div>
          </td>
          <td><span style="font-family:'JetBrains Mono',monospace;font-weight:700;color:#f59e0b">₹{s['ltp']:.2f}</span></td>
          <td style="color:{dc};font-weight:600">{s['day_chg_pct']:+.2f}%</td>
          <td style="color:{wc};font-weight:600">{s['week_chg_pct']:+.2f}%</td>
          <td>
            <div style="color:{rc};font-weight:800;font-family:'JetBrains Mono',monospace">{s['rsi']:.1f}</div>
            <div style="font-size:.65rem;color:{'#00ff95' if s['rsi_slope']>0 else '#ff6b9d'}">{s['rsi_slope']:+.1f} slope</div>
          </td>
          <td style="color:{sc};font-weight:800;font-family:'JetBrains Mono',monospace">{s['score']}/100</td>
          <td>{danger_chips(s['fk_flags'])}</td>
          <td>{rev_chips(s['rev_confirms'])}</td>
          <td>
            <div style="color:#00ff95;font-weight:700;font-family:'JetBrains Mono',monospace">₹{s['target_1']:.2f}</div>
            <div style="font-size:.68rem;color:#2dd4bf">T2: ₹{s['target_2']:.2f}</div>
          </td>
          <td style="color:#ff6b9d;font-weight:700;font-family:'JetBrains Mono',monospace">₹{s['stop_loss']:.2f}</td>
          <td style="color:{rrc};font-weight:800;font-family:'JetBrains Mono',monospace">{rr:.1f}×</td>
          <td>{verdict_tag(s['verdict'])}</td>
        </tr>"""

    # ── Avoided rows ──────────────────────────────────────────
    avoided_rows = ""
    for s in sorted(all_avoided, key=lambda x: x['danger_score'], reverse=True)[:15]:
        dc = "#00ff95" if s['day_chg_pct'] > 0 else "#ff6b9d"
        wc = "#00ff95" if s['week_chg_pct'] > 0 else "#ff6b9d"
        avoided_rows += f"""
        <tr>
          <td style="font-weight:800;color:#e0f2f1">{s['symbol']}<br><span style="font-size:.65rem;color:#4a7a78">{s.get('sector','')}</span></td>
          <td style="font-family:'JetBrains Mono',monospace;color:#f59e0b">₹{s['ltp']:.2f}</td>
          <td style="color:{dc}">{s['day_chg_pct']:+.2f}%</td>
          <td style="color:{wc}">{s['week_chg_pct']:+.2f}%</td>
          <td style="color:#ffa502;font-weight:700">{s['rsi']:.1f}</td>
          <td><span style="color:#ff6b9d;font-weight:800;font-family:'JetBrains Mono',monospace">{s['danger_score']}/6</span></td>
          <td>{danger_chips(s['fk_flags'])}</td>
        </tr>"""

    # ── Sector detail ─────────────────────────────────────────
    sector_detail_html = ""
    for sn in bullish_sectors:
        analysis = sector_analysis[sn]
        idx      = analysis['index_data']
        icon     = SECTOR_ICONS.get(sn, "📊")
        sl_c     = "#00ff95" if idx['rsi_slope'] > 0 else "#ff6b9d"
        wk_c     = "#00ff95" if idx['week_chg_pct'] > 0 else "#ff6b9d"
        dn_c     = "#00ff95" if idx['danger_score'] <= 1 else ("#ffa502" if idx['danger_score'] <= 2 else "#ff6b9d")

        stocks_sorted = sorted(analysis['stocks'], key=lambda x: x['score'], reverse=True)
        rows = ""
        for st in stocks_sorted:
            dc   = "#00ff95" if st['day_chg_pct']  > 0 else "#ff6b9d"
            wc   = "#00ff95" if st['week_chg_pct'] > 0 else "#ff6b9d"
            rc   = "#ff6b9d" if st['rsi'] < 30 else ("#ffa502" if st['rsi'] < 50 else "#00ff95")
            sc_c = "#00ff95" if st['score'] >= 60 else ("#ffa502" if st['score'] >= 40 else "#888")
            rows += f"""
            <tr class="{'top-row' if st['score']>=60 else ''}">
              <td style="font-weight:800;color:#e0f2f1">{st['symbol']}</td>
              <td style="color:#4a7a78">{st.get('weight',0):.1f}%</td>
              <td style="font-family:'JetBrains Mono',monospace;color:#f59e0b">₹{st['ltp']:.2f}</td>
              <td style="color:{dc}">{st['day_chg_pct']:+.2f}%</td>
              <td style="color:{wc}">{st['week_chg_pct']:+.2f}%</td>
              <td>
                <span style="color:{rc};font-weight:800">{st['rsi']:.1f}</span>
                <span style="color:{'#00ff95' if st['rsi_slope']>0 else '#ff6b9d'};font-size:.68rem"> ({st['rsi_slope']:+.1f})</span>
              </td>
              <td style="color:{sc_c};font-weight:800">{st['score']}/100</td>
              <td>{danger_chips(st['fk_flags'])}</td>
              <td>{rev_chips(st['rev_confirms'])}</td>
              <td style="color:#00ff95;font-family:'JetBrains Mono',monospace">₹{st['target_1']:.2f}</td>
              <td style="color:#ff6b9d;font-family:'JetBrains Mono',monospace">₹{st['stop_loss']:.2f}</td>
              <td>{verdict_tag(st['verdict'])}</td>
            </tr>"""

        anchor_id = sn.lower().replace(" ", "-")
        sector_detail_html += f"""
        <div class="detail-block" id="sector-{anchor_id}">
          <div class="detail-header">
            <span class="detail-icon">{icon}</span>
            <h3>{sn.upper()}</h3>
            <div class="detail-meta">
              RSI <strong>{idx['rsi']:.1f}</strong> &nbsp;|&nbsp;
              Slope <strong style="color:{sl_c}">{idx['rsi_slope']:+.1f}</strong> &nbsp;|&nbsp;
              Week <strong style="color:{wk_c}">{idx['week_chg_pct']:+.2f}%</strong> &nbsp;|&nbsp;
              Danger <strong style="color:{dn_c}">{idx['danger_score']}/6</strong>
            </div>
          </div>
          <div class="tbl-wrap">
            <table>
              <thead><tr>
                <th>Stock</th><th>Wt%</th><th>LTP</th><th>Day%</th><th>Week%</th>
                <th>RSI (slope)</th><th>Score</th><th>⚠ Danger</th>
                <th>✅ Reversals</th><th>Target</th><th>Stop</th><th>Verdict</th>
              </tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>
        </div>"""

    # ══════════════════════════════════════════════════════════
    #  FULL HTML  — "v3" removed from title
    #              explain box moved BELOW scorecard
    # ══════════════════════════════════════════════════════════
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>🎯 Nifty Sector Scanner</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --nc:#00d9ff;--ng:#00ff95;--nr:#ff6b9d;
  --no:#ffa502;--bg:#000814;--bg2:#001328;
  --card:#030d18;--border:rgba(0,217,255,.12);
}}
body{{
  font-family:'Plus Jakarta Sans',sans-serif;
  background:linear-gradient(135deg,var(--bg2),var(--bg));
  min-height:100vh;padding:20px;color:#cfd8dc;font-size:13px;
}}
body::before{{
  content:'';position:fixed;top:-100px;right:-100px;
  width:500px;height:500px;border-radius:50%;
  background:radial-gradient(circle,rgba(0,217,255,.06),transparent 70%);
  pointer-events:none;z-index:0;
}}
.container{{
  max-width:1500px;margin:auto;
  background:rgba(0,8,20,.97);
  border-radius:16px;
  box-shadow:0 0 60px rgba(0,217,255,.2);
  overflow:hidden;
  border:1px solid var(--border);
  position:relative;z-index:1;
}}
.header{{
  background:linear-gradient(135deg,var(--bg2) 0%,#003d7a 100%);
  color:var(--nc);padding:28px 28px 24px;
  border-bottom:2px solid var(--nc);
  display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:16px;
}}
.header h1{{font-size:clamp(1.2rem,2.5vw,1.8rem);font-weight:800;
  text-shadow:0 0 20px rgba(0,217,255,.7);margin-bottom:4px}}
.header .sub{{font-size:.8rem;color:#80deea;opacity:.85;line-height:1.5}}
#live-clock{{
  font-family:'JetBrains Mono',monospace;
  background:var(--nc);color:#000;
  border-radius:30px;padding:10px 22px;
  font-weight:700;font-size:.82rem;
  white-space:nowrap;
  box-shadow:0 0 20px rgba(0,217,255,.5);
  flex-shrink:0;
}}
.summary{{
  display:flex;flex-wrap:wrap;gap:12px;
  padding:20px 28px;
  background:rgba(0,31,63,.35);
  border-bottom:1px solid rgba(0,217,255,.12);
}}
.stat{{
  flex:1 1 120px;
  background:rgba(0,217,255,.06);
  border-radius:10px;padding:14px 16px;
  text-align:center;
  border-left:3px solid var(--nc);
  transition:transform .2s;
}}
.stat:hover{{transform:translateY(-2px)}}
.stat .num{{font-size:1.9rem;font-weight:800;color:var(--nc);line-height:1}}
.stat .lbl{{font-size:.65rem;color:#4a7a78;text-transform:uppercase;
  letter-spacing:.8px;margin-top:5px}}
.explain-wrap{{
  display:flex;gap:14px;flex-wrap:wrap;
  padding:20px 28px 4px;
}}
.explain-panel{{flex:1 1 300px;border-radius:12px;overflow:hidden;}}
.ep-head{{
  display:flex;align-items:center;gap:10px;
  padding:12px 16px;font-size:.82rem;font-weight:800;
}}
.ep-head.danger{{
  background:rgba(255,107,157,.1);color:var(--nr);
  border:1px solid rgba(255,107,157,.25);border-bottom:none;
}}
.ep-head.ok{{
  background:rgba(0,217,255,.08);color:var(--nc);
  border:1px solid rgba(0,217,255,.2);border-bottom:none;
}}
.ep-body{{
  display:flex;flex-wrap:wrap;gap:6px;
  padding:14px 16px;border-radius:0 0 12px 12px;
}}
.ep-body.danger{{
  background:rgba(255,107,157,.04);
  border:1px solid rgba(255,107,157,.2);border-top:none;
}}
.ep-body.ok{{
  background:rgba(0,217,255,.03);
  border:1px solid rgba(0,217,255,.15);border-top:none;
}}
.ep-chip{{padding:5px 12px;border-radius:20px;font-size:.7rem;font-weight:700;}}
.ep-chip.danger{{
  background:rgba(255,107,157,.12);color:#ff9ab0;
  border:1px solid rgba(255,107,157,.28);
}}
.ep-chip.ok{{
  background:rgba(0,217,255,.1);color:#80deea;
  border:1px solid rgba(0,217,255,.22);
}}
.section{{padding:24px 28px}}
.section-title{{
  font-size:1rem;font-weight:800;color:var(--nc);
  padding:10px 16px;
  border-left:4px solid var(--nc);
  background:linear-gradient(90deg,rgba(0,217,255,.08),transparent);
  border-radius:4px;margin-bottom:18px;
  text-shadow:0 0 8px rgba(0,217,255,.3);
}}
.s5-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(140px,1fr));
  gap:8px;
  overflow-x:auto;
}}
.s5-card{{
  background:linear-gradient(145deg,#030f1c,#010810);
  border-radius:12px;padding:12px 8px;
  text-align:center;
  transition:transform .25s,box-shadow .25s;
  border:1px solid rgba(0,217,255,.1);
  min-width:130px;
}}
.s5-card:hover{{transform:translateY(-3px);box-shadow:0 8px 20px rgba(0,217,255,.15);}}
.clickable-card{{cursor:pointer;position:relative;}}
.clickable-card::after{{
  content:'↓';
  position:absolute;bottom:6px;right:8px;
  font-size:.55rem;color:rgba(0,217,255,.35);
  font-weight:700;letter-spacing:.5px;
  transition:color .2s;
}}
.clickable-card:hover::after{{color:rgba(0,217,255,.9);}}
.clickable-card.bull::after{{content:'↓ Detail';}}
.clickable-card.bear::after{{content:'↓ Avoided';}}
@keyframes card-flash{{
  0%{{box-shadow:0 0 0 0 rgba(0,217,255,.6)}}
  50%{{box-shadow:0 0 0 8px rgba(0,217,255,0)}}
  100%{{box-shadow:0 0 0 0 rgba(0,217,255,0)}}
}}
.card-flash{{animation:card-flash .6s ease;}}
.s5-card.bull{{border-color:rgba(0,255,149,.2);}}
.s5-card.bear{{border-color:rgba(255,107,157,.18);}}
.s5-header{{display:flex;align-items:center;justify-content:center;gap:4px;margin-bottom:8px;}}
.s5-icon{{font-size:.9rem}}
.s5-name{{font-size:.58rem;font-weight:800;letter-spacing:.5px;text-transform:uppercase;color:#80deea;line-height:1.2;}}
.s5-ring-wrap{{position:relative;width:74px;height:74px;margin:0 auto 8px;}}
.rsi-svg{{display:block}}
.s5-ring-label{{
  position:absolute;top:50%;left:50%;
  transform:translate(-50%,-50%);text-align:center;line-height:1.2;
}}
.s5-rsi-num{{font-family:'JetBrains Mono',monospace;font-size:.95rem;font-weight:800;}}
.s5-rsi-sub{{font-size:.45rem;color:#2a5070;letter-spacing:1.5px;text-transform:uppercase;}}
.badge-bull{{
  display:inline-block;padding:3px 8px;border-radius:30px;
  font-size:.58rem;font-weight:800;margin-bottom:8px;
  background:rgba(0,255,149,.12);color:#00ff95;border:1px solid rgba(0,255,149,.28);
}}
.badge-bear{{
  display:inline-block;padding:3px 8px;border-radius:30px;
  font-size:.58rem;font-weight:800;margin-bottom:8px;
  background:rgba(255,107,157,.1);color:#ff6b9d;border:1px solid rgba(255,107,157,.25);
}}
.s5-stats{{display:grid;grid-template-columns:1fr 1fr;gap:4px;margin-bottom:8px;text-align:left;}}
.s5-stat{{background:rgba(255,255,255,.03);border-radius:5px;padding:5px 6px;}}
.s5-sl{{font-size:.5rem;color:#2a5070;letter-spacing:.8px;text-transform:uppercase;margin-bottom:1px;}}
.s5-sv{{font-family:'JetBrains Mono',monospace;font-size:.7rem;font-weight:600;color:#e0f2f1;}}
.s5-danger-bar{{margin-top:4px}}
.s5-db-label{{font-size:.55rem;color:#2a5070;display:flex;justify-content:space-between;margin-bottom:3px;}}
.s5-db-track{{height:4px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;}}
.s5-db-fill{{height:100%;border-radius:3px;transition:width .8s ease}}
.tbl-wrap{{overflow-x:auto;border-radius:8px;border:1px solid rgba(0,217,255,.12);margin-bottom:8px;}}
table{{width:100%;border-collapse:collapse;min-width:900px}}
thead tr{{background:linear-gradient(135deg,var(--bg2),#003d7a)}}
th{{color:var(--nc);padding:10px 10px;text-align:left;font-size:.68rem;font-weight:700;text-transform:uppercase;letter-spacing:.6px;white-space:nowrap;}}
td{{padding:9px 10px;border-bottom:1px solid rgba(0,217,255,.07);color:#cfd8dc;vertical-align:middle;}}
tbody tr:hover{{background:rgba(0,217,255,.04)}}
.top-row{{background:linear-gradient(90deg,rgba(0,217,255,.07),transparent)!important;border-left:3px solid var(--nc);}}
tbody tr:last-child td{{border-bottom:none}}
.vtag{{display:inline-block;padding:4px 10px;border-radius:5px;font-size:.68rem;font-weight:800;white-space:nowrap;}}
.warn-chip{{
  display:inline-block;
  background:rgba(255,107,157,.12);border:1px solid rgba(255,107,157,.28);
  color:#ff9ab0;padding:2px 7px;border-radius:10px;
  font-size:.62rem;font-weight:700;margin:1px;white-space:nowrap;
}}
.rev-chip{{
  display:inline-block;
  background:rgba(0,217,255,.1);border:1px solid rgba(0,217,255,.22);
  color:#80deea;padding:2px 7px;border-radius:10px;
  font-size:.62rem;font-weight:700;margin:1px;white-space:nowrap;
}}
.detail-block{{margin-bottom:24px;border:1px solid rgba(0,217,255,.15);border-radius:12px;overflow:hidden;}}
.detail-header{{
  background:linear-gradient(135deg,var(--bg2),#003d7a);
  padding:14px 18px;border-bottom:2px solid var(--nc);
  display:flex;align-items:center;gap:10px;flex-wrap:wrap;
}}
.detail-icon{{font-size:1.2rem}}
.detail-header h3{{font-size:.95rem;font-weight:800;color:var(--nc);text-shadow:0 0 8px rgba(0,217,255,.5);flex:1;}}
.detail-meta{{font-size:.78rem;color:#80deea;width:100%}}
.avoided-section{{
  padding:24px 28px;
  background:rgba(255,107,157,.03);
  border-top:1px solid rgba(255,107,157,.12);
}}
.avoided-title{{
  font-size:1rem;font-weight:800;color:var(--nr);
  padding:10px 16px;
  border-left:4px solid var(--nr);
  background:linear-gradient(90deg,rgba(255,107,157,.08),transparent);
  border-radius:4px;margin-bottom:10px;
}}
.disclaimer{{
  margin:10px 28px 24px;padding:14px 18px;
  background:rgba(255,107,157,.06);
  border-left:3px solid var(--nr);border-radius:6px;
  font-size:.75rem;color:#ffb3d9;line-height:1.6;
}}
.footer{{
  text-align:center;padding:18px;
  background:rgba(0,31,63,.35);
  border-top:1px solid rgba(0,217,255,.1);
  font-size:.75rem;color:#4a7a78;
}}
/* ── TABLET (≤900px) ─────────────────────────────────────── */
@media(max-width:900px){{
  .s5-grid{{grid-template-columns:repeat(5,1fr);}}
  table{{min-width:700px}}
}}
/* ── MOBILE LARGE (≤640px) ───────────────────────────────── */
@media(max-width:640px){{
  body{{padding:8px}}
  .container{{border-radius:10px}}
  .header{{flex-direction:column;align-items:flex-start;padding:16px}}
  .header h1{{font-size:1.1rem}}
  #live-clock{{width:100%;text-align:center;font-size:.75rem;padding:8px 14px}}
  .summary{{padding:10px;gap:8px}}
  .stat{{flex:1 1 90px;padding:10px 8px}}
  .stat .num{{font-size:1.4rem}}
  .s5-grid{{grid-template-columns:repeat(2,1fr);gap:6px}}
  .s5-card{{min-width:0;padding:10px 6px}}
  .s5-name{{font-size:.55rem}}
  .s5-ring-wrap{{width:60px;height:60px}}
  .rsi-svg{{width:60px;height:60px}}
  .s5-rsi-num{{font-size:.8rem}}
  .explain-wrap{{flex-direction:column;padding:12px 12px 4px}}
  .explain-panel{{flex:1 1 100%}}
  .section{{padding:12px 10px}}
  .section-title{{font-size:.85rem;padding:8px 12px}}
  .avoided-section{{padding:12px 10px}}
  .disclaimer{{margin:8px 10px 16px;font-size:.7rem}}
  .footer{{font-size:.68rem;padding:12px}}
  .detail-header{{padding:10px 12px}}
  .detail-header h3{{font-size:.82rem}}
  .detail-meta{{font-size:.7rem}}
  th{{font-size:.62rem;padding:8px 7px}}
  td{{padding:7px 7px;font-size:.72rem}}
  .vtag{{font-size:.6rem;padding:3px 7px}}
  .warn-chip,.rev-chip{{font-size:.58rem;padding:2px 5px}}
}}
/* ── MOBILE SMALL (≤400px) ───────────────────────────────── */
@media(max-width:400px){{
  .s5-grid{{grid-template-columns:repeat(2,1fr)}}
  .stat{{flex:1 1 80px}}
  .stat .num{{font-size:1.2rem}}
}}
</style>
</head>
<body>
<div class="container">

<!-- ── HEADER  (no "v3") ────────────────────────────────────── -->
<div class="header">
  <div>
    <h1>🎯 Nifty Sector Scanner</h1>
    <div class="sub">
      Falling-Knife Filter · 6-Point Danger Check · Reversal Confirmation<br>
      Report generated: {ist_time}
    </div>
  </div>
  <div id="live-clock">🕐 Loading...</div>
</div>

<!-- ── SUMMARY STRIP ──────────────────────────────────────────── -->
<div class="summary">
  <div class="stat">
    <div class="num">{total_sectors}</div>
    <div class="lbl">Sectors Scanned</div>
  </div>
  <div class="stat" style="border-color:var(--ng)">
    <div class="num" style="color:var(--ng)">{bullish_count}</div>
    <div class="lbl">Truly Bullish</div>
  </div>
  <div class="stat" style="border-color:var(--nc)">
    <div class="num" style="color:var(--nc)">{len(top_picks)}</div>
    <div class="lbl">Valid Buys</div>
  </div>
  <div class="stat" style="border-color:var(--no)">
    <div class="num" style="color:var(--no)">{len(strong_buys)}</div>
    <div class="lbl">Strong Watch</div>
  </div>
  <div class="stat" style="border-color:var(--nr)">
    <div class="num" style="color:var(--nr)">{len(all_avoided)}</div>
    <div class="lbl">Avoided (Knife)</div>
  </div>
  <div class="stat" style="border-color:var(--nc)">
    <div class="num" style="color:var(--nc);font-size:1.1rem;padding-top:8px">{top_symbol}</div>
    <div class="lbl">Top Pick</div>
  </div>
</div>

<!-- ── SECTOR SCORECARD ────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">🏆 Sector Scorecard</div>
  <div style="overflow-x:auto;">
    <div class="s5-grid">{sector_cards_html}</div>
  </div>
</div>

<!-- ── EXPLAIN BOX — now BELOW scorecard ──────────────────────── -->
<div class="explain-wrap">
  <div class="explain-panel">
    <div class="ep-head danger">⛔ 6 Danger Signals — Any 3 or more = BLOCKED</div>
    <div class="ep-body danger">
      <span class="ep-chip danger">⛔ MA Bearish (20&lt;50&lt;200)</span>
      <span class="ep-chip danger">⛔ Price Below SMA20 &amp; SMA50</span>
      <span class="ep-chip danger">⛔ RSI Still Falling</span>
      <span class="ep-chip danger">⛔ Institutions Selling</span>
      <span class="ep-chip danger">⛔ 4+ of 5 Days Red</span>
      <span class="ep-chip danger">⛔ MACD Bearish &amp; Worsening</span>
    </div>
  </div>
  <div class="explain-panel">
    <div class="ep-head ok">✅ Reversal Confirmations — At Least 1 Required</div>
    <div class="ep-body ok">
      <span class="ep-chip ok">✅ RSI Turning Up</span>
      <span class="ep-chip ok">✅ Volume Climax</span>
      <span class="ep-chip ok">✅ Bullish Engulfing</span>
      <span class="ep-chip ok">✅ 52W Low Bounce</span>
      <span class="ep-chip ok">✅ MACD Histogram Improving</span>
      <span class="ep-chip ok">✅ SMA20 Stabilizing</span>
    </div>
  </div>
</div>

<!-- ── BUY TABLE ──────────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">🟢 Top Valid Buy Recommendations — Knife-Filtered</div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>#</th><th>Stock</th><th>LTP</th><th>Day%</th><th>Week%</th>
        <th>RSI (slope)</th><th>Score</th><th>⚠ Danger</th><th>✅ Reversals</th>
        <th>Target</th><th>Stop Loss</th><th>R:R</th><th>Verdict</th>
      </tr></thead>
      <tbody>{buy_rows if buy_rows else
        '<tr><td colspan="13" style="text-align:center;color:#2a5070;padding:24px">No valid buys — market in downtrend. All falling knives blocked.</td></tr>'
      }</tbody>
    </table>
  </div>
</div>

<!-- ── SECTOR DETAIL ──────────────────────────────────────────── -->
<div class="section">
  <div class="section-title">📊 Bullish Sector Detail</div>
  {sector_detail_html if sector_detail_html else
   '<p style="color:#2a5070;padding:12px">No bullish sectors with clean setups detected.</p>'}
</div>

<!-- ── AVOIDED TABLE ──────────────────────────────────────────── -->
<div class="avoided-section" id="avoided-section">
  <div class="avoided-title">🚫 Stocks Avoided — Falling Knife Detected</div>
  <p style="color:rgba(255,107,157,.6);font-size:.75rem;margin-bottom:14px">
    These stocks had RSI &lt; 40 and would have been recommended by the old script.
    They are blocked because 3 or more danger signals are active.
  </p>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Stock</th><th>LTP</th><th>Day%</th><th>Week%</th>
        <th>RSI</th><th>Danger</th><th>Reasons Blocked</th>
      </tr></thead>
      <tbody>{avoided_rows if avoided_rows else
        '<tr><td colspan="7" style="text-align:center;color:#2a5070;padding:16px">No stocks blocked this session.</td></tr>'
      }</tbody>
    </table>
  </div>
</div>

<!-- ── DISCLAIMER ─────────────────────────────────────────────── -->
<div class="disclaimer">
  <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational purposes only.
  Past performance does not guarantee future results. Falling-knife filters reduce but do not eliminate loss risk.
  Always use strict stop losses and consult a SEBI-registered financial advisor before making any investment decision.
</div>

<div class="footer">
  © 2026 Nifty Sector Scanner · Falling-Knife Filter Edition · For Educational Purposes Only
</div>
</div>

<script>
function updateClock() {{
  var now  = new Date();
  var opts = {{
    timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric',
    hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:true
  }};
  var el = document.getElementById('live-clock');
  if (el) el.textContent = '🕐 ' + now.toLocaleString('en-IN', opts) + ' IST';
}}
updateClock();
setInterval(updateClock, 1000);
window.addEventListener('load', function() {{
  // RSI ring animation
  document.querySelectorAll('.rsi-svg circle:last-child').forEach(function(c) {{
    var final = c.getAttribute('stroke-dashoffset');
    c.setAttribute('stroke-dashoffset', '251.3');
    setTimeout(function() {{ c.style.transition = 'stroke-dashoffset 1.2s ease'; c.setAttribute('stroke-dashoffset', final); }}, 200);
  }});
  // Remove card-flash class after animation completes
  document.querySelectorAll('.clickable-card').forEach(function(card) {{
    card.addEventListener('animationend', function() {{
      card.classList.remove('card-flash');
    }});
  }});
}});
</script>
</body></html>"""
    return html


# =============================================================================
#  EMAIL HTML  — DARK THEME (fixes the "too white" problem)
# =============================================================================
def generate_email_html(sector_analysis, bullish_sectors, ist_time, top_picks, all_avoided):
    """
    A self-contained dark-themed email that renders well in Gmail/Outlook.
    Uses inline styles only (no <style> tags — many email clients strip them).
    Background: #000814  Text: #cfd8dc  Accent: #00d9ff
    """

    total   = len(sector_analysis)
    bull_n  = len(bullish_sectors)
    top_sym = top_picks[0]['symbol'] if top_picks else '—'
    avoid_n = len(all_avoided)

    # ── Summary stats row ─────────────────────────────────────
    def stat_cell(num, label, color="#00d9ff"):
        return f"""<td style="width:16%;text-align:center;padding:16px 8px;
          background:#001328;border-radius:8px;border-left:3px solid {color}">
          <div style="font-size:28px;font-weight:800;color:{color};
            font-family:'Courier New',monospace;line-height:1">{num}</div>
          <div style="font-size:10px;color:#4a7a78;text-transform:uppercase;
            letter-spacing:1px;margin-top:6px">{label}</div>
        </td>"""

    stats_row = f"""
    <table width="100%" cellpadding="0" cellspacing="6" style="margin-bottom:24px">
      <tr>
        {stat_cell(total,   'Sectors Scanned', '#00d9ff')}
        <td style="width:1%"></td>
        {stat_cell(bull_n,  'Bullish',          '#00ff95')}
        <td style="width:1%"></td>
        {stat_cell(len(top_picks), 'Valid Buys', '#00d9ff')}
        <td style="width:1%"></td>
        {stat_cell(avoid_n, 'Avoided (Knife)',  '#ff6b9d')}
        <td style="width:1%"></td>
        {stat_cell(top_sym, 'Top Pick',         '#ffa502')}
      </tr>
    </table>"""

    # ── Sector scorecard rows ──────────────────────────────────
    sector_rows = ""
    for sn, analysis in sector_analysis.items():
        idx     = analysis['index_data']
        is_bull = sn in bullish_sectors
        icon    = SECTOR_ICONS.get(sn, "📊")
        ring    = rsi_ring_svg_email(idx['rsi'], is_bull)

        badge_bg  = "rgba(0,255,149,.15)"  if is_bull else "rgba(255,107,157,.15)"
        badge_col = "#00ff95"              if is_bull else "#ff6b9d"
        badge_txt = "🟢 BULLISH"           if is_bull else "🔴 BLOCKED"
        sl_col    = "#00ff95" if idx['rsi_slope']   > 0 else "#ff6b9d"
        wk_col    = "#00ff95" if idx['week_chg_pct']> 0 else "#ff6b9d"
        dn_col    = "#00ff95" if idx['danger_score']<= 1 else ("#ffa502" if idx['danger_score']<= 2 else "#ff6b9d")
        rev_short = idx['rev_confirms'][0] if idx['rev_confirms'] else \
                    (f"week {idx['week_chg_pct']:+.1f}%" if idx['week_chg_pct'] else "—")

        sector_rows += f"""
        <tr>
          <td style="padding:10px;background:#030f1c;border-radius:8px;
            border-left:3px solid {'#00ff95' if is_bull else '#ff6b9d'};
            border-bottom:8px solid #000814">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td style="width:90px;vertical-align:middle;text-align:center">{ring}</td>
                <td style="padding-left:14px;vertical-align:middle">
                  <div style="font-size:11px;font-weight:800;color:#80deea;
                    text-transform:uppercase;letter-spacing:1px;margin-bottom:4px">
                    {icon} {sn}</div>
                  <div style="display:inline-block;padding:3px 12px;border-radius:20px;
                    background:{badge_bg};color:{badge_col};font-size:10px;
                    font-weight:800;margin-bottom:8px">{badge_txt}</div>
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding-right:20px">
                        <div style="font-size:9px;color:#2a5070;text-transform:uppercase">Slope</div>
                        <div style="color:{sl_col};font-weight:700;font-size:13px;
                          font-family:'Courier New',monospace">
                          {idx['rsi_slope']:+.1f} {'↑' if idx['rsi_slope']>0 else '↓'}</div>
                      </td>
                      <td style="padding-right:20px">
                        <div style="font-size:9px;color:#2a5070;text-transform:uppercase">Week</div>
                        <div style="color:{wk_col};font-weight:700;font-size:13px;
                          font-family:'Courier New',monospace">{idx['week_chg_pct']:+.2f}%</div>
                      </td>
                      <td style="padding-right:20px">
                        <div style="font-size:9px;color:#2a5070;text-transform:uppercase">Danger</div>
                        <div style="color:{dn_col};font-weight:700;font-size:13px;
                          font-family:'Courier New',monospace">{idx['danger_score']}/6</div>
                      </td>
                      <td>
                        <div style="font-size:9px;color:#2a5070;text-transform:uppercase">Key Signal</div>
                        <div style="color:#80deea;font-size:11px">{'✅ ' if idx['rev_confirms'] else ''}{rev_short}</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr><td style="height:6px"></td></tr>"""

    # ── Top picks table ────────────────────────────────────────
    pick_rows = ""
    for i, s in enumerate(top_picks[:10], 1):
        dc  = "#00ff95" if s['day_chg_pct']  > 0 else "#ff6b9d"
        wc  = "#00ff95" if s['week_chg_pct'] > 0 else "#ff6b9d"
        rc  = "#ff6b9d" if s['rsi'] < 30 else ("#ffa502" if s['rsi'] < 50 else "#00ff95")
        sc  = "#00ff95" if s['score'] >= 60 else ("#ffa502" if s['score'] >= 40 else "#888")
        rr  = s['risk_reward']
        rrc = "#00ff95" if rr >= 2 else ("#ffa502" if rr >= 1 else "#ff6b9d")
        vmap = {
            'VALID':        ('#00ff95','#000','✅ VALID'),
            'STRONG WATCH': ('#00d9ff','#000','🔥 STRONG'),
            'CAUTION':      ('#ffa502','#000','⚠ CAUTION'),
        }
        vbg, vfg, vlbl = vmap.get(s['verdict'], ('#555','#fff', s['verdict']))
        row_bg = "#031420" if i % 2 == 0 else "#020e18"
        pick_rows += f"""
        <tr style="background:{row_bg}">
          <td style="padding:8px 6px;color:#2a5070;font-weight:700;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">{i}</td>
          <td style="padding:8px 6px;border-bottom:1px solid #0a1f35">
            <div style="font-weight:800;color:#e0f2f1;font-size:12px">{s['symbol']}</div>
            <div style="font-size:10px;color:#4a7a78">{s.get('sector','')}</div>
          </td>
          <td style="padding:8px 6px;color:#f59e0b;font-weight:700;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">₹{s['ltp']:.2f}</td>
          <td style="padding:8px 6px;color:{dc};font-weight:600;
            border-bottom:1px solid #0a1f35">{s['day_chg_pct']:+.2f}%</td>
          <td style="padding:8px 6px;color:{wc};font-weight:600;
            border-bottom:1px solid #0a1f35">{s['week_chg_pct']:+.2f}%</td>
          <td style="padding:8px 6px;border-bottom:1px solid #0a1f35">
            <span style="color:{rc};font-weight:800;font-family:'Courier New',monospace">{s['rsi']:.1f}</span>
          </td>
          <td style="padding:8px 6px;color:{sc};font-weight:800;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">{s['score']}/100</td>
          <td style="padding:8px 6px;color:#00ff95;font-weight:700;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">₹{s['target_1']:.2f}</td>
          <td style="padding:8px 6px;color:#ff6b9d;font-weight:700;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">₹{s['stop_loss']:.2f}</td>
          <td style="padding:8px 6px;color:{rrc};font-weight:800;
            font-family:'Courier New',monospace;border-bottom:1px solid #0a1f35">{rr:.1f}×</td>
          <td style="padding:8px 6px;border-bottom:1px solid #0a1f35">
            <span style="background:{vbg};color:{vfg};padding:3px 8px;border-radius:4px;
              font-size:10px;font-weight:800;white-space:nowrap">{vlbl}</span>
          </td>
        </tr>"""

    def th(txt):
        return f'<th style="padding:10px 6px;text-align:left;color:#00d9ff;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;background:#001328;white-space:nowrap">{txt}</th>'

    email_html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Nifty Sector Scanner</title></head>
<body style="margin:0;padding:0;background-color:#000814;font-family:Arial,sans-serif;color:#cfd8dc">

<table width="100%" cellpadding="0" cellspacing="0" style="background:#000814;min-height:100vh">
<tr><td align="center" style="padding:20px">

<table width="700" cellpadding="0" cellspacing="0" style="max-width:700px;width:100%;
  background:#000814;border-radius:12px;overflow:hidden;
  border:1px solid rgba(0,217,255,.2);
  box-shadow:0 0 40px rgba(0,217,255,.15)">

  <!-- HEADER -->
  <tr>
    <td style="background:linear-gradient(135deg,#001328,#003d7a);
      padding:24px 28px;border-bottom:2px solid #00d9ff">
      <div style="font-size:22px;font-weight:800;color:#00d9ff;margin-bottom:4px">
        🎯 Nifty Sector Scanner
      </div>
      <div style="font-size:12px;color:#80deea;line-height:1.5">
        Falling-Knife Filter · 6-Point Danger Check · Reversal Confirmation<br>
        <span style="color:#4a9a78">{ist_time}</span>
      </div>
    </td>
  </tr>

  <!-- BODY -->
  <tr><td style="padding:24px 28px;background:#000814">

    <!-- SUMMARY STATS -->
    {stats_row}

    <!-- SECTOR SCORECARD -->
    <div style="font-size:14px;font-weight:800;color:#00d9ff;
      padding:10px 14px;border-left:4px solid #00d9ff;
      background:rgba(0,217,255,.06);border-radius:4px;margin-bottom:16px">
      🏆 Sector Scorecard
    </div>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px">
      {sector_rows}
    </table>

    <!-- TOP PICKS TABLE -->
    <div style="font-size:14px;font-weight:800;color:#00d9ff;
      padding:10px 14px;border-left:4px solid #00ff95;
      background:rgba(0,255,149,.05);border-radius:4px;margin-bottom:16px">
      🟢 Top Valid Buys — Knife-Filtered
    </div>
    <div style="overflow-x:auto;border-radius:8px;
      border:1px solid rgba(0,217,255,.15);margin-bottom:28px">
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;min-width:600px">
        <thead>
          <tr>
            {th('#')}{th('Stock')}{th('LTP')}{th('Day%')}{th('Week%')}
            {th('RSI')}{th('Score')}{th('Target')}{th('Stop')}{th('R:R')}{th('Verdict')}
          </tr>
        </thead>
        <tbody>
          {pick_rows if pick_rows else
            '<tr><td colspan="11" style="text-align:center;color:#2a5070;padding:20px;background:#020e18">No valid buys this session.</td></tr>'}
        </tbody>
      </table>
    </div>

    <!-- DISCLAIMER -->
    <div style="background:rgba(255,107,157,.08);border-left:3px solid #ff6b9d;
      border-radius:6px;padding:14px 16px;font-size:11px;color:#ffb3d9;line-height:1.6">
      <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational
      purposes only. Past performance does not guarantee future results. Falling-knife filters
      reduce but do not eliminate loss risk. Always use strict stop losses and consult a
      SEBI-registered financial advisor before making any investment decision.
    </div>

  </td></tr>

  <!-- FOOTER -->
  <tr>
    <td style="background:#001328;padding:16px 28px;text-align:center;
      border-top:1px solid rgba(0,217,255,.1);
      font-size:11px;color:#4a7a78">
      © 2026 Nifty Sector Scanner · Falling-Knife Filter Edition · For Educational Purposes Only
    </td>
  </tr>

</table>
</td></tr>
</table>
</body></html>"""
    return email_html


# =============================================================================
#  EMAIL SENDER
# =============================================================================
def send_email_report(web_html, email_html, subject):
    """Send multipart email: plain fallback + dark HTML version."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = RECEIVER_EMAIL

        plain = MIMEText("Nifty Sector Scanner report attached. Please view in an HTML-capable email client.", 'plain')
        html  = MIMEText(email_html, 'html')   # ← dark email HTML, not the web HTML

        msg.attach(plain)
        msg.attach(html)   # last part wins in email clients

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.send_message(msg)
        print(f"{GREEN}✅ Email sent to {RECEIVER_EMAIL}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ Email failed: {e}{RESET}")
        return False


# =============================================================================
#  MAIN
# =============================================================================
def main():
    print(f"{CYAN}{'='*70}{RESET}")
    print(f"{CYAN}🎯 NIFTY SECTOR SCANNER — Progress Ring UI + Knife Filter{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    ist          = pytz.timezone("Asia/Kolkata")
    now_ist      = datetime.now(ist)
    ist_time_str = now_ist.strftime("%d %b %Y %I:%M %p IST")
    print(f"{BLUE}⏰ {ist_time_str}{RESET}\n")

    sector_analysis = {}
    bullish_sectors = []

    for sector_name, config in sectors_config.items():
        print(f"{YELLOW}📊 Scanning {sector_name}...{RESET}")

        idx_data = fetch_and_analyze(config['ticker'])
        if not idx_data:
            print(f"{RED}   ❌ No index data{RESET}")
            continue

        is_bull, reasons = is_sector_bullish(idx_data)
        strength_score   = max(0, 50 - idx_data['danger_score'] * 8 + idx_data['rev_count'] * 10)

        rsi_dir_label = idx_data.get('rsi_direction', 'Flat')
        if is_bull:
            bullish_sectors.append(sector_name)
            print(f"{GREEN}   ✅ BULLISH  RSI:{idx_data['rsi']:.1f} ({rsi_dir_label})  "
                  f"Slope:{idx_data['rsi_slope']:+.1f}  "
                  f"Danger:{idx_data['danger_score']}/6{RESET}")
        else:
            print(f"{RED}   🚫 BLOCKED  RSI:{idx_data['rsi']:.1f} ({rsi_dir_label})  "
                  f"Slope:{idx_data['rsi_slope']:+.1f}  "
                  f"Danger:{idx_data['danger_score']}/6{RESET}")
            for r in reasons:
                print(f"       {r}")

        stocks_data = []
        for ticker, info in config['stocks'].items():
            sd = fetch_and_analyze(ticker)
            if sd:
                sd['symbol']   = ticker.replace('.NS', '')
                sd['weight']   = info['weight']
                sd['industry'] = info['industry']
                stocks_data.append(sd)

        sector_analysis[sector_name] = {
            'index_data':     idx_data,
            'strength_score': strength_score,
            'is_bullish':     is_bull,
            'sector_reasons': reasons,
            'stocks':         stocks_data,
        }

    # ── Summary ───────────────────────────────────────────────
    all_valid   = [st for sn in bullish_sectors
                   for st in sector_analysis[sn]['stocks']
                   if st['verdict'] in ('VALID', 'STRONG WATCH')]
    all_avoided = [st for sn_data in sector_analysis.values()
                   for st in sn_data['stocks'] if st['verdict'] == 'AVOID']
    top_picks   = sorted(all_valid, key=lambda x: x['score'], reverse=True)[:10]

    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{GREEN}✅ Done!  Bullish sectors: {len(bullish_sectors)}{RESET}")
    for s in bullish_sectors:
        print(f"{GREEN}   • {s}{RESET}")
    print(f"\n{MAGENTA}🔥 Top Valid Picks:{RESET}")
    for i, p in enumerate(top_picks[:5], 1):
        veto_tag = f"  {RED}🚫Veto:{p['veto_signals']}/6{RESET}" if p.get('trend_veto_fired') else ""
        rsi_dir  = p.get('rsi_direction', 'Flat')
        print(f"{YELLOW}   {i}. {p['symbol']}  Score:{p['score']}/100  "
              f"RSI:{p['rsi']:.1f}({rsi_dir})  "
              f"Danger:{p['danger_score']}/6  Verdict:{p['verdict']}{veto_tag}{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")

    # ── Save web HTML ──────────────────────────────────────────
    web_html = generate_html(sector_analysis, bullish_sectors, ist_time_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(web_html)
    print(f"{GREEN}✅ index.html saved{RESET}")

    # ── Send dark-themed email ─────────────────────────────────
    if GMAIL_USER and GMAIL_APP_PASS:
        email_html = generate_email_html(
            sector_analysis, bullish_sectors, ist_time_str, top_picks, all_avoided
        )
        top_sym = top_picks[0]['symbol'] if top_picks else 'None'
        subject = f"🎯 {len(bullish_sectors)} Bullish | Top: {top_sym} | {ist_time_str}"
        send_email_report(web_html, email_html, subject)

    print(f"\n{CYAN}{'='*70}{RESET}")
    print(f"{GREEN}🎯 Report Complete — index.html ready{RESET}")
    print(f"{CYAN}{'='*70}{RESET}\n")


if __name__ == "__main__":
    main()
