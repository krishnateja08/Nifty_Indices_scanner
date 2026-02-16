import yfinance as yf
import pandas as pd
import warnings
from tabulate import tabulate
from datetime import datetime
import pytz
import contextlib
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client
import numpy as np

warnings.filterwarnings("ignore")

# --- CONFIGURATION (Environment Variables) ---
GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_APP_PASS = os.getenv('GMAIL_APP_PASS')
RECEIVER_EMAIL = os.getenv('RECEIVER_EMAIL', 'krishnateja.sapbasis@gmail.com')
TWILIO_SID = os.getenv('TWILIO_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM', 'whatsapp:+14155238886')
TWILIO_TO = os.getenv('TWILIO_TO', 'whatsapp:+17372876924')

# --- Suppress all yfinance console output ---
@contextlib.contextmanager
def suppress_stdout():
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        yield

# --- ANSI COLORS (For Terminal) ---
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
RESET = "\033[0m"

# --- Enhanced Sector Config with Industry Classification ---
sectors_config = {
    "Nifty Bank": {
        "ticker": "^NSEBANK",
        "stocks": {
            "HDFCBANK.NS": {"weight": 28.1, "industry": "Private Bank"},
            "ICICIBANK.NS": {"weight": 19.3, "industry": "Private Bank"},
            "SBIN.NS": {"weight": 18.9, "industry": "PSU Bank"},
            "AXISBANK.NS": {"weight": 10.0, "industry": "Private Bank"},
            "KOTAKBANK.NS": {"weight": 8.8, "industry": "Private Bank"},
            "INDUSINDBK.NS": {"weight": 5.0, "industry": "Private Bank"},
            "BANKBARODA.NS": {"weight": 3.5, "industry": "PSU Bank"},
            "PNB.NS": {"weight": 2.5, "industry": "PSU Bank"}
        }
    },
    "Nifty IT": {
        "ticker": "^CNXIT",
        "stocks": {
            "INFY.NS": {"weight": 27.0, "industry": "IT Services"},
            "TCS.NS": {"weight": 22.0, "industry": "IT Services"},
            "HCLTECH.NS": {"weight": 11.0, "industry": "IT Services"},
            "TECHM.NS": {"weight": 10.0, "industry": "IT Services"},
            "WIPRO.NS": {"weight": 7.0, "industry": "IT Services"},
            "LTIM.NS": {"weight": 6.0, "industry": "IT Services"},
            "PERSISTENT.NS": {"weight": 4.0, "industry": "Product Engineering"},
            "COFORGE.NS": {"weight": 3.0, "industry": "IT Consulting"}
        }
    },
    "Nifty Private Bank": {
        "ticker": "NIFTY_PVT_BANK.NS",
        "stocks": {
            "HDFCBANK.NS": {"weight": 40.4, "industry": "Private Bank"},
            "ICICIBANK.NS": {"weight": 27.4, "industry": "Private Bank"},
            "AXISBANK.NS": {"weight": 11.6, "industry": "Private Bank"},
            "KOTAKBANK.NS": {"weight": 11.5, "industry": "Private Bank"},
            "FEDERALBNK.NS": {"weight": 5.0, "industry": "Private Bank"},
            "INDUSINDBK.NS": {"weight": 4.1, "industry": "Private Bank"}
        }
    },
    "Nifty Pharma": {
        "ticker": "^CNXPHARMA",
        "stocks": {
            "SUNPHARMA.NS": {"weight": 21.3, "industry": "Pharma - Domestic"},
            "DIVISLAB.NS": {"weight": 9.7, "industry": "Pharma - API"},
            "CIPLA.NS": {"weight": 9.4, "industry": "Pharma - Domestic"},
            "DRREDDY.NS": {"weight": 9.4, "industry": "Pharma - Global"},
            "LUPIN.NS": {"weight": 6.6, "industry": "Pharma - Global"},
            "AUROPHARMA.NS": {"weight": 6.0, "industry": "Pharma - Global"},
            "BIOCON.NS": {"weight": 5.5, "industry": "Biotech"},
            "ALKEM.NS": {"weight": 4.5, "industry": "Pharma - Domestic"}
        }
    },
    "Nifty Realty": {
        "ticker": "^CNXREALTY",
        "stocks": {
            "DLF.NS": {"weight": 21.1, "industry": "Real Estate - Commercial"},
            "PHOENIXLTD.NS": {"weight": 16.1, "industry": "Real Estate - Retail"},
            "LODHA.NS": {"weight": 14.2, "industry": "Real Estate - Residential"},
            "PRESTIGE.NS": {"weight": 12.8, "industry": "Real Estate - Mixed"},
            "GODREJPROP.NS": {"weight": 12.2, "industry": "Real Estate - Residential"},
            "OBEROIRLTY.NS": {"weight": 8.5, "industry": "Real Estate - Luxury"},
            "BRIGADE.NS": {"weight": 6.0, "industry": "Real Estate - Mixed"}
        }
    },
    "Nifty FMCG": {
        "ticker": "^CNXFMCG",
        "stocks": {
            "ITC.NS": {"weight": 33.0, "industry": "Diversified FMCG"},
            "HINDUNILVR.NS": {"weight": 18.0, "industry": "Personal Care"},
            "NESTLEIND.NS": {"weight": 8.0, "industry": "Packaged Foods"},
            "TATACONSUM.NS": {"weight": 7.0, "industry": "Beverages"},
            "BRITANNIA.NS": {"weight": 6.0, "industry": "Biscuits"},
            "DABUR.NS": {"weight": 5.5, "industry": "Ayurvedic Products"},
            "MARICO.NS": {"weight": 4.5, "industry": "Hair & Skin Care"},
            "GODREJCP.NS": {"weight": 4.0, "industry": "Home Care"}
        }
    },
    "Nifty Metal": {
        "ticker": "^CNXMETAL",
        "stocks": {
            "TATASTEEL.NS": {"weight": 17.0, "industry": "Steel"},
            "HINDALCO.NS": {"weight": 15.0, "industry": "Aluminum"},
            "JSWSTEEL.NS": {"weight": 14.0, "industry": "Steel"},
            "JINDALSTEL.NS": {"weight": 12.0, "industry": "Steel"},
            "NMDC.NS": {"weight": 8.0, "industry": "Iron Ore"},
            "VEDL.NS": {"weight": 7.5, "industry": "Diversified Metals"},
            "SAIL.NS": {"weight": 6.5, "industry": "Steel - PSU"},
            "HINDZINC.NS": {"weight": 6.0, "industry": "Zinc"}
        }
    },
    "Nifty Auto": {
        "ticker": "^CNXAUTO",
        "stocks": {
            "MARUTI.NS": {"weight": 20.0, "industry": "Passenger Vehicles"},
            "TMCV.NS": {"weight": 15.0, "industry": "Commercial Vehicles"},
            "TMPV.NS": {"weight": 15.0, "industry": "Commercial Vehicles"},
            "M&M.NS": {"weight": 12.0, "industry": "SUVs & Tractors"},
            "BAJAJ-AUTO.NS": {"weight": 10.0, "industry": "Two Wheelers"},
            "HEROMOTOCO.NS": {"weight": 9.0, "industry": "Two Wheelers"},
            "EICHERMOT.NS": {"weight": 8.0, "industry": "Premium Two Wheelers"},
            "TVSMOTOR.NS": {"weight": 6.0, "industry": "Two Wheelers"},
            "BOSCHLTD.NS": {"weight": 5.0, "industry": "Auto Components"}
        }
    },
    "Nifty Energy": {
        "ticker": "^CNXENERGY",
        "stocks": {
            "RELIANCE.NS": {"weight": 35.0, "industry": "Oil & Gas - Integrated"},
            "ONGC.NS": {"weight": 15.0, "industry": "Oil & Gas - Upstream"},
            "NTPC.NS": {"weight": 12.0, "industry": "Power Generation"},
            "POWERGRID.NS": {"weight": 10.0, "industry": "Power Transmission"},
            "COALINDIA.NS": {"weight": 8.0, "industry": "Coal Mining"},
            "ADANIGREEN.NS": {"weight": 7.0, "industry": "Renewable Energy"},
            "BPCL.NS": {"weight": 6.0, "industry": "Oil Refining"},
            "IOC.NS": {"weight": 5.0, "industry": "Oil Refining"}
        }
    },
    "Nifty Consumer Durables": {
        "ticker": "^CNXCONSUMERDURABLES",
        "stocks": {
            "TITAN.NS": {"weight": 25.0, "industry": "Jewelry & Watches"},
            "VOLTAS.NS": {"weight": 12.0, "industry": "Air Conditioners"},
            "HAVELLS.NS": {"weight": 11.0, "industry": "Electrical Equipment"},
            "CROMPTON.NS": {"weight": 8.0, "industry": "Consumer Electricals"},
            "WHIRLPOOL.NS": {"weight": 7.0, "industry": "Home Appliances"},
            "BLUESTARCO.NS": {"weight": 6.0, "industry": "Air Conditioning"},
            "SYMPHONY.NS": {"weight": 5.0, "industry": "Air Coolers"}
        }
    }
}

