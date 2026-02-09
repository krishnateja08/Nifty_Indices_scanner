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
            "TATAMOTORS.NS": {"weight": 15.0, "industry": "Commercial Vehicles"},
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
    """
    Advanced profit potential calculation
    Returns: profit_score (0-100), target_price, stop_loss, risk_reward_ratio
    """
    score = 0
    
    # Distance from 52-week low (higher = better for momentum)
    dist_from_low = ((ltp - low_52w) / low_52w) * 100
    dist_from_high = ((high_52w - ltp) / ltp) * 100
    
    # RSI-based scoring (oversold = higher potential)
    if rsi < 25:
        score += 35  # Extremely oversold
    elif rsi < 30:
        score += 30
    elif rsi < 35:
        score += 25
    elif rsi < 40:
        score += 20
    
    # Trend momentum (positive weekly change even when oversold = strong reversal)
    if trend and trend > 0:
        score += 25  # Bullish reversal in progress
    elif trend and trend > -1:
        score += 15  # Consolidating
    
    # Upside potential (room to 52W high)
    if dist_from_high > 30:
        score += 20  # Significant upside
    elif dist_from_high > 20:
        score += 15
    elif dist_from_high > 10:
        score += 10
    
    # Position from 52W range (lower = better entry)
    range_position = (ltp - low_52w) / (high_52w - low_52w) * 100 if (high_52w - low_52w) > 0 else 50
    if range_position < 30:
        score += 20  # In bottom 30% of range
    elif range_position < 50:
        score += 10
    
    # Calculate targets
    target_1 = ltp * 1.05  # 5% target
    target_2 = ltp * 1.10  # 10% target
    target_3 = ltp * 1.15  # 15% target
    stop_loss = ltp * 0.95  # 5% stop loss
    
    # Risk-Reward Ratio
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
    
    # RSI Levels
    if rsi_val < 25:
        signals.append("🔥 Extreme Oversold")
    elif rsi_val < 30:
        signals.append("🔥 RSI Oversold")
    elif rsi_val < 40:
        signals.append("📊 RSI Buy Zone")
    
    # Moving Average Analysis
    mas = calculate_moving_averages(data)
    if mas['ema_9'] and mas['ema_21']:
        if mas['ema_9'] > mas['ema_21'] and ltp > mas['ema_9']:
            signals.append("✅ Golden Cross")
        elif ltp > mas['ema_9']:
            signals.append("📈 Above EMA9")
    
    # Volume Surge
    if len(data) >= 20 and 'Volume' in data.columns:
        avg_volume = data['Volume'].iloc[-20:-1].mean()
        last_volume = data['Volume'].iloc[-1]
        if last_volume > avg_volume * 1.8:
            signals.append("💥 High Volume")
        elif last_volume > avg_volume * 1.3:
            signals.append("📊 Volume Surge")
    
    # Price Action (Bullish Engulfing)
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
    
    # RSI Component
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
    
    # Trend Component
    if week_chg:
        if week_chg > 5:
            score += 30
        elif week_chg > 3:
            score += 25
        elif week_chg > 1:
            score += 20
        elif week_chg > -1:
            score += 10
    
    # Reversal Bonus
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

