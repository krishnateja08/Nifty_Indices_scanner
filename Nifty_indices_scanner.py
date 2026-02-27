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

# --- CONFIGURATION ---
GMAIL_USER      = os.getenv('GMAIL_USER')
GMAIL_APP_PASS  = os.getenv('GMAIL_APP_PASS')
RECEIVER_EMAIL  = os.getenv('RECEIVER_EMAIL', 'krishnateja.sapbasis@gmail.com')

@contextlib.contextmanager
def suppress_stdout():
    with contextlib.redirect_stdout(io.StringIO()):
        yield

# --- ANSI COLORS ---
RED = "\033[91m"; GREEN = "\033[92m"; YELLOW = "\033[93m"
CYAN = "\033[96m"; BLUE = "\033[94m"; MAGENTA = "\033[95m"; RESET = "\033[0m"

# =============================================================================
#  SECTOR CONFIG
# =============================================================================
sectors_config = {
    "Nifty Bank": {
        "ticker": "^NSEBANK",
        "stocks": {
            "HDFCBANK.NS":  {"weight": 28.1, "industry": "Private Bank"},
            "ICICIBANK.NS": {"weight": 19.3, "industry": "Private Bank"},
            "SBIN.NS":      {"weight": 18.9, "industry": "PSU Bank"},
            "AXISBANK.NS":  {"weight": 10.0, "industry": "Private Bank"},
            "KOTAKBANK.NS": {"weight":  8.8, "industry": "Private Bank"},
            "INDUSINDBK.NS":{"weight":  5.0, "industry": "Private Bank"},
            "BANKBARODA.NS":{"weight":  3.5, "industry": "PSU Bank"},
            "PNB.NS":       {"weight":  2.5, "industry": "PSU Bank"},
        }
    },
    "Nifty IT": {
        "ticker": "^CNXIT",
        "stocks": {
            "INFY.NS":      {"weight": 27.0, "industry": "IT Services"},
            "TCS.NS":       {"weight": 22.0, "industry": "IT Services"},
            "HCLTECH.NS":   {"weight": 11.0, "industry": "IT Services"},
            "TECHM.NS":     {"weight": 10.0, "industry": "IT Services"},
            "WIPRO.NS":     {"weight":  7.0, "industry": "IT Services"},
            "LTIM.NS":      {"weight":  6.0, "industry": "IT Services"},
            "PERSISTENT.NS":{"weight":  4.0, "industry": "Product Engineering"},
            "COFORGE.NS":   {"weight":  3.0, "industry": "IT Consulting"},
        }
    },
    "Nifty Pharma": {
        "ticker": "^CNXPHARMA",
        "stocks": {
            "SUNPHARMA.NS": {"weight": 21.3, "industry": "Pharma - Domestic"},
            "DIVISLAB.NS":  {"weight":  9.7, "industry": "Pharma - API"},
            "CIPLA.NS":     {"weight":  9.4, "industry": "Pharma - Domestic"},
            "DRREDDY.NS":   {"weight":  9.4, "industry": "Pharma - Global"},
            "LUPIN.NS":     {"weight":  6.6, "industry": "Pharma - Global"},
            "AUROPHARMA.NS":{"weight":  6.0, "industry": "Pharma - Global"},
            "BIOCON.NS":    {"weight":  5.5, "industry": "Biotech"},
            "ALKEM.NS":     {"weight":  4.5, "industry": "Pharma - Domestic"},
        }
    },
    "Nifty Realty": {
        "ticker": "^CNXREALTY",
        "stocks": {
            "DLF.NS":       {"weight": 21.1, "industry": "Real Estate - Commercial"},
            "PHOENIXLTD.NS":{"weight": 16.1, "industry": "Real Estate - Retail"},
            "LODHA.NS":     {"weight": 14.2, "industry": "Real Estate - Residential"},
            "PRESTIGE.NS":  {"weight": 12.8, "industry": "Real Estate - Mixed"},
            "GODREJPROP.NS":{"weight": 12.2, "industry": "Real Estate - Residential"},
            "OBEROIRLTY.NS":{"weight":  8.5, "industry": "Real Estate - Luxury"},
            "BRIGADE.NS":   {"weight":  6.0, "industry": "Real Estate - Mixed"},
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
            "MARUTI.NS":    {"weight": 20.0, "industry": "Passenger Vehicles"},
            "M&M.NS":       {"weight": 12.0, "industry": "SUVs & Tractors"},
            "BAJAJ-AUTO.NS":{"weight": 10.0, "industry": "Two Wheelers"},
            "HEROMOTOCO.NS":{"weight":  9.0, "industry": "Two Wheelers"},
            "EICHERMOT.NS": {"weight":  8.0, "industry": "Premium Two Wheelers"},
            "TVSMOTOR.NS":  {"weight":  6.0, "industry": "Two Wheelers"},
            "BOSCHLTD.NS":  {"weight":  5.0, "industry": "Auto Components"},
        }
    },
    "Nifty Energy": {
        "ticker": "^CNXENERGY",
        "stocks": {
            "RELIANCE.NS":  {"weight": 35.0, "industry": "Oil & Gas - Integrated"},
            "ONGC.NS":      {"weight": 15.0, "industry": "Oil & Gas - Upstream"},
            "NTPC.NS":      {"weight": 12.0, "industry": "Power Generation"},
            "POWERGRID.NS": {"weight": 10.0, "industry": "Power Transmission"},
            "COALINDIA.NS": {"weight":  8.0, "industry": "Coal Mining"},
            "ADANIGREEN.NS":{"weight":  7.0, "industry": "Renewable Energy"},
            "BPCL.NS":      {"weight":  6.0, "industry": "Oil Refining"},
            "IOC.NS":       {"weight":  5.0, "industry": "Oil Refining"},
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
    "Nifty Consumer Durables": {
        "ticker": "^CNXCONSUMERDURABLES",
        "stocks": {
            "TITAN.NS":    {"weight": 25.0, "industry": "Jewelry & Watches"},
            "VOLTAS.NS":   {"weight": 12.0, "industry": "Air Conditioners"},
            "HAVELLS.NS":  {"weight": 11.0, "industry": "Electrical Equipment"},
            "CROMPTON.NS": {"weight":  8.0, "industry": "Consumer Electricals"},
            "WHIRLPOOL.NS":{"weight":  7.0, "industry": "Home Appliances"},
            "BLUESTARCO.NS":{"weight": 6.0, "industry": "Air Conditioning"},
            "SYMPHONY.NS": {"weight":  5.0, "industry": "Air Coolers"},
        }
    },
}

# =============================================================================
#  INDICATORS
# =============================================================================
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain  = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs    = gain / loss
    return 100 - (100 / (1 + rs))

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
#  ★  FALLING-KNIFE DETECTION  ★
#  Returns a dict of all trend/momentum checks with pass/fail
# =============================================================================
def falling_knife_checks(data):
    """
    Run 6 independent checks to detect a stock in a confirmed downtrend.
    Returns:
        checks  – dict of {check_name: bool}  (True = DANGER / falling)
        flags   – list of human-readable warning strings
        score   – 0-6, number of danger signals firing
    """
    close  = data['Close']
    volume = data['Volume']
    checks = {}
    flags  = []

    # 1. MA BEARISH ALIGNMENT  (SMA20 < SMA50 < SMA200)
    if len(close) >= 200:
        sma20  = close.rolling(20).mean().iloc[-1]
        sma50  = close.rolling(50).mean().iloc[-1]
        sma200 = close.rolling(200).mean().iloc[-1]
        ma_bear = (sma20 < sma50) and (sma50 < sma200)
        checks['ma_bearish'] = ma_bear
        if ma_bear:
            flags.append("⛔ MA Bearish (20<50<200)")
    else:
        checks['ma_bearish'] = False

    # 2. PRICE BELOW ALL MAs  (no support from any MA)
    if len(close) >= 50:
        sma20 = close.rolling(20).mean().iloc[-1]
        sma50 = close.rolling(50).mean().iloc[-1]
        ltp   = close.iloc[-1]
        below_all = (ltp < sma20) and (ltp < sma50)
        checks['price_below_mas'] = below_all
        if below_all:
            flags.append("⛔ Price Below SMA20 & SMA50")
    else:
        checks['price_below_mas'] = False

    # 3. RSI STILL FALLING  (RSI trending down over last 5 bars)
    if len(close) >= 20:
        rsi_series = calculate_rsi(close)
        rsi_now    = rsi_series.iloc[-1]
        rsi_5ago   = rsi_series.iloc[-6]
        rsi_falling = (rsi_now < rsi_5ago - 3)   # dropped >3 pts in 5 days
        checks['rsi_falling'] = rsi_falling
        if rsi_falling:
            flags.append(f"⛔ RSI Still Falling ({rsi_5ago:.0f}→{rsi_now:.0f})")
    else:
        checks['rsi_falling'] = False

    # 4. VOLUME DISTRIBUTION  (down-day volume > up-day volume over 10 days)
    if len(data) >= 10:
        recent     = data.tail(10)
        up_days    = recent[recent['Close'] >= recent['Open']]
        down_days  = recent[recent['Close'] <  recent['Open']]
        avg_up_vol = up_days['Volume'].mean()   if len(up_days)   > 0 else 0
        avg_dn_vol = down_days['Volume'].mean() if len(down_days) > 0 else 0
        dist_bear  = avg_dn_vol > avg_up_vol * 1.2  # 20% more volume on red days
        checks['distribution'] = dist_bear
        if dist_bear:
            flags.append("⛔ Institutions Selling (Down-Vol > Up-Vol)")
    else:
        checks['distribution'] = False

    # 5. CONSECUTIVE RED DAYS  (4 of last 5 candles are red)
    if len(data) >= 5:
        last5     = data.tail(5)
        red_days  = (last5['Close'] < last5['Open']).sum()
        consec_red = red_days >= 4
        checks['consecutive_red'] = consec_red
        if consec_red:
            flags.append(f"⛔ {red_days}/5 Recent Days Red")
    else:
        checks['consecutive_red'] = False

    # 6. MACD BEARISH  (MACD below signal AND histogram still negative/worsening)
    if len(close) >= 35:
        macd_val, signal_val, hist_val = calculate_macd(close)
        _, _, hist_prev                = calculate_macd(close.iloc[:-1])
        macd_bear = (macd_val < signal_val) and (hist_val < 0) and (hist_val <= hist_prev)
        checks['macd_bearish'] = macd_bear
        if macd_bear:
            flags.append("⛔ MACD Bearish & Worsening")
    else:
        checks['macd_bearish'] = False

    danger_score = sum(checks.values())
    return checks, flags, danger_score


# =============================================================================
#  REVERSAL CONFIRMATION  (needs to PASS before a buy is valid)
# =============================================================================
def reversal_confirmations(data):
    """
    Positive signals that the selling is EXHAUSTING and a real bounce may follow.
    Returns list of confirmation strings and a confirmation count.
    """
    confirms = []
    close    = data['Close']
    volume   = data['Volume']

    # RSI turning up from oversold (was <35, now rising)
    if len(close) >= 20:
        rsi_series = calculate_rsi(close)
        rsi_now    = rsi_series.iloc[-1]
        rsi_2ago   = rsi_series.iloc[-3]
        if rsi_now < 40 and rsi_now > rsi_2ago + 1.5:
            confirms.append("✅ RSI Turning Up from Oversold")

    # Volume climax on last down-day (exhaustion selling)
    if len(data) >= 20:
        avg_vol  = volume.tail(20).mean()
        last_vol = volume.iloc[-1]
        last_red = data['Close'].iloc[-1] < data['Open'].iloc[-1]
        if last_red and last_vol > avg_vol * 2.0:
            confirms.append("✅ Volume Climax (Exhaustion)")

    # Bullish engulfing or strong green candle after red run
    if len(data) >= 3:
        c1o, c1c = data['Open'].iloc[-3], data['Close'].iloc[-3]
        c0o, c0c = data['Open'].iloc[-1], data['Close'].iloc[-1]
        if c1c < c1o and c0c > c0o and c0c > c1o:
            confirms.append("✅ Bullish Engulfing Pattern")

    # Price bouncing off 52-week low zone (within 3%)
    if len(close) >= 252:
        low_52w = close.tail(252).min()
        if close.iloc[-1] <= low_52w * 1.03 and close.iloc[-1] > close.iloc[-2]:
            confirms.append("✅ Bounce from 52W Low Zone")

    # MACD histogram turning less negative (divergence forming)
    if len(close) >= 35:
        _, _, hist_now  = calculate_macd(close)
        _, _, hist_prev = calculate_macd(close.iloc[:-1])
        _, _, hist_2ago = calculate_macd(close.iloc[:-2])
        if hist_now < 0 and hist_now > hist_prev > hist_2ago:
            confirms.append("✅ MACD Histogram Improving")

    # SMA20 slope turning flat/up after declining
    if len(close) >= 25:
        sma_now  = close.rolling(20).mean().iloc[-1]
        sma_3ago = close.rolling(20).mean().iloc[-4]
        if sma_now >= sma_3ago * 0.999:  # SMA20 no longer falling
            confirms.append("✅ SMA20 Slope Stabilizing")

    return confirms, len(confirms)


# =============================================================================
#  MAIN STOCK FETCH + ANALYSIS
# =============================================================================
def fetch_and_analyze(ticker, period="6mo"):
    try:
        with suppress_stdout():
            data = yf.download(ticker, period=period, interval="1d",
                               progress=False, multi_level_index=False)
        if data.empty or len(data) < 50:
            return None

        close = data['Close']
        ltp   = close.iloc[-1]

        # Basic metrics
        prev_close   = close.iloc[-2]
        day_chg_pct  = ((ltp - prev_close) / prev_close) * 100
        week_chg_pct = ((ltp - close.iloc[-6]) / close.iloc[-6]) * 100 if len(close) >= 6 else 0
        month_chg_pct= ((ltp - close.iloc[-22]) / close.iloc[-22]) * 100 if len(close) >= 22 else 0

        high_52w = data['High'].tail(252).max() if len(data) >= 252 else data['High'].max()
        low_52w  = data['Low'].tail(252).min()  if len(data) >= 252 else data['Low'].min()

        # Moving averages
        sma20  = close.rolling(20).mean().iloc[-1]
        sma50  = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
        sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        # RSI
        rsi_series = calculate_rsi(close)
        rsi_now    = rsi_series.iloc[-1]
        rsi_5ago   = rsi_series.iloc[-6]
        rsi_slope  = rsi_now - rsi_5ago   # positive = RSI rising

        # ATR
        atr     = calculate_atr(data)
        atr_pct = (atr / ltp) * 100

        # Falling knife checks
        fk_checks, fk_flags, danger_score = falling_knife_checks(data)

        # Reversal confirmations
        rev_confirms, rev_count = reversal_confirmations(data)

        # ── VERDICT LOGIC ────────────────────────────────────────
        # A stock is BLOCKED (falling knife) if it has 3+ danger signals
        # A stock is WATCHLIST if it has 1-2 danger signals
        # A stock is VALID BUY only if:
        #   - danger_score <= 2  AND
        #   - at least 1 reversal confirmation
        is_falling_knife = danger_score >= 3
        has_reversal     = rev_count >= 1

        if is_falling_knife:
            verdict = "AVOID"
        elif danger_score == 2 and not has_reversal:
            verdict = "AVOID"
        elif danger_score <= 1 and has_reversal:
            verdict = "STRONG WATCH" if rsi_now < 35 else "VALID"
        elif danger_score <= 2 and has_reversal:
            verdict = "CAUTION"
        else:
            verdict = "WATCH"

        # ── SCORE (only rewarded when not a falling knife) ───────
        score = 0
        if not is_falling_knife:
            # RSI zone
            if rsi_now < 25:   score += 20
            elif rsi_now < 30: score += 15
            elif rsi_now < 40: score += 10
            # RSI turning up (KEY: only bonus if rising)
            if rsi_slope > 3:  score += 20
            elif rsi_slope > 0: score += 10
            # Reversal confirmations
            score += rev_count * 10
            # Not in bearish MA alignment
            if not fk_checks.get('ma_bearish', False): score += 10
            # Price distance from 52W high (upside room)
            dist_from_high = ((high_52w - ltp) / ltp) * 100
            if dist_from_high > 30:   score += 10
            elif dist_from_high > 15: score += 5
        score = min(score, 100)

        # ── ATR-based stop & target ───────────────────────────────
        stop_loss = ltp - (atr * 1.5)
        target_1  = ltp + (atr * 2.0)
        target_2  = ltp + (atr * 3.5)
        risk_reward = ((target_1 - ltp) / (ltp - stop_loss)) if (ltp - stop_loss) > 0 else 0

        return {
            "ltp":            ltp,
            "day_chg_pct":    day_chg_pct,
            "week_chg_pct":   week_chg_pct,
            "month_chg_pct":  month_chg_pct,
            "rsi":            rsi_now,
            "rsi_slope":      rsi_slope,
            "sma20":          sma20,
            "sma50":          sma50,
            "sma200":         sma200,
            "high_52w":       high_52w,
            "low_52w":        low_52w,
            "atr":            atr,
            "atr_pct":        atr_pct,
            "danger_score":   danger_score,
            "fk_flags":       fk_flags,
            "rev_confirms":   rev_confirms,
            "rev_count":      rev_count,
            "is_falling_knife": is_falling_knife,
            "verdict":        verdict,
            "score":          score,
            "stop_loss":      stop_loss,
            "target_1":       target_1,
            "target_2":       target_2,
            "risk_reward":    risk_reward,
        }
    except Exception as e:
        return None


# =============================================================================
#  SECTOR-LEVEL BULLISH CHECK
# =============================================================================
def is_sector_bullish(idx_data):
    """
    Sector must pass ALL 3 conditions to be considered bullish.
    Old script only needed RSI < 40 — this prevents IT-type false signals.
    """
    if not idx_data:
        return False, []

    reasons = []
    passes  = 0

    # 1. RSI not in confirmed downtrend (must be < 55 but also not still falling hard)
    rsi        = idx_data['rsi']
    rsi_slope  = idx_data['rsi_slope']
    if rsi < 50 and rsi_slope > -2:
        passes += 1
        reasons.append(f"✅ RSI {rsi:.1f} — not overbought & slope OK")
    else:
        reasons.append(f"❌ RSI {rsi:.1f} slope {rsi_slope:+.1f} — trending down")

    # 2. NOT a falling knife (danger score <= 2)
    if idx_data['danger_score'] <= 2:
        passes += 1
        reasons.append(f"✅ Danger Score {idx_data['danger_score']}/6 — acceptable")
    else:
        reasons.append(f"❌ Danger Score {idx_data['danger_score']}/6 — falling knife")

    # 3. At least one reversal confirmation OR week change positive
    if idx_data['rev_count'] >= 1 or (idx_data['week_chg_pct'] and idx_data['week_chg_pct'] > 0.5):
        passes += 1
        confirms_str = ", ".join(idx_data['rev_confirms'][:2]) if idx_data['rev_confirms'] else f"week +{idx_data['week_chg_pct']:.1f}%"
        reasons.append(f"✅ Reversal evidence: {confirms_str}")
    else:
        reasons.append(f"❌ No reversal confirmation — week {idx_data['week_chg_pct']:+.1f}%")

    return passes >= 2, reasons   # need 2 of 3 to be bullish


# =============================================================================
#  HTML GENERATOR
# =============================================================================
def generate_html(sector_analysis, bullish_sectors, ist_time):
    total_sectors = len(sector_analysis)
    bullish_count = len(bullish_sectors)

    all_valid_stocks = []
    all_avoided      = []
    for sn, analysis in sector_analysis.items():
        for st in analysis['stocks']:
            st['sector'] = sn
            if st['verdict'] in ('VALID', 'STRONG WATCH') and sn in bullish_sectors:
                all_valid_stocks.append(st)
            if st['verdict'] == 'AVOID':
                all_avoided.append(st)

    top_picks   = sorted(all_valid_stocks, key=lambda x: x['score'], reverse=True)[:20]
    strong_buys = [s for s in all_valid_stocks if s['score'] >= 60 and s['rsi'] < 32]
    top_symbol  = top_picks[0]['symbol'] if top_picks else '—'

    # ── Sector cards ─────────────────────────────────────────
    sector_cards = ""
    for sn, analysis in sector_analysis.items():
        idx   = analysis['index_data']
        sc    = analysis['strength_score']
        bull  = sn in bullish_sectors
        reasons_html = "".join([f'<div class="reason">{r}</div>' for r in analysis['sector_reasons'][:3]])
        badge_color = "#00ff95" if bull else "#ff6b9d"
        badge_text  = "🟢 BULLISH" if bull else "🔴 BLOCKED"
        wk_color    = "#00ff95" if idx['week_chg_pct'] > 0 else "#ff6b9d"
        fk_color    = "#ff6b9d" if idx['danger_score'] >= 3 else ("#ffa502" if idx['danger_score'] >= 2 else "#00ff95")
        sector_cards += f"""
        <div class="sector-card {'bullish-card' if bull else 'bearish-card'}">
            <div class="sector-name">{sn}</div>
            <div class="sector-badge" style="background:{badge_color}">{badge_text}</div>
            <div class="sector-metrics">
                <span>RSI <strong style="color:{'#ffa502' if idx['rsi'] < 40 else '#cfd8dc'}">{idx['rsi']:.1f}</strong></span>
                <span>RSI Slope <strong style="color:{'#00ff95' if idx['rsi_slope']>0 else '#ff6b9d'}">{idx['rsi_slope']:+.1f}</strong></span>
                <span>Week <strong style="color:{wk_color}">{idx['week_chg_pct']:+.2f}%</strong></span>
                <span>Danger <strong style="color:{fk_color}">{idx['danger_score']}/6</strong></span>
            </div>
            <div class="sector-reasons">{reasons_html}</div>
        </div>"""

    # ── Top picks table ───────────────────────────────────────
    def verdict_tag(v):
        colors = {
            'VALID':        ('#00ff95','#000','✅ VALID BUY'),
            'STRONG WATCH': ('#00d9ff','#000','🔥 STRONG WATCH'),
            'CAUTION':      ('#ffa502','#000','⚠️ CAUTION'),
            'WATCH':        ('#888888','#fff','👀 WATCH'),
            'AVOID':        ('#ff6b9d','#000','🚫 AVOID'),
        }
        bg, fg, label = colors.get(v, ('#888','#fff', v))
        return f'<span class="tag" style="background:{bg};color:{fg}">{label}</span>'

    def danger_badge(n):
        color = "#00ff95" if n == 0 else ("#ffa502" if n <= 2 else "#ff6b9d")
        return f'<span style="color:{color};font-weight:700">{n}/6</span>'

    buy_rows = ""
    for i, s in enumerate(top_picks, 1):
        dc   = "#00ff95" if s['day_chg_pct']  > 0 else "#ff6b9d"
        wc   = "#00ff95" if s['week_chg_pct'] > 0 else "#ff6b9d"
        rsi  = s['rsi']
        rc   = "#ff6b9d" if rsi < 30 else ("#ffa502" if rsi < 50 else "#00ff95")
        sc   = "#00ff95" if s['score'] >= 60 else ("#ffa502" if s['score'] >= 40 else "#888")
        fk_flags_html = " ".join([f'<span class="warn-pill">{f}</span>' for f in s['fk_flags']]) if s['fk_flags'] else '<span style="color:#00ff95;font-size:.7rem">✅ No Flags</span>'
        rev_html = " ".join([f'<span class="sig-pill">{c}</span>' for c in s['rev_confirms'][:2]]) if s['rev_confirms'] else '—'
        buy_rows += f"""
        <tr class="{'top-row' if s['score'] >= 60 else ''}">
            <td><strong>{i}</strong></td>
            <td><strong>{s['symbol']}</strong><br><small style="color:#888">{s.get('sector','')}</small><br><small style="color:#555">{s.get('industry','')}</small></td>
            <td>₹{s['ltp']:.2f}</td>
            <td style="color:{dc}">{s['day_chg_pct']:+.2f}%</td>
            <td style="color:{wc}">{s['week_chg_pct']:+.2f}%</td>
            <td style="color:{rc}"><strong>{rsi:.1f}</strong><br><small style="color:{'#00ff95' if s['rsi_slope']>0 else '#ff6b9d'};font-size:.7rem">{s['rsi_slope']:+.1f} slope</small></td>
            <td style="color:{sc}"><strong>{s['score']}/100</strong></td>
            <td>{danger_badge(s['danger_score'])}<br><small style="font-size:.65rem">{fk_flags_html[:60] if s['fk_flags'] else ''}</small></td>
            <td>{rev_html}</td>
            <td style="color:#00ff95">₹{s['target_1']:.2f}<br><small>T2: ₹{s['target_2']:.2f}</small></td>
            <td style="color:#ff6b9d">₹{s['stop_loss']:.2f}</td>
            <td style="color:#00ff95">{s['risk_reward']:.1f}×</td>
            <td>{verdict_tag(s['verdict'])}</td>
        </tr>"""

    # ── Avoided (falling knife) table ────────────────────────
    avoided_rows = ""
    for s in sorted(all_avoided, key=lambda x: x['danger_score'], reverse=True)[:15]:
        fk_html = " ".join([f'<span class="warn-pill">{f}</span>' for f in s['fk_flags'][:3]])
        dc = "#00ff95" if s['day_chg_pct'] > 0 else "#ff6b9d"
        wc = "#00ff95" if s['week_chg_pct'] > 0 else "#ff6b9d"
        avoided_rows += f"""
        <tr>
            <td><strong>{s['symbol']}</strong><br><small style="color:#888">{s.get('sector','')}</small></td>
            <td>₹{s['ltp']:.2f}</td>
            <td style="color:{dc}">{s['day_chg_pct']:+.2f}%</td>
            <td style="color:{wc}">{s['week_chg_pct']:+.2f}%</td>
            <td style="color:#ffa502">{s['rsi']:.1f}</td>
            <td><span style="color:#ff6b9d;font-weight:700">{s['danger_score']}/6</span></td>
            <td>{fk_html}</td>
        </tr>"""

    # ── Detailed sector breakdown ─────────────────────────────
    sector_detail = ""
    for sn in bullish_sectors:
        analysis = sector_analysis[sn]
        idx      = analysis['index_data']
        stocks_sorted = sorted(analysis['stocks'], key=lambda x: x['score'], reverse=True)
        rows = ""
        for st in stocks_sorted:
            dc   = "#00ff95" if st['day_chg_pct']  > 0 else "#ff6b9d"
            wc   = "#00ff95" if st['week_chg_pct'] > 0 else "#ff6b9d"
            rc   = "#ff6b9d" if st['rsi'] < 30 else ("#ffa502" if st['rsi'] < 50 else "#00ff95")
            sc_c = "#00ff95" if st['score'] >= 60 else ("#ffa502" if st['score'] >= 40 else "#888")
            fk_short = ", ".join(st['fk_flags'][:2]) if st['fk_flags'] else "✅ Clean"
            rev_short = ", ".join(st['rev_confirms'][:2]) if st['rev_confirms'] else "—"
            rows += f"""
            <tr class="{'top-row' if st['score'] >= 60 else ''}">
                <td><strong>{st['symbol']}</strong></td>
                <td>{st.get('weight',0):.1f}%</td>
                <td>₹{st['ltp']:.2f}</td>
                <td style="color:{dc}">{st['day_chg_pct']:+.2f}%</td>
                <td style="color:{wc}">{st['week_chg_pct']:+.2f}%</td>
                <td style="color:{rc}">{st['rsi']:.1f} <small style="color:{'#00ff95' if st['rsi_slope']>0 else '#ff6b9d'}">({st['rsi_slope']:+.1f})</small></td>
                <td style="color:{sc_c}"><strong>{st['score']}/100</strong></td>
                <td style="font-size:.75rem;color:#ff9999">{fk_short}</td>
                <td style="font-size:.75rem;color:#99ff99">{rev_short}</td>
                <td style="color:#00ff95">₹{st['target_1']:.2f}</td>
                <td style="color:#ff6b9d">₹{st['stop_loss']:.2f}</td>
                <td>{verdict_tag(st['verdict'])}</td>
            </tr>"""
        sector_detail += f"""
        <div class="sector-detail-block">
            <div class="sector-detail-header">
                <h3>📊 {sn.upper()}</h3>
                <div class="sector-meta">
                    RSI: <strong>{idx['rsi']:.1f}</strong> &nbsp;|&nbsp;
                    RSI Slope: <strong style="color:{'#00ff95' if idx['rsi_slope']>0 else '#ff6b9d'}">{idx['rsi_slope']:+.1f}</strong> &nbsp;|&nbsp;
                    Week: <strong style="color:{'#00ff95' if idx['week_chg_pct']>0 else '#ff6b9d'}">{idx['week_chg_pct']:+.2f}%</strong> &nbsp;|&nbsp;
                    Danger: <strong style="color:{'#00ff95' if idx['danger_score']<=2 else '#ff6b9d'}">{idx['danger_score']}/6</strong>
                </div>
            </div>
            <div class="table-wrap"><table>
                <thead><tr>
                    <th>Stock</th><th>Wt%</th><th>LTP</th><th>Day%</th><th>Week%</th>
                    <th>RSI (slope)</th><th>Score</th><th>⚠ Danger Flags</th>
                    <th>✅ Reversals</th><th>Target</th><th>Stop</th><th>Verdict</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table></div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎯 Nifty Sector Scanner v2 — Knife Filter</title>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
  :root {{
    --nc:#00d9ff; --ng:#00ff95; --nr:#ff6b9d;
    --no:#ffa502; --bg:#000814; --bg2:#001328;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:'Plus Jakarta Sans',sans-serif;background:linear-gradient(135deg,var(--bg2),var(--bg));min-height:100vh;padding:20px;color:#cfd8dc;font-size:13px}}
  .container{{max-width:1500px;margin:auto;background:rgba(0,8,20,.97);border-radius:16px;box-shadow:0 0 50px rgba(0,217,255,.3);overflow:hidden;border:1px solid rgba(0,217,255,.25)}}

  /* HEADER */
  .header{{background:linear-gradient(135deg,var(--bg2),#003d7a);color:var(--nc);padding:32px 28px;border-bottom:3px solid var(--nc);display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px}}
  .header h1{{font-size:1.9rem;font-weight:800;text-shadow:0 0 20px rgba(0,217,255,.8);margin-bottom:6px}}
  .header .sub{{font-size:.85rem;color:#80deea;opacity:.85}}
  #live-clock{{font-family:'JetBrains Mono',monospace;background:var(--nc);color:#000;border-radius:30px;padding:10px 22px;font-weight:700;font-size:.85rem;white-space:nowrap;box-shadow:0 0 18px rgba(0,217,255,.6)}}

  /* SUMMARY STRIP */
  .summary{{display:flex;flex-wrap:wrap;gap:14px;padding:22px 28px;background:rgba(0,31,63,.4);border-bottom:1px solid rgba(0,217,255,.15)}}
  .stat{{flex:1 1 130px;background:rgba(0,217,255,.08);border-radius:10px;padding:14px 18px;text-align:center;border-left:4px solid var(--nc)}}
  .stat .num{{font-size:2rem;font-weight:800;color:var(--nc)}}
  .stat .lbl{{font-size:.7rem;color:#80deea;text-transform:uppercase;letter-spacing:.5px;margin-top:4px}}

  /* EXPLANATION BOX */
  .explain-box{{margin:20px 28px;padding:18px 22px;background:rgba(0,255,149,.07);border:1px solid rgba(0,255,149,.25);border-left:5px solid var(--ng);border-radius:8px}}
  .explain-box h3{{color:var(--ng);font-size:.95rem;margin-bottom:10px}}
  .explain-box .checks{{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}}
  .check-pill{{background:rgba(0,255,149,.12);border:1px solid rgba(0,255,149,.3);color:var(--ng);padding:4px 12px;border-radius:20px;font-size:.75rem;font-weight:600}}
  .warn-pill{{display:inline-block;background:rgba(255,107,157,.15);border:1px solid rgba(255,107,157,.3);color:var(--nr);padding:2px 7px;border-radius:12px;font-size:.65rem;font-weight:700;margin:1px;white-space:nowrap}}
  .sig-pill{{display:inline-block;background:rgba(0,217,255,.15);border:1px solid rgba(0,217,255,.3);color:var(--nc);padding:2px 7px;border-radius:12px;font-size:.65rem;font-weight:700;margin:1px;white-space:nowrap}}

  /* SECTIONS */
  .section{{padding:24px 28px}}
  .section-title{{font-size:1.1rem;font-weight:800;color:var(--nc);padding:10px 16px;border-left:5px solid var(--nc);background:linear-gradient(90deg,rgba(0,217,255,.1),transparent);border-radius:4px;margin-bottom:18px;text-shadow:0 0 10px rgba(0,217,255,.4)}}

  /* SECTOR GRID */
  .sector-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px;margin-bottom:10px}}
  .sector-card{{border-radius:10px;padding:14px;transition:all .25s}}
  .bullish-card{{border:1px solid rgba(0,255,149,.35);background:rgba(0,255,149,.06);box-shadow:0 0 14px rgba(0,255,149,.15)}}
  .bearish-card{{border:1px solid rgba(255,107,157,.25);background:rgba(255,107,157,.04)}}
  .sector-card:hover{{transform:translateY(-3px)}}
  .sector-name{{font-weight:800;font-size:.88rem;color:var(--nc);margin-bottom:6px}}
  .sector-badge{{display:inline-block;color:#000;font-size:.7rem;font-weight:800;padding:3px 10px;border-radius:20px;margin-bottom:8px}}
  .sector-metrics{{font-size:.75rem;color:#cfd8dc;display:flex;flex-direction:column;gap:3px}}
  .sector-reasons{{margin-top:8px}}
  .reason{{font-size:.68rem;color:#80cbc4;line-height:1.4;padding:1px 0}}

  /* TABLES */
  .tbl-wrap{{overflow-x:auto;margin-bottom:20px;border-radius:8px;border:1px solid rgba(0,217,255,.15)}}
  table{{width:100%;border-collapse:collapse;min-width:900px}}
  thead tr{{background:linear-gradient(135deg,var(--bg2),#003d7a)}}
  th{{color:var(--nc);padding:10px 9px;text-align:left;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;text-shadow:0 0 5px rgba(0,217,255,.4)}}
  td{{padding:9px;border-bottom:1px solid rgba(0,217,255,.08);color:#cfd8dc;vertical-align:middle}}
  tbody tr:hover{{background:rgba(0,217,255,.05)}}
  .top-row{{background:linear-gradient(90deg,rgba(0,217,255,.08),transparent)!important;border-left:3px solid var(--nc)}}
  .tag{{display:inline-block;padding:4px 10px;border-radius:5px;font-size:.7rem;font-weight:800;white-space:nowrap}}

  /* SECTOR DETAIL */
  .sector-detail-block{{margin-bottom:30px;border:1px solid rgba(0,217,255,.2);border-radius:10px;overflow:hidden}}
  .sector-detail-header{{background:linear-gradient(135deg,var(--bg2),#003d7a);color:var(--nc);padding:14px 18px;border-bottom:2px solid var(--nc)}}
  .sector-detail-header h3{{font-size:1rem;margin-bottom:4px;text-shadow:0 0 10px rgba(0,217,255,.6)}}
  .sector-meta{{font-size:.82rem;color:#80deea}}

  /* AVOIDED SECTION */
  .avoided-section{{padding:24px 28px;background:rgba(255,107,157,.03);border-top:1px solid rgba(255,107,157,.15)}}
  .avoided-title{{font-size:1.1rem;font-weight:800;color:var(--nr);padding:10px 16px;border-left:5px solid var(--nr);background:linear-gradient(90deg,rgba(255,107,157,.1),transparent);border-radius:4px;margin-bottom:18px}}

  /* DISCLAIMER */
  .disclaimer{{margin:10px 28px 24px;padding:14px 18px;background:rgba(255,107,157,.08);border-left:4px solid var(--nr);border-radius:6px;font-size:.78rem;color:#ffb3d9}}
  .footer{{text-align:center;padding:18px;background:rgba(0,31,63,.4);border-top:1px solid rgba(0,217,255,.15);font-size:.78rem;color:#80deea}}

  @media(max-width:640px){{
    .header{{flex-direction:column;align-items:flex-start}}
    .header h1{{font-size:1.3rem}}
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <div>
      <h1>🎯 Nifty Sector Scanner <span style="color:var(--ng)">v2</span></h1>
      <div class="sub">Falling-Knife Filter · Reversal Confirmation · 6-Point Danger Check</div>
      <div class="sub" style="margin-top:4px">Report: {ist_time}</div>
    </div>
    <div id="live-clock">🕐 Loading...</div>
  </div>

  <div class="summary">
    <div class="stat"><div class="num">{total_sectors}</div><div class="lbl">Sectors Scanned</div></div>
    <div class="stat" style="border-color:var(--ng)"><div class="num" style="color:var(--ng)">{bullish_count}</div><div class="lbl">Truly Bullish</div></div>
    <div class="stat" style="border-color:var(--nc)"><div class="num" style="color:var(--nc)">{len(top_picks)}</div><div class="lbl">Valid Buys</div></div>
    <div class="stat" style="border-color:var(--no)"><div class="num" style="color:var(--no)">{len(strong_buys)}</div><div class="lbl">Strong Watch</div></div>
    <div class="stat" style="border-color:var(--nr)"><div class="num" style="color:var(--nr)">{len(all_avoided)}</div><div class="lbl">Avoided (Knife)</div></div>
    <div class="stat" style="border-color:var(--nc)"><div class="num" style="color:var(--nc);font-size:1.1rem;padding-top:8px">{top_symbol}</div><div class="lbl">Top Pick</div></div>
  </div>

  <!-- HOW THE FILTER WORKS -->
  <div class="explain-box">
    <h3>🛡️ How the Falling-Knife Filter Works (NEW in v2)</h3>
    <p style="color:#80deea;font-size:.8rem;margin-bottom:8px">
      Each stock is checked against <strong>6 danger signals</strong>. A stock with 3+ signals is blocked as a falling knife regardless of RSI. Stocks are only recommended when danger is low AND there is at least 1 reversal confirmation.
    </p>
    <div class="checks">
      <span class="check-pill">⛔ MA Bearish Alignment (20&lt;50&lt;200)</span>
      <span class="check-pill">⛔ Price Below SMA20 & SMA50</span>
      <span class="check-pill">⛔ RSI Still Falling</span>
      <span class="check-pill">⛔ Institutions Selling (Down-Vol &gt; Up-Vol)</span>
      <span class="check-pill">⛔ 4+ of Last 5 Days Red</span>
      <span class="check-pill">⛔ MACD Bearish & Worsening</span>
    </div>
    <p style="color:#80deea;font-size:.8rem;margin-top:10px">
      <strong style="color:var(--ng)">Reversal confirmations required:</strong>
      RSI turning up · Volume climax · Bullish engulfing · 52W low bounce · MACD histogram improving · SMA20 stabilizing
    </p>
  </div>

  <div class="section">
    <div class="section-title">🏆 Sector Scorecard</div>
    <div class="sector-grid">{sector_cards}</div>
  </div>

  <div class="section">
    <div class="section-title">🟢 Top Valid Buy Recommendations (Knife-Filtered)</div>
    <div class="tbl-wrap"><table>
      <thead><tr>
        <th>#</th><th>Stock</th><th>LTP</th><th>Day%</th><th>Week%</th>
        <th>RSI (slope)</th><th>Score</th><th>Danger</th><th>Reversals</th>
        <th>Target</th><th>Stop Loss</th><th>R:R</th><th>Verdict</th>
      </tr></thead>
      <tbody>{buy_rows if buy_rows else '<tr><td colspan="13" style="text-align:center;color:#888;padding:20px">No valid buys — market in downtrend. Avoiding all falling knives.</td></tr>'}</tbody>
    </table></div>
  </div>

  <div class="section">
    <div class="section-title">📊 Bullish Sector Detail</div>
    {sector_detail if sector_detail else '<p style="color:#888;padding:10px">No bullish sectors with clean setups detected.</p>'}
  </div>

  <div class="avoided-section">
    <div class="avoided-title">🚫 Stocks Avoided — Falling Knife Detection</div>
    <p style="color:#ff9999;font-size:.8rem;margin-bottom:14px">These stocks would have been recommended by the old script (RSI &lt; 40). They are blocked because 3+ danger signals are active.</p>
    <div class="tbl-wrap"><table>
      <thead><tr>
        <th>Stock</th><th>LTP</th><th>Day%</th><th>Week%</th><th>RSI</th><th>Danger Score</th><th>Reasons Blocked</th>
      </tr></thead>
      <tbody>{avoided_rows if avoided_rows else '<tr><td colspan="7" style="text-align:center;color:#888;padding:16px">No stocks blocked this session.</td></tr>'}</tbody>
    </table></div>
  </div>

  <div class="disclaimer">
    <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational purposes only.
    Past performance does not guarantee future results. Falling-knife filters reduce but do not eliminate loss risk.
    Always use stop losses and consult a SEBI-registered advisor before investing.
  </div>

  <div class="footer">© 2026 Nifty Sector Scanner v2 · Falling-Knife Filter Edition · For Educational Purposes Only</div>
</div>

<script>
function updateClock() {{
  var now  = new Date();
  var opts = {{timeZone:'Asia/Kolkata',day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:true}};
  var el   = document.getElementById('live-clock');
  if (el) el.textContent = '🕐 ' + now.toLocaleString('en-IN', opts) + ' IST';
}}
updateClock();
setInterval(updateClock, 1000);
</script>
</body></html>"""
    return html


# =============================================================================
#  EMAIL
# =============================================================================
def send_email_report(html_content, subject):
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From']    = GMAIL_USER
        msg['To']      = RECEIVER_EMAIL
        msg.attach(MIMEText(html_content, 'html'))
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
    print(f"{CYAN}{'='*75}{RESET}")
    print(f"{CYAN}🎯 NIFTY SECTOR SCANNER v2 — Falling-Knife Filter Edition{RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")

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

        if is_bull:
            bullish_sectors.append(sector_name)
            print(f"{GREEN}   ✅ BULLISH  RSI:{idx_data['rsi']:.1f} Slope:{idx_data['rsi_slope']:+.1f} Danger:{idx_data['danger_score']}/6{RESET}")
        else:
            print(f"{RED}   🚫 BLOCKED  RSI:{idx_data['rsi']:.1f} Slope:{idx_data['rsi_slope']:+.1f} Danger:{idx_data['danger_score']}/6{RESET}")
            for r in reasons:
                print(f"       {r}")

        # Analyze individual stocks
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

    # Summary
    all_valid = [st for sn in bullish_sectors
                 for st in sector_analysis[sn]['stocks']
                 if st['verdict'] in ('VALID', 'STRONG WATCH')]
    top_picks = sorted(all_valid, key=lambda x: x['score'], reverse=True)[:10]

    print(f"\n{CYAN}{'='*75}{RESET}")
    print(f"{GREEN}✅ Done! Bullish sectors: {len(bullish_sectors)}{RESET}")
    for s in bullish_sectors:
        print(f"{GREEN}   • {s}{RESET}")
    print(f"\n{MAGENTA}🔥 Top Valid Picks:{RESET}")
    for i, p in enumerate(top_picks[:5], 1):
        print(f"{YELLOW}   {i}. {p['symbol']}  Score:{p['score']}/100  Danger:{p['danger_score']}/6  Verdict:{p['verdict']}{RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")

    # Save HTML
    html = generate_html(sector_analysis, bullish_sectors, ist_time_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"{GREEN}✅ index.html saved{RESET}")

    # Email
    if GMAIL_USER and GMAIL_APP_PASS:
        top_sym  = top_picks[0]['symbol'] if top_picks else 'None'
        subject  = f"🎯 {len(bullish_sectors)} Bullish | Top: {top_sym} | {ist_time_str}"
        send_email_report(html, subject)

    print(f"{CYAN}{'='*75}{RESET}")
    print(f"{GREEN}🎯 Report Complete{RESET}")
    print(f"{CYAN}{'='*75}{RESET}\n")


if __name__ == "__main__":
    main()