def calculate_rsi(series, period=14):
    """Calculate RSI indicator"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_moving_averages(data):
    """Calculate multiple moving averages"""
    return {
        'sma_20': data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else None,
        'sma_50': data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else None,
        'ema_9': data['Close'].ewm(span=9, adjust=False).mean().iloc[-1] if len(data) >= 9 else None,
        'ema_21': data['Close'].ewm(span=21, adjust=False).mean().iloc[-1] if len(data) >= 21 else None
    }

def calculate_profit_potential(ltp, high_52w, low_52w, rsi, trend):
    score = 0
    dist_from_low = ((ltp - low_52w) / low_52w) * 100
    dist_from_high = ((high_52w - ltp) / ltp) * 100
    if rsi < 25:
        score += 35
    elif rsi < 30:
        score += 30
    elif rsi < 35:
        score += 25
    elif rsi < 40:
        score += 20
    if trend and trend > 0:
        score += 25
    elif trend and trend > -1:
        score += 15
    if dist_from_high > 30:
        score += 20
    elif dist_from_high > 20:
        score += 15
    elif dist_from_high > 10:
        score += 10
    range_position = (ltp - low_52w) / (high_52w - low_52w) * 100 if (high_52w - low_52w) > 0 else 50
    if range_position < 30:
        score += 20
    elif range_position < 50:
        score += 10
    target_1 = ltp * 1.05
    target_2 = ltp * 1.10
    target_3 = ltp * 1.15
    stop_loss = ltp * 0.95
    risk = ltp - stop_loss
    reward = target_2 - ltp
    risk_reward = reward / risk if risk > 0 else 0
    return {
        'score': min(score, 100),
        'target_1': target_1,
        'target_2': target_2,
        'target_3': target_3,
        'stop_loss': stop_loss,
        'risk_reward': risk_reward,
        'upside_potential': dist_from_high
    }

def detect_bullish_signals(data, rsi_val, ltp):
    """Detect various bullish technical signals"""
    signals = []
    if rsi_val < 25:
        signals.append("🔥 Extreme Oversold")
    elif rsi_val < 30:
        signals.append("🔥 RSI Oversold")
    elif rsi_val < 40:
        signals.append("📊 RSI Buy Zone")
    mas = calculate_moving_averages(data)
    if mas['ema_9'] and mas['ema_21']:
        if mas['ema_9'] > mas['ema_21'] and ltp > mas['ema_9']:
            signals.append("✅ Golden Cross")
        elif ltp > mas['ema_9']:
            signals.append("📈 Above EMA9")
    if len(data) >= 20 and 'Volume' in data.columns:
        avg_volume = data['Volume'].iloc[-20:-1].mean()
        last_volume = data['Volume'].iloc[-1]
        if last_volume > avg_volume * 1.8:
            signals.append("💥 High Volume")
        elif last_volume > avg_volume * 1.3:
            signals.append("📊 Volume Surge")
    if len(data) >= 2:
        prev_close = data['Close'].iloc[-2]
        prev_open = data['Open'].iloc[-2]
        curr_close = data['Close'].iloc[-1]
        curr_open = data['Open'].iloc[-1]
        if prev_close < prev_open and curr_close > curr_open and curr_close > prev_open:
            signals.append("🕯️ Bullish Pattern")
    return signals

def calculate_index_strength(rsi, week_chg):
    """Calculate overall index strength score (0-100)"""
    score = 0
    if rsi < 25:
        score += 45
    elif rsi < 30:
        score += 40
    elif rsi < 35:
        score += 35
    elif rsi < 40:
        score += 30
    elif rsi < 50:
        score += 15
    if week_chg:
        if week_chg > 5:
            score += 30
        elif week_chg > 3:
            score += 25
        elif week_chg > 1:
            score += 20
        elif week_chg > -1:
            score += 10
    if rsi < 40 and week_chg and week_chg > 0:
        score += 25
    return min(score, 100)

def fetch_market_data(ticker, period="3mo"):
    """Fetch comprehensive market data"""
    try:
        with suppress_stdout():
            data = yf.download(ticker, period=period, interval="1d", progress=False, multi_level_index=False)
        if data.empty or len(data) < 15:
            return None
        ltp = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) >= 2 else ltp
        day_chg_pct = ((ltp - prev_close) / prev_close) * 100
        week_chg_pct = ((ltp - data['Close'].iloc[-6]) / data['Close'].iloc[-6]) * 100 if len(data) >= 6 else None
        rsi_val = calculate_rsi(data['Close']).iloc[-1]
        mas = calculate_moving_averages(data)
        signals = detect_bullish_signals(data, rsi_val, ltp)
        high_52w = data['High'].max()
        low_52w = data['Low'].min()
        profit_metrics = calculate_profit_potential(ltp, high_52w, low_52w, rsi_val, week_chg_pct)
        return {
            "ltp": ltp,
            "day_chg_pct": day_chg_pct,
            "week_chg_pct": week_chg_pct,
            "rsi": rsi_val,
            "sma_20": mas['sma_20'],
            "ema_9": mas['ema_9'],
            "signals": signals,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "profit_score": profit_metrics['score'],
            "target_1": profit_metrics['target_1'],
            "target_2": profit_metrics['target_2'],
            "stop_loss": profit_metrics['stop_loss'],
            "risk_reward": profit_metrics['risk_reward'],
            "upside_potential": profit_metrics['upside_potential']
        }
    except Exception as e:
        return None

# ─────────────────────────────────────────────────────────────
#  THEME 7: NEON CYAN - GitHub Pages HTML Generator
# ─────────────────────────────────────────────────────────────
def generate_github_pages_html(sector_analysis, bullish_sectors, ist_time):
    """Generate Neon Cyan themed index.html for GitHub Pages."""

    total_sectors = len(sector_analysis)
    bullish_count = len(bullish_sectors)

    all_stocks = []
    for sn in bullish_sectors:
        for st in sector_analysis[sn]['stocks']:
            all_stocks.append({**st, 'sector': sn})
    top_picks   = sorted(all_stocks, key=lambda x: x['profit_score'], reverse=True)[:20]
    strong_buys = [s for s in all_stocks if s['profit_score'] >= 70 and s['rsi'] < 30]

    # ── Sector cards ─────────────────────────────────────────
    sector_cards = ""
    for sn, analysis in sector_analysis.items():
        idx  = analysis['index_data']
        sc   = analysis['strength_score']
        bull = sn in bullish_sectors
        badge_color = "#00ff95" if bull else ("#ff6b9d" if idx['rsi'] > 70 else "#ffa502")
        badge_text  = "🟢 BULLISH" if bull else ("🔴 BEARISH" if idx['rsi'] > 70 else "🟡 NEUTRAL")
        wk_color    = "#00ff95" if idx['week_chg_pct'] and idx['week_chg_pct'] > 0 else "#ff6b9d"
        wk_sign     = "+" if idx['week_chg_pct'] and idx['week_chg_pct'] > 0 else ""
        sector_cards += f"""
        <div class="sector-card {'bullish-card' if bull else ''}">
            <div class="sector-name">{sn}</div>
            <div class="sector-badge" style="background:{badge_color}">{badge_text}</div>
            <div class="sector-metrics">
                <span>RSI <strong>{idx['rsi']:.1f}</strong></span>
                <span>Week <strong style="color:{wk_color}">{wk_sign}{idx['week_chg_pct']:.2f}%</strong></span>
                <span>Score <strong>{sc}/100</strong></span>
            </div>
        </div>"""

    # ── Top picks table rows ──────────────────────────────────
    buy_rows = ""
    for i, s in enumerate(top_picks, 1):
        ps  = s['profit_score']
        rsi = s['rsi']
        pc  = "#00ff95" if ps >= 70 else "#ffa502" if ps >= 50 else "#888"
        rc  = "#ff6b9d" if rsi < 25 else "#ff6b9d" if rsi < 40 else "#ffa502" if rsi < 60 else "#00ff95"
        dc  = "#00ff95" if s['day_chg_pct'] > 0 else "#ff6b9d"
        wc  = "#00ff95" if s['week_chg_pct'] and s['week_chg_pct'] > 0 else "#ff6b9d"
        if ps >= 70 and rsi < 30:
            action = '<span class="tag strong-buy">🔥 STRONG BUY</span>'
        elif ps >= 60 or rsi < 35:
            action = '<span class="tag buy">📊 BUY</span>'
        else:
            action = '<span class="tag watch">👀 WATCH</span>'
        sigs = " ".join([f'<span class="sig-pill">{sg}</span>' for sg in s['signals'][:2]])
        buy_rows += f"""
        <tr class="{'top-row' if ps >= 75 else ''}">
            <td><strong>{i}</strong></td>
            <td><strong>{s['symbol']}</strong><br><small style="color:#888">{s['sector']}</small></td>
            <td>₹{s['ltp']:.2f}</td>
            <td style="color:{dc}">{s['day_chg_pct']:+.2f}%</td>
            <td style="color:{wc}">{s['week_chg_pct']:+.2f}%</td>
            <td style="color:{rc}"><strong>{rsi:.1f}</strong></td>
            <td style="color:{pc}"><strong>{ps}/100</strong></td>
            <td style="color:#00ff95">₹{s['target_2']:.2f}</td>
            <td style="color:#ff6b9d">₹{s['stop_loss']:.2f}</td>
            <td style="color:#00ff95">+{s['upside_potential']:.1f}%</td>
            <td>{sigs}</td>
            <td>{action}</td>
        </tr>"""

    # ── Detailed bullish sector breakdown ─────────────────────
    sector_detail = ""
    for sn in bullish_sectors:
        analysis = sector_analysis[sn]
        idx      = analysis['index_data']
        wk_color = "#00ff95" if idx['week_chg_pct'] > 0 else "#ff6b9d"
        wk_sign  = "+" if idx['week_chg_pct'] > 0 else ""
        industries: dict = {}
        for st in analysis['stocks']:
            industries.setdefault(st['industry'], []).append(st)
        ind_tables = ""
        for ind, stocks in sorted(industries.items()):
            stocks_s = sorted(stocks, key=lambda x: x['profit_score'], reverse=True)
            rows = ""
            for st in stocks_s:
                ps  = st['profit_score']
                rsi = st['rsi']
                pc  = "#00ff95" if ps >= 70 else "#ffa502" if ps >= 50 else "#888"
                rc  = "#ff6b9d" if rsi < 25 else "#ff6b9d" if rsi < 40 else "#ffa502" if rsi < 60 else "#00ff95"
                dc  = "#00ff95" if st['day_chg_pct'] > 0 else "#ff6b9d"
                wc  = "#00ff95" if st['week_chg_pct'] and st['week_chg_pct'] > 0 else "#ff6b9d"
                if ps >= 70 and rsi < 30:
                    act = '<span class="tag strong-buy">🔥 STRONG BUY</span>'
                elif ps >= 60 or rsi < 35:
                    act = '<span class="tag buy">📊 BUY</span>'
                else:
                    act = '<span class="tag watch">👀 WATCH</span>'
                sigs = " ".join([f'<span class="sig-pill">{sg}</span>' for sg in st['signals'][:3]])
                rows += f"""
                <tr class="{'top-row' if ps >= 75 else ''}">
                    <td><strong>{st['symbol']}</strong></td>
                    <td>{st['weight']:.1f}%</td>
                    <td>₹{st['ltp']:.2f}</td>
                    <td style="color:{dc}">{st['day_chg_pct']:+.2f}%</td>
                    <td style="color:{wc}">{st['week_chg_pct']:+.2f}%</td>
                    <td style="color:{rc}"><strong>{rsi:.1f}</strong></td>
                    <td style="color:{pc}"><strong>{ps}/100</strong></td>
                    <td style="color:#00ff95">₹{st['target_2']:.2f}</td>
                    <td style="color:#ff6b9d">₹{st['stop_loss']:.2f}</td>
                    <td style="color:#00ff95">+{st['upside_potential']:.1f}%</td>
                    <td>{sigs}</td>
                    <td>{act}</td>
                </tr>"""
            ind_tables += f"""
            <h4 class="industry-title">🏭 {ind}</h4>
            <div class="table-wrap">
            <table>
                <thead><tr>
                    <th>Stock</th><th>Weight</th><th>LTP</th>
                    <th>Day %</th><th>Week %</th><th>RSI</th>
                    <th>Score</th><th>Target</th><th>Stop Loss</th>
                    <th>Upside</th><th>Signals</th><th>Action</th>
                </tr></thead>
                <tbody>{rows}</tbody>
            </table></div>"""
        sector_detail += f"""
        <div class="sector-detail-block">
            <div class="sector-detail-header">
                <h3>📊 {sn.upper()} — Bullish Setup</h3>
                <div class="sector-meta">
                    RSI: <strong>{idx['rsi']:.1f}</strong> &nbsp;|&nbsp;
                    Week: <strong style="color:{wk_color}">{wk_sign}{idx['week_chg_pct']:.2f}%</strong> &nbsp;|&nbsp;
                    LTP: <strong>₹{idx['ltp']:.2f}</strong> &nbsp;|&nbsp;
                    Score: <strong>{analysis['strength_score']}/100</strong>
                </div>
            </div>
            {ind_tables}
        </div>"""

    top_symbol = top_picks[0]['symbol'] if top_picks else '—'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎯 Nifty Indices - Neon Cyan Theme</title>
<style>
  :root {{
    --neon-cyan:#00d9ff;
    --neon-green:#00ff95;
    --neon-pink:#ff6b9d;
    --neon-orange:#ffa502;
    --dark-bg:#000814;
    --darker:#001f3f;
  }}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{
    font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;
    background:linear-gradient(135deg, var(--darker) 0%, var(--dark-bg) 100%);
    min-height:100vh; padding:20px; color:#cfd8dc;
  }}
  .container {{
    max-width:1400px; margin:auto; background:rgba(0, 8, 20, 0.95);
    border-radius:16px; box-shadow:0 0 40px rgba(0, 217, 255, 0.4);
    overflow:hidden; border:1px solid rgba(0, 217, 255, 0.3);
  }}
  .header {{
    background:linear-gradient(135deg, var(--darker) 0%, #003d7a 100%);
    color:var(--neon-cyan); padding:36px 30px 28px; text-align:center;
    text-shadow:0 0 20px rgba(0, 217, 255, 0.8);
    border-bottom:3px solid var(--neon-cyan);
  }}
  .header h1 {{ font-size:2.2rem; font-weight:700; margin-bottom:6px; }}
  .header .subtitle {{ opacity:.85; font-size:.95rem; color:#80deea; }}
  .summary-strip {{
    display:flex; flex-wrap:wrap; gap:16px;
    padding:24px 30px; background:rgba(0, 31, 63, 0.5);
    border-bottom:1px solid rgba(0, 217, 255, 0.2);
  }}
  .stat-box {{
    flex:1 1 140px; background:rgba(0, 217, 255, 0.1);
    border-radius:10px; padding:16px 20px; text-align:center;
    box-shadow:0 0 15px rgba(0, 217, 255, 0.2);
    border-left:4px solid var(--neon-cyan);
    transition:all 0.3s;
  }}
  .stat-box:hover {{
    transform:translateY(-3px);
    box-shadow:0 0 25px rgba(0, 217, 255, 0.4);
  }}
  .stat-box .stat-val {{ font-size:2rem; font-weight:700; color:var(--neon-cyan); }}
  .stat-box .stat-lbl {{ font-size:.78rem; color:#80deea; margin-top:4px; text-transform:uppercase; letter-spacing:.5px; }}
  .section {{ padding:28px 30px; }}
  .section-title {{
    font-size:1.25rem; font-weight:700; color:var(--neon-cyan);
    padding:10px 16px; border-left:5px solid var(--neon-cyan);
    background:linear-gradient(90deg,rgba(0, 217, 255, 0.1) 0%, transparent 100%);
    border-radius:4px; margin-bottom:20px;
    text-shadow:0 0 10px rgba(0, 217, 255, 0.5);
  }}
  .sector-grid {{
    display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
    gap:14px; margin-bottom:10px;
  }}
  .sector-card {{
    border:1px solid rgba(0, 217, 255, 0.3);
    border-radius:10px; padding:14px;
    background:rgba(0, 217, 255, 0.05);
    box-shadow:0 0 10px rgba(0, 217, 255, 0.15);
    transition:all 0.3s;
  }}
  .sector-card:hover {{
    transform:translateY(-3px);
    box-shadow:0 0 20px rgba(0, 217, 255, 0.3);
  }}
  .bullish-card {{
    border-color:var(--neon-green);
    background:linear-gradient(135deg,rgba(0, 255, 149, 0.1) 0%, transparent 100%);
    box-shadow:0 0 15px rgba(0, 255, 149, 0.2);
  }}
  .sector-name {{ font-weight:700; font-size:.9rem; color:var(--neon-cyan); margin-bottom:6px; }}
  .sector-badge {{ display:inline-block; color:#000; font-size:.72rem; font-weight:700; padding:3px 9px; border-radius:20px; margin-bottom:8px; }}
  .sector-metrics {{ font-size:.8rem; color:#cfd8dc; display:flex; flex-direction:column; gap:3px; }}
  .table-wrap {{ overflow-x:auto; margin-bottom:20px; }}
  table {{ width:100%; border-collapse:collapse; font-size:.83rem; }}
  thead tr {{ background:linear-gradient(135deg, var(--darker) 0%, #003d7a 100%); }}
  thead th {{
    color:var(--neon-cyan); padding:11px 10px; text-align:left;
    font-weight:600; font-size:.75rem; text-transform:uppercase;
    letter-spacing:.4px; white-space:nowrap;
    text-shadow:0 0 5px rgba(0, 217, 255, 0.5);
  }}
  tbody td {{ padding:10px; border-bottom:1px solid rgba(0, 217, 255, 0.1); vertical-align:middle; color:#cfd8dc; }}
  tbody tr:hover {{ background:rgba(0, 217, 255, 0.05); }}
  .top-row {{ background:linear-gradient(90deg,rgba(0, 217, 255, 0.1) 0%, transparent 100%) !important; border-left:3px solid var(--neon-cyan); }}
  .tag {{ display:inline-block; padding:4px 10px; border-radius:5px; font-size:.72rem; font-weight:700; white-space:nowrap; }}
  .strong-buy {{ background:var(--neon-green); color:#000; }}
  .buy        {{ background:var(--neon-cyan); color:#000; }}
  .watch      {{ background:#888;           color:#fff; }}
  .sig-pill {{
    display:inline-block;
    background:linear-gradient(135deg, var(--neon-cyan) 0%, #0099cc 100%);
    color:#000; font-size:.65rem; padding:2px 7px; border-radius:12px;
    margin:1px; white-space:nowrap; font-weight:700;
    box-shadow:0 0 5px rgba(0, 217, 255, 0.5);
  }}
  .sector-detail-block {{
    margin-bottom:40px;
    border:1px solid rgba(0, 217, 255, 0.3);
    border-radius:12px; overflow:hidden;
    box-shadow:0 0 20px rgba(0, 217, 255, 0.2);
  }}
  .sector-detail-header {{
    background:linear-gradient(135deg, var(--darker) 0%, #003d7a 100%);
    color:var(--neon-cyan); padding:16px 20px;
    border-bottom:2px solid var(--neon-cyan);
  }}
  .sector-detail-header h3 {{
    font-size:1.1rem; margin-bottom:6px;
    text-shadow:0 0 10px rgba(0, 217, 255, 0.8);
  }}
  .sector-meta {{ font-size:.85rem; opacity:.9; color:#80deea; }}
  .industry-title {{
    font-size:.9rem; color:var(--neon-green);
    padding:10px 16px 4px;
    border-bottom:2px solid rgba(0, 255, 149, 0.3);
    margin-bottom:4px;
    text-shadow:0 0 8px rgba(0, 255, 149, 0.5);
  }}
  .disclaimer {{
    background:rgba(255, 107, 157, 0.1);
    border-left:4px solid var(--neon-pink);
    border-radius:6px; padding:14px 18px; font-size:.8rem;
    color:#ffb3d9; margin:10px 0 0;
    box-shadow:0 0 10px rgba(255, 107, 157, 0.2);
  }}
  .footer {{
    text-align:center; padding:20px;
    background:rgba(0, 31, 63, 0.5);
    font-size:.8rem; color:#80deea;
    border-top:1px solid rgba(0, 217, 255, 0.2);
  }}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>🎯 Nifty Indices Market Intelligence</h1>
    <div class="subtitle">Generated: {ist_time}</div>
  </div>

  <div class="summary-strip">
    <div class="stat-box">
      <div class="stat-val">{total_sectors}</div>
      <div class="stat-lbl">Sectors Analyzed</div>
    </div>
    <div class="stat-box" style="border-color:var(--neon-green)">
      <div class="stat-val" style="color:var(--neon-green)">{bullish_count}</div>
      <div class="stat-lbl">Bullish Sectors</div>
    </div>
    <div class="stat-box" style="border-color:var(--neon-cyan)">
      <div class="stat-val" style="color:var(--neon-cyan)">{len(top_picks)}</div>
      <div class="stat-lbl">Buy Opportunities</div>
    </div>
    <div class="stat-box" style="border-color:var(--neon-orange)">
      <div class="stat-val" style="color:var(--neon-orange)">{len(strong_buys)}</div>
      <div class="stat-lbl">Strong Buys</div>
    </div>
    <div class="stat-box" style="border-color:var(--neon-cyan)">
      <div class="stat-val" style="color:var(--neon-cyan);font-size:1.1rem;padding-top:8px">{top_symbol}</div>
      <div class="stat-lbl">Top Pick</div>
    </div>
  </div>

  <div class="section">
    <div class="section-title">🏆 Sector Overview</div>
    <div class="sector-grid">{sector_cards}</div>
  </div>

  <div class="section">
    <div class="section-title">🟢 Top Buy Recommendations</div>
    <div class="table-wrap">
    <table>
      <thead><tr>
        <th>#</th><th>Stock</th><th>LTP</th><th>Day %</th><th>Week %</th>
        <th>RSI</th><th>Score</th><th>Target</th><th>Stop Loss</th>
        <th>Upside</th><th>Signals</th><th>Action</th>
      </tr></thead>
      <tbody>{buy_rows}</tbody>
    </table>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📊 Detailed Sector Breakdown (Bullish Only)</div>
    {sector_detail if sector_detail else '<p style="color:#888;padding:10px">No bullish sectors detected in this session.</p>'}
  </div>

  <div class="section">
    <div class="disclaimer">
      <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational purposes only.
      Past performance does not guarantee future results. All trading involves risk.
      Please conduct your own research and consult with a certified financial advisor before making any investment decisions.
      The profit scores and targets are algorithmic calculations and should not be considered as guaranteed outcomes.
    </div>
  </div>

  <div class="footer">© 2026 Nifty Indices Scanner | Neon Cyan Theme | For Educational Purposes Only</div>
</div>
</body>
</html>"""
    return html