def generate_executive_html_report(sector_analysis, bullish_sectors, ist_time):
    """Generate executive-level HTML report with advanced styling"""
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ 
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 20px; 
                margin: 0;
            }}
            .container {{ 
                max-width: 1400px; 
                margin: auto; 
                background: white; 
                padding: 30px; 
                border-radius: 15px; 
                box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            h1 {{ 
                color: white; 
                margin: 0;
                font-size: 32px;
                font-weight: 600;
            }}
            .timestamp {{
                color: rgba(255,255,255,0.9);
                font-size: 14px;
                margin-top: 8px;
            }}
            h2 {{ 
                color: #2c3e50; 
                margin-top: 35px; 
                padding: 12px 15px;
                background: linear-gradient(90deg, #ecf0f1 0%, #ffffff 100%);
                border-left: 5px solid #3498db;
                border-radius: 5px;
                font-size: 22px;
            }}
            h3 {{ 
                color: #16a085; 
                margin-top: 25px; 
                font-size: 18px;
                padding-bottom: 8px;
                border-bottom: 2px solid #ecf0f1;
            }}
            table {{ 
                width: 100%; 
                border-collapse: collapse; 
                margin: 20px 0; 
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
            }}
            th {{ 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 14px 10px; 
                text-align: left; 
                font-weight: 600;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            td {{ 
                padding: 12px 10px; 
                border-bottom: 1px solid #ecf0f1;
                font-size: 13px;
            }}
            tr:hover {{ 
                background-color: #f8f9fa; 
            }}
            .rsi-extreme {{ color: #c0392b; font-weight: bold; }}
            .rsi-low {{ color: #e74c3c; font-weight: bold; }}
            .rsi-medium {{ color: #f39c12; font-weight: bold; }}
            .rsi-high {{ color: #27ae60; font-weight: bold; }}
            .positive {{ color: #27ae60; font-weight: 600; }}
            .negative {{ color: #e74c3c; font-weight: 600; }}
            .signal-badge {{ 
                display: inline-block; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; 
                padding: 4px 10px; 
                border-radius: 15px; 
                font-size: 10px; 
                margin: 2px; 
                font-weight: 600;
            }}
            .bullish-sector {{ 
                background: linear-gradient(90deg, #d4edda 0%, #ffffff 100%);
                border-left: 5px solid #28a745;
            }}
            .summary-box {{ 
                background: linear-gradient(135deg, #e8f4f8 0%, #f0f8ff 100%);
                padding: 20px; 
                border-radius: 10px; 
                margin: 25px 0; 
                border-left: 5px solid #3498db;
                box-shadow: 0 3px 10px rgba(0,0,0,0.1);
            }}
            .metric {{ 
                display: inline-block; 
                margin: 8px 15px;
                font-size: 15px;
            }}
            .metric strong {{
                color: #2c3e50;
            }}
            .sector-header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 18px;
                border-radius: 10px;
                margin-top: 35px;
                box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            }}
            .sector-header h2 {{
                color: white;
                margin: 0;
                background: none;
                border: none;
                padding: 0;
                font-size: 24px;
            }}
            .profit-high {{ color: #27ae60; font-weight: bold; }}
            .profit-medium {{ color: #f39c12; font-weight: bold; }}
            .profit-low {{ color: #95a5a6; }}
            .action-strong-buy {{ 
                background: #27ae60; 
                color: white; 
                padding: 6px 12px; 
                border-radius: 5px; 
                font-weight: bold;
                display: inline-block;
            }}
            .action-buy {{ 
                background: #3498db; 
                color: white; 
                padding: 6px 12px; 
                border-radius: 5px; 
                font-weight: bold;
                display: inline-block;
            }}
            .action-watch {{ 
                background: #95a5a6; 
                color: white; 
                padding: 6px 12px; 
                border-radius: 5px; 
                font-weight: bold;
                display: inline-block;
            }}
            .top-pick {{
                background: linear-gradient(90deg, #fff3cd 0%, #ffffff 100%);
                border-left: 5px solid #ffc107;
            }}
            .disclaimer {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 8px;
                margin-top: 40px;
                border-left: 4px solid #e74c3c;
                font-size: 12px;
                color: #6c757d;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 Market Intelligence Report</h1>
                <div class="timestamp">Generated: {ist_time}</div>
            </div>
            
            <div class="summary-box">
                <h3 style="margin-top: 0; border: none; color: #2c3e50;">📊 Executive Summary</h3>
                <div class="metric">🎯 <strong>Bullish Sectors:</strong> {len(bullish_sectors)}</div>
                <div class="metric">📈 <strong>Total Sectors Analyzed:</strong> {len(sector_analysis)}</div>
                <div class="metric">💡 <strong>Top Opportunities:</strong> {', '.join(bullish_sectors[:3]) if bullish_sectors else 'None'}</div>
            </div>
    """
    
    # Sector Rankings Table
    html += "<h2>🏆 Sector Performance Rankings</h2>"
    html += '<table><tr><th>Rank</th><th>Sector</th><th>Index RSI</th><th>Week Change</th><th>Strength Score</th><th>Status</th><th>Top Stocks</th></tr>'
    
    for rank, (sector_name, analysis) in enumerate(sector_analysis.items(), 1):
        idx_data = analysis['index_data']
        score = analysis['strength_score']
        status = "🟢 BULLISH" if sector_name in bullish_sectors else "🔴 BEARISH" if idx_data['rsi'] > 70 else "🟡 NEUTRAL"
        
        rsi_class = "rsi-extreme" if idx_data['rsi'] < 25 else "rsi-low" if idx_data['rsi'] < 40 else "rsi-medium" if idx_data['rsi'] < 60 else "rsi-high"
        week_class = "positive" if idx_data['week_chg_pct'] and idx_data['week_chg_pct'] > 0 else "negative"
        
        # Get top 2 stocks by profit score
        top_stocks = sorted(analysis['stocks'], key=lambda x: x['profit_score'], reverse=True)[:2]
        top_stocks_str = ', '.join([s['symbol'] for s in top_stocks])
        
        html += f"""
        <tr class="{'bullish-sector' if sector_name in bullish_sectors else ''}">
            <td><strong>{rank}</strong></td>
            <td><strong>{sector_name}</strong></td>
            <td class="{rsi_class}">{idx_data['rsi']:.1f}</td>
            <td class="{week_class}">{idx_data['week_chg_pct']:+.2f}%</td>
            <td><strong>{score}/100</strong></td>
            <td>{status}</td>
            <td>{top_stocks_str}</td>
        </tr>
        """
    html += "</table>"
    
    # Detailed Analysis for Bullish Sectors
    for sector_name in bullish_sectors:
        analysis = sector_analysis[sector_name]
        idx_data = analysis['index_data']
        
        html += f"""
        <div class="sector-header">
            <h2>📊 {sector_name.upper()} - Bullish Setup</h2>
            <div style="margin-top: 10px; font-size: 14px;">
                Index RSI: <strong>{idx_data['rsi']:.1f}</strong> | 
                Week: <strong class="{'positive' if idx_data['week_chg_pct'] > 0 else 'negative'}">{idx_data['week_chg_pct']:+.2f}%</strong> | 
                LTP: <strong>₹{idx_data['ltp']:.2f}</strong>
            </div>
        </div>
        """
        
        # Group stocks by industry
        industries = {}
        for stock_info in analysis['stocks']:
            industry = stock_info['industry']
            if industry not in industries:
                industries[industry] = []
            industries[industry].append(stock_info)
        
        # Display stocks grouped by industry
        for industry, stocks in sorted(industries.items()):
            # Sort by profit score
            stocks_sorted = sorted(stocks, key=lambda x: x['profit_score'], reverse=True)
            
            html += f"<h3>🏭 {industry}</h3>"
            html += """
            <table>
                <tr>
                    <th>Stock</th>
                    <th>Weight</th>
                    <th>LTP</th>
                    <th>Day %</th>
                    <th>Week %</th>
                    <th>RSI</th>
                    <th>Profit Score</th>
                    <th>Target</th>
                    <th>Stop Loss</th>
                    <th>Upside %</th>
                    <th>Signals</th>
                    <th>Action</th>
                </tr>
            """
            
            for stock in stocks_sorted:
                rsi_class = "rsi-extreme" if stock['rsi'] < 25 else "rsi-low" if stock['rsi'] < 40 else "rsi-medium" if stock['rsi'] < 60 else "rsi-high"
                day_class = "positive" if stock['day_chg_pct'] > 0 else "negative"
                week_class = "positive" if stock['week_chg_pct'] and stock['week_chg_pct'] > 0 else "negative"
                
                profit_class = "profit-high" if stock['profit_score'] >= 70 else "profit-medium" if stock['profit_score'] >= 50 else "profit-low"
                
                # Action based on profit score and RSI
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
                    <td><strong>{stock['symbol']}</strong></td>
                    <td>{stock['weight']:.1f}%</td>
                    <td>₹{stock['ltp']:.2f}</td>
                    <td class="{day_class}">{stock['day_chg_pct']:+.2f}%</td>
                    <td class="{week_class}">{stock['week_chg_pct']:+.2f}%</td>
                    <td class="{rsi_class}">{stock['rsi']:.1f}</td>
                    <td class="{profit_class}"><strong>{stock['profit_score']}/100</strong></td>
                    <td class="positive">₹{stock['target_2']:.2f}</td>
                    <td class="negative">₹{stock['stop_loss']:.2f}</td>
                    <td class="positive">+{stock['upside_potential']:.1f}%</td>
                    <td>{signals_html}</td>
                    <td>{action}</td>
                </tr>
                """
            html += "</table>"
    
    html += """
        <div class="disclaimer">
            <strong>⚠️ Risk Disclaimer:</strong> This report is for informational and educational purposes only. 
            Past performance does not guarantee future results. All trading involves risk. 
            Please conduct your own research and consult with a certified financial advisor before making any investment decisions.
            The profit scores and targets are algorithmic calculations and should not be considered as guaranteed outcomes.
        </div>
        </div>
    </body>
    </html>
    """
    
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
        
        message_body = f"""🎯 *Market Alert - {ist_time}*

📊 *Bullish Sectors:* {len(bullish_sectors)}
"""
        if bullish_sectors:
            message_body += f"\n💡 *Top Sectors:*\n"
            for sector in bullish_sectors[:3]:
                message_body += f"• {sector}\n"
            
            if top_picks:
                message_body += f"\n🔥 *Top Profit Picks:*\n"
                for pick in top_picks[:5]:
                    message_body += f"• {pick['symbol']} (Score: {pick['score']}/100)\n"
        else:
            message_body += "\n⚠️ No bullish setups detected"
        
        message_body += f"\n📧 Full report sent via email"
        
        client.messages.create(
            from_=TWILIO_FROM,
            body=message_body,
            to=TWILIO_TO
        )
        
        print(f"{GREEN}✅ WhatsApp alert sent{RESET}")
        return True
    except Exception as e:
        print(f"{RED}❌ WhatsApp failed: {e}{RESET}")
        return False

def main():
    print(f"{CYAN}{'='*80}{RESET}")
    print(f"{CYAN}🎯 MARKET INTELLIGENCE SCANNER - Executive Edition{RESET}")
    print(f"{CYAN}{'='*80}{RESET}\n")
    
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    ist_time_str = now_ist.strftime("%Y-%m-%d %H:%M IST")
    
    print(f"{BLUE}⏰ Analysis Time: {ist_time_str}{RESET}\n")
    
    sector_analysis = {}
    bullish_sectors = []
    all_stocks = []
    
    # Analyze each sector
    for sector_name, config in sectors_config.items():
        print(f"{YELLOW}📊 Analyzing {sector_name}...{RESET}")
        
        # Fetch index data
        index_data = fetch_market_data(config['ticker'])
        if not index_data:
            print(f"{RED}   ❌ Failed to fetch index data{RESET}")
            continue
        
        # Calculate strength score
        strength_score = calculate_index_strength(index_data['rsi'], index_data['week_chg_pct'])
        
        # Determine if sector is bullish
        is_bullish = (index_data['rsi'] < 40) or (index_data['rsi'] < 50 and index_data['week_chg_pct'] and index_data['week_chg_pct'] > 2)
        
        if is_bullish:
            bullish_sectors.append(sector_name)
            print(f"{GREEN}   ✅ BULLISH - RSI: {index_data['rsi']:.1f}, Score: {strength_score}/100{RESET}")
        else:
            print(f"{RED}   ⏸️  Not Bullish - RSI: {index_data['rsi']:.1f}{RESET}")
        
        # Analyze stocks in this sector
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
                    all_stocks.append({
                        'symbol': stock_entry['symbol'],
                        'score': stock_entry['profit_score'],
                        'sector': sector_name
                    })
        
        sector_analysis[sector_name] = {
            'index_data': index_data,
            'strength_score': strength_score,
            'is_bullish': is_bullish,
            'stocks': stocks_data
        }
    
    # Get top profit picks
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
    
    # Generate HTML report
    html_report = generate_executive_html_report(sector_analysis, bullish_sectors, ist_time_str)
    
    # Email subject
    if bullish_sectors:
        subject = f"🎯 {len(bullish_sectors)} Bullish Sectors | Top Pick: {top_picks[0]['symbol']} | {ist_time_str}"
    else:
        subject = f"📊 Market Report | No Bullish Signals | {ist_time_str}"
    
    # Send notifications
    email_sent = send_email_report(html_report, subject)
    whatsapp_sent = send_whatsapp_alert(bullish_sectors, top_picks, ist_time_str)
    
    print(f"\n{CYAN}{'='*80}{RESET}")
    print(f"{GREEN}🎯 Report Generation Complete{RESET}")
    print(f"   Email: {'✅ Sent' if email_sent else '❌ Failed'}")
    print(f"   WhatsApp: {'✅ Sent' if whatsapp_sent else '⚠️ Skipped'}")
    print(f"{CYAN}{'='*80}{RESET}\n")

if __name__ == "__main__":
    main()