def generate_executive_html_report(sector_analysis, bullish_sectors, ist_time):
    """Generate executive-level HTML report with Neon Cyan theme (for email)"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #001f3f 0%, #003d7a 100%); padding: 20px; margin: 0; }}
            .container {{ max-width: 1400px; margin: auto; background: #000814; padding: 30px; border-radius: 15px; box-shadow: 0 0 40px rgba(0, 217, 255, 0.5); border: 2px solid rgba(0, 217, 255, 0.3); }}
            .header {{ background: linear-gradient(135deg, #001f3f 0%, #003d7a 100%); color: #00d9ff; padding: 25px; border-radius: 10px; margin-bottom: 30px; text-align: center; text-shadow: 0 0 20px rgba(0, 217, 255, 0.8); border: 2px solid #00d9ff; }}
            h1 {{ color: #00d9ff; margin: 0; font-size: 32px; font-weight: 600; }}
            .timestamp {{ color: #80deea; font-size: 14px; margin-top: 8px; }}
            h2 {{ color: #00d9ff; margin-top: 35px; padding: 12px 15px; background: linear-gradient(90deg, rgba(0, 217, 255, 0.2) 0%, transparent 100%); border-left: 5px solid #00d9ff; border-radius: 5px; font-size: 22px; text-shadow: 0 0 10px rgba(0, 217, 255, 0.5); }}
            h3 {{ color: #00ff95; margin-top: 25px; font-size: 18px; padding-bottom: 8px; border-bottom: 2px solid rgba(0, 255, 149, 0.3); text-shadow: 0 0 8px rgba(0, 255, 149, 0.5); }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; box-shadow: 0 0 20px rgba(0, 217, 255, 0.3); border-radius: 8px; overflow: hidden; }}
            th {{ background: linear-gradient(135deg, #001f3f 0%, #003d7a 100%); color: #00d9ff; padding: 14px 10px; text-align: left; font-weight: 600; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; text-shadow: 0 0 5px rgba(0, 217, 255, 0.5); }}
            td {{ padding: 12px 10px; border-bottom: 1px solid rgba(0, 217, 255, 0.1); font-size: 13px; background: rgba(0, 8, 20, 0.8); color: #cfd8dc; }}
            tr:hover {{ background-color: rgba(0, 217, 255, 0.05); }}
            .rsi-extreme {{ color: #ff6b9d; font-weight: bold; }}
            .rsi-low {{ color: #ff6b9d; font-weight: bold; }}
            .rsi-medium {{ color: #ffa502; font-weight: bold; }}
            .rsi-high {{ color: #00ff95; font-weight: bold; }}
            .positive {{ color: #00ff95; font-weight: 600; }}
            .negative {{ color: #ff6b9d; font-weight: 600; }}
            .signal-badge {{ display: inline-block; background: linear-gradient(135deg, #00d9ff 0%, #0099cc 100%); color: #000; padding: 4px 10px; border-radius: 15px; font-size: 10px; margin: 2px; font-weight: 700; box-shadow: 0 0 5px rgba(0, 217, 255, 0.5); }}
            .bullish-sector {{ background: linear-gradient(90deg, rgba(0, 255, 149, 0.1) 0%, transparent 100%); border-left: 5px solid #00ff95; }}
            .summary-box {{ background: linear-gradient(135deg, rgba(0, 217, 255, 0.15) 0%, rgba(0, 217, 255, 0.05) 100%); padding: 20px; border-radius: 10px; margin: 25px 0; border-left: 5px solid #00d9ff; box-shadow: 0 0 15px rgba(0, 217, 255, 0.3); }}
            .metric {{ display: inline-block; margin: 8px 15px; font-size: 15px; color: #cfd8dc; }}
            .metric strong {{ color: #00d9ff; }}
            .sector-header {{ background: linear-gradient(135deg, #001f3f 0%, #003d7a 100%); color: #00d9ff; padding: 18px; border-radius: 10px; margin-top: 35px; box-shadow: 0 0 20px rgba(0, 217, 255, 0.4); border: 2px solid #00d9ff; }}
            .sector-header h2 {{ color: #00d9ff; margin: 0; background: none; border: none; padding: 0; font-size: 24px; text-shadow: 0 0 15px rgba(0, 217, 255, 0.8); }}
            .profit-high {{ color: #00ff95; font-weight: bold; }}
            .profit-medium {{ color: #ffa502; font-weight: bold; }}
            .profit-low {{ color: #888; }}
            .action-strong-buy {{ background: #00ff95; color: #000; padding: 6px 12px; border-radius: 5px; font-weight: bold; display: inline-block; box-shadow: 0 0 10px rgba(0, 255, 149, 0.5); }}
            .action-buy {{ background: #00d9ff; color: #000; padding: 6px 12px; border-radius: 5px; font-weight: bold; display: inline-block; box-shadow: 0 0 10px rgba(0, 217, 255, 0.5); }}
            .action-watch {{ background: #888; color: #fff; padding: 6px 12px; border-radius: 5px; font-weight: bold; display: inline-block; }}
            .top-pick {{ background: linear-gradient(90deg, rgba(0, 217, 255, 0.15) 0%, transparent 100%); border-left: 5px solid #00d9ff; }}
            .disclaimer {{ background: rgba(255, 107, 157, 0.1); padding: 15px; border-radius: 8px; margin-top: 40px; border-left: 4px solid #ff6b9d; font-size: 12px; color: #ffb3d9; box-shadow: 0 0 10px rgba(255, 107, 157, 0.2); }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Market Intelligence Report</h1>
                <div class="timestamp">Generated: {ist_time}</div>
            </div>
            <div class="summary-box">
                <h3 style="margin-top: 0; border: none; color: #00d9ff;">📊 Executive Summary</h3>
                <div class="metric">🎯 <strong>Bullish Sectors:</strong> {len(bullish_sectors)}</div>
                <div class="metric">📈 <strong>Total Sectors Analyzed:</strong> {len(sector_analysis)}</div>
                <div class="metric">💡 <strong>Top Opportunities:</strong> {', '.join(bullish_sectors[:3]) if bullish_sectors else 'None'}</div>
            </div>
    """

    html += "<h2>🏆 Sector Performance Rankings</h2>"
    html += '<table><tr><th>Rank</th><th>Sector</th><th>Index RSI</th><th>Week Change</th><th>Strength Score</th><th>Status</th><th>Top Stocks</th></tr>'
    for rank, (sector_name, analysis) in enumerate(sector_analysis.items(), 1):
        idx_data   = analysis['index_data']
        score      = analysis['strength_score']
        status     = "🟢 BULLISH" if sector_name in bullish_sectors else "🔴 BEARISH" if idx_data['rsi'] > 70 else "🟡 NEUTRAL"
        rsi_class  = "rsi-extreme" if idx_data['rsi'] < 25 else "rsi-low" if idx_data['rsi'] < 40 else "rsi-medium" if idx_data['rsi'] < 60 else "rsi-high"
        week_class = "positive" if idx_data['week_chg_pct'] and idx_data['week_chg_pct'] > 0 else "negative"
        top_stocks = sorted(analysis['stocks'], key=lambda x: x['profit_score'], reverse=True)[:2]
        top_stocks_str = ', '.join([s['symbol'] for s in top_stocks])
        html += f"""
        <tr class="{'bullish-sector' if sector_name in bullish_sectors else ''}">
            <td><strong>{rank}</strong></td><td><strong>{sector_name}</strong></td>
            <td class="{rsi_class}">{idx_data['rsi']:.1f}</td>
            <td class="{week_class}">{idx_data['week_chg_pct']:+.2f}%</td>
            <td><strong>{score}/100</strong></td><td>{status}</td><td>{top_stocks_str}</td>
        </tr>"""
    html += "</table>"

    for sector_name in bullish_sectors:
        analysis = sector_analysis[sector_name]
        idx_data = analysis['index_data']
        html += f"""
        <div class="sector-header">
            <h2>📊 {sector_name.upper()} - Bullish Setup</h2>
            <div style="margin-top: 10px; font-size: 14px; color: #80deea;">
                Index RSI: <strong style="color: #00d9ff;">{idx_data['rsi']:.1f}</strong> |
                Week: <strong class="{'positive' if idx_data['week_chg_pct'] > 0 else 'negative'}">{idx_data['week_chg_pct']:+.2f}%</strong> |
                LTP: <strong style="color: #00d9ff;">₹{idx_data['ltp']:.2f}</strong>
            </div>
        </div>"""
        industries = {}
        for stock_info in analysis['stocks']:
            industries.setdefault(stock_info['industry'], []).append(stock_info)
        for industry, stocks in sorted(industries.items()):
            stocks_sorted = sorted(stocks, key=lambda x: x['profit_score'], reverse=True)
            html += f"<h3>🏭 {industry}</h3>"
            html += "<table><tr><th>Stock</th><th>Weight</th><th>LTP</th><th>Day %</th><th>Week %</th><th>RSI</th><th>Profit Score</th><th>Target</th><th>Stop Loss</th><th>Upside %</th><th>Signals</th><th>Action</th></tr>"
            for stock in stocks_sorted:
                rsi_class    = "rsi-extreme" if stock['rsi'] < 25 else "rsi-low" if stock['rsi'] < 40 else "rsi-medium" if stock['rsi'] < 60 else "rsi-high"
                day_class    = "positive" if stock['day_chg_pct'] > 0 else "negative"
                week_class   = "positive" if stock['week_chg_pct'] and stock['week_chg_pct'] > 0 else "negative"
                profit_class = "profit-high" if stock['profit_score'] >= 70 else "profit-medium" if stock['profit_score'] >= 50 else "profit-low"
                if stock['profit_score'] >= 70 and stock['rsi'] < 30:
                    action = '<span class="action-strong-buy">🔥 STRONG BUY</span>'
                elif stock['profit_score'] >= 60 or stock['rsi'] < 35:
                    action = '<span class="action-buy">📊 BUY</span>'
                else:
                    action = '<span class="action-watch">👀 WATCH</span>'
                signals_html = ' '.join([f'<span class="signal-badge">{sig}</span>' for sig in stock['signals'][:3]])
                row_class = "top-pick" if stock['profit_score'] >= 75 else ""
                html += f"""
                <tr class="{row_class}">
                    <td><strong>{stock['symbol']}</strong></td><td>{stock['weight']:.1f}%</td>
                    <td>₹{stock['ltp']:.2f}</td>
                    <td class="{day_class}">{stock['day_chg_pct']:+.2f}%</td>
                    <td class="{week_class}">{stock['week_chg_pct']:+.2f}%</td>
                    <td class="{rsi_class}">{stock['rsi']:.1f}</td>
                    <td class="{profit_class}"><strong>{stock['profit_score']}/100</strong></td>
                    <td class="positive">₹{stock['target_2']:.2f}</td>
                    <td class="negative">₹{stock['stop_loss']:.2f}</td>
                    <td class="positive">+{stock['upside_potential']:.1f}%</td>
                    <td>{signals_html}</td><td>{action}</td>
                </tr>"""
            html += "</table>"

    html += """
        <div class="disclaimer">
            <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational purposes only.
            Past performance does not guarantee future results. All trading involves risk.
            Please conduct your own research and consult with a certified financial advisor before making any investment decisions.
            The profit scores and targets are algorithmic calculations and should not be considered as guaranteed outcomes.
        </div></div></body></html>"""
    return html


def send_email_report(html_content, subject):
    """Send email report via Gmail (inline, no attachment)"""
    try:
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = RECEIVER_EMAIL
        msg.attach(MIMEText(html_content, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.send_message(msg)
        print(f"{GREEN}✅ Email sent successfully to {RECEIVER_EMAIL}{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ Email failed: {e}{RESET}")
        return False

def send_whatsapp_alert(bullish_sectors, top_picks, ist_time):
    """Send WhatsApp alert with top picks"""
    if not (TWILIO_SID and TWILIO_AUTH_TOKEN):
        print(f"{YELLOW}⚠️ WhatsApp disabled (missing credentials){RESET}")
        return False
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message_body = f"""🎯 *Market Alert - {ist_time}*\n\n📊 *Bullish Sectors:* {len(bullish_sectors)}\n"""
        if bullish_sectors:
            message_body += "\n💡 *Top Sectors:*\n"
            for sector in bullish_sectors[:3]:
                message_body += f"• {sector}\n"
            if top_picks:
                message_body += "\n🔥 *Top Profit Picks:*\n"
                for pick in top_picks[:5]:
                    message_body += f"• {pick['symbol']} (Score: {pick['score']}/100)\n"
        else:
            message_body += "\n⚠️ No bullish setups detected"
        message_body += "\n📧 Full report sent via email"
        client.messages.create(from_=TWILIO_FROM, body=message_body, to=TWILIO_TO)
        print(f"{GREEN}✅ WhatsApp alert sent{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ WhatsApp failed: {e}{RESET}")
        return False

def main():
    print(f"{CYAN}{'='*80}{RESET}")
    print(f"{CYAN}🎯 NEON CYAN THEME - Market Intelligence Scanner{RESET}")
    print(f"{CYAN}{'='*80}{RESET}\n")

    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    ist_time_str = now_ist.strftime("%Y-%m-%d %H:%M IST")

    print(f"{BLUE}⏰ Analysis Time: {ist_time_str}{RESET}\n")

    sector_analysis = {}
    bullish_sectors = []
    all_stocks = []

    for sector_name, config in sectors_config.items():
        print(f"{YELLOW}📊 Analyzing {sector_name}...{RESET}")
        index_data = fetch_market_data(config['ticker'])
        if not index_data:
            print(f"{RED}   ❌ Failed to fetch index data{RESET}")
            continue
        strength_score = calculate_index_strength(index_data['rsi'], index_data['week_chg_pct'])
        is_bullish = (index_data['rsi'] < 40) or (index_data['rsi'] < 50 and index_data['week_chg_pct'] and index_data['week_chg_pct'] > 2)
        if is_bullish:
            bullish_sectors.append(sector_name)
            print(f"{GREEN}   ✅ BULLISH - RSI: {index_data['rsi']:.1f}, Score: {strength_score}/100{RESET}")
        else:
            print(f"{RED}   ⏸️  Not Bullish - RSI: {index_data['rsi']:.1f}{RESET}")

        stocks_data = []
        for stock_ticker, stock_info in config['stocks'].items():
            stock_data = fetch_market_data(stock_ticker)
            if stock_data:
                stock_entry = {
                    'symbol': stock_ticker.replace('.NS', ''),
                    'weight': stock_info['weight'],
                    'industry': stock_info['industry'],
                    **stock_data
                }
                stocks_data.append(stock_entry)
                if is_bullish:
                    all_stocks.append({'symbol': stock_entry['symbol'], 'score': stock_entry['profit_score'], 'sector': sector_name})

        sector_analysis[sector_name] = {
            'index_data': index_data,
            'strength_score': strength_score,
            'is_bullish': is_bullish,
            'stocks': stocks_data
        }

    top_picks = sorted(all_stocks, key=lambda x: x['score'], reverse=True)[:10]

    print(f"\n{CYAN}{'='*80}{RESET}")
    print(f"{GREEN}✅ Analysis Complete!{RESET}")
    print(f"{MAGENTA}📊 Bullish Sectors: {len(bullish_sectors)}{RESET}")
    if bullish_sectors:
        for sector in bullish_sectors:
            print(f"{GREEN}   • {sector}{RESET}")
    print(f"\n{MAGENTA}🔥 Top Profit Picks:{RESET}")
    for i, pick in enumerate(top_picks[:5], 1):
        print(f"{YELLOW}   {i}. {pick['symbol']} - Score: {pick['score']}/100 ({pick['sector']}){RESET}")
    print(f"{CYAN}{'='*80}{RESET}\n")

    # ── Save GitHub Pages HTML ──────────────────────────────────
    pages_html = generate_github_pages_html(sector_analysis, bullish_sectors, ist_time_str)
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(pages_html)
    print(f"{GREEN}✅ index.html saved for GitHub Pages (Neon Cyan Theme){RESET}")

    # ── Send email ─────────────────────────────────────────────
    html_report = generate_executive_html_report(sector_analysis, bullish_sectors, ist_time_str)
    if bullish_sectors:
        subject = f"🎯 {len(bullish_sectors)} Bullish Sectors | Top Pick: {top_picks[0]['symbol']} | {ist_time_str}"
    else:
        subject = f"📊 Market Report | No Bullish Signals | {ist_time_str}"

    email_sent    = send_email_report(html_report, subject)
    whatsapp_sent = send_whatsapp_alert(bullish_sectors, top_picks, ist_time_str)

    print(f"\n{CYAN}{'='*80}{RESET}")
    print(f"{GREEN}🎯 Report Generation Complete (Neon Cyan Theme){RESET}")
    print(f"   Email:      {'✅ Sent' if email_sent else '❌ Failed'}")
    print(f"   WhatsApp:   {'✅ Sent' if whatsapp_sent else '⚠️ Skipped'}")
    print(f"   Pages HTML: ✅ index.html written")
    print(f"{CYAN}{'='*80}{RESET}\n")

if __name__ == "__main__":
    main()
