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
GMAIL_APP_PASS = os.getenv('GMAIL_APP_PASSWORD') # Matches your YAML secret name
RECEIVER_EMAIL = os.getenv('RECIPIENT_EMAIL', 'krishnateja.sapbasis@gmail.com')
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886')
TWILIO_TO = os.getenv('TWILIO_TO_NUMBER', 'whatsapp:+17372876924')

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
MAGENTA = "\033[35m"
ORANGE = "\033[33m"
RESET = "\033[0m"

# --- Enhanced Sector Config ---
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
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_moving_averages(data):
    return {
        'sma_20': data['Close'].rolling(window=20).mean().iloc[-1] if len(data) >= 20 else None,
        'sma_50': data['Close'].rolling(window=50).mean().iloc[-1] if len(data) >= 50 else None,
        'ema_9': data['Close'].ewm(span=9, adjust=False).mean().iloc[-1] if len(data) >= 9 else None,
        'ema_21': data['Close'].ewm(span=21, adjust=False).mean().iloc[-1] if len(data) >= 21 else None
    }

def calculate_profit_potential(ltp, high_52w, low_52w, rsi, trend):
    score = 0
    dist_from_high = ((high_52w - ltp) / ltp) * 100
    
    if rsi < 25: score += 35
    elif rsi < 30: score += 30
    elif rsi < 35: score += 25
    elif rsi < 40: score += 20
    
    if trend and trend > 0: score += 25
    elif trend and trend > -1: score += 15
    
    if dist_from_high > 30: score += 20
    elif dist_from_high > 20: score += 15
    elif dist_from_high > 10: score += 10
    
    range_position = (ltp - low_52w) / (high_52w - low_52w) * 100 if (high_52w - low_52w) > 0 else 50
    if range_position < 30: score += 20
    elif range_position < 50: score += 10
    
    target_2 = ltp * 1.10
    stop_loss = ltp * 0.95
    risk = ltp - stop_loss
    reward = target_2 - ltp
    risk_reward = reward / risk if risk > 0 else 0
    
    return {
        'score': min(score, 100),
        'target_1': ltp * 1.05,
        'target_2': target_2,
        'target_3': ltp * 1.15,
        'stop_loss': stop_loss,
        'risk_reward': risk_reward,
        'upside_potential': dist_from_high
    }

def detect_bullish_signals(data, rsi_val, ltp):
    signals = []
    if rsi_val < 25: signals.append("🔥 Extreme Oversold")
    elif rsi_val < 30: signals.append("🔥 RSI Oversold")
    elif rsi_val < 40: signals.append("📊 RSI Buy Zone")
    
    mas = calculate_moving_averages(data)
    if mas['ema_9'] and mas['ema_21']:
        if mas['ema_9'] > mas['ema_21'] and ltp > mas['ema_9']: signals.append("✅ Golden Cross")
        elif ltp > mas['ema_9']: signals.append("📈 Above EMA9")
    
    if len(data) >= 2:
        if data['Close'].iloc[-1] > data['Open'].iloc[-1] and data['Close'].iloc[-1] > data['Open'].iloc[-2]:
            signals.append("🕯️ Bullish Pattern")
    return signals

def calculate_index_strength(rsi, week_chg):
    score = 0
    if rsi < 25: score += 45
    elif rsi < 35: score += 35
    elif rsi < 50: score += 15
    if week_chg and week_chg > 0: score += 20
    return min(score, 100)

def fetch_market_data(ticker, period="3mo"):
    try:
        with suppress_stdout():
            data = yf.download(ticker, period=period, interval="1d", progress=False)
        if data.empty or len(data) < 15: return None
        
        ltp = float(data['Close'].iloc[-1])
        prev_close = float(data['Close'].iloc[-2])
        day_chg_pct = ((ltp - prev_close) / prev_close) * 100
        week_chg_pct = ((ltp - data['Close'].iloc[-6]) / data['Close'].iloc[-6]) * 100 if len(data) >= 6 else 0
        
        rsi_val = float(calculate_rsi(data['Close']).iloc[-1])
        mas = calculate_moving_averages(data)
        signals = detect_bullish_signals(data, rsi_val, ltp)
        
        high_52w = float(data['High'].max())
        low_52w = float(data['Low'].min())
        profit_metrics = calculate_profit_potential(ltp, high_52w, low_52w, rsi_val, week_chg_pct)
        
        return {
            "ltp": ltp, "day_chg_pct": day_chg_pct, "week_chg_pct": week_chg_pct,
            "rsi": rsi_val, "sma_20": mas['sma_20'], "ema_9": mas['ema_9'],
            "signals": signals, "high_52w": high_52w, "low_52w": low_52w,
            "profit_score": profit_metrics['score'], "target_1": profit_metrics['target_1'],
            "target_2": profit_metrics['target_2'], "stop_loss": profit_metrics['stop_loss'],
            "risk_reward": profit_metrics['risk_reward'], "upside_potential": profit_metrics['upside_potential']
        }
    except: return None

def generate_executive_html_report(sector_analysis, bullish_sectors, ist_time):
    # (HTML styling kept same as your provided code for visual consistency)
    html = f"""<html><head><style>
    body {{ font-family: sans-serif; background: #f4f7f6; padding: 20px; }}
    .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
    .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    th, td {{ padding: 12px; border: 1px solid #ddd; text-align: left; }}
    th {{ background: #f8f9fa; }}
    .positive {{ color: green; }}
    .negative {{ color: red; }}
    </style></head><body><div class="container">
    <div class="header"><h1>Market Report</h1><p>{ist_time}</p></div>
    <h3>Bullish Sectors: {len(bullish_sectors)}</h3>"""

    for sector in bullish_sectors:
        data = sector_analysis[sector]
        html += f"<h2>{sector}</h2><table><tr><th>Stock</th><th>LTP</th><th>RSI</th><th>Score</th></tr>"
        for stock in data['stocks']:
            html += f"<tr><td>{stock['symbol']}</td><td>{stock['ltp']:.2f}</td><td>{stock['rsi']:.1f}</td><td>{stock['profit_score']}</td></tr>"
        html += "</table>"
    html += "</div></body></html>"
    return html

def send_email_report(html_content, subject):
    if not GMAIL_USER or not GMAIL_APP_PASS: return False
    try:
        msg = MIMEMultipart(); msg['Subject'] = subject; msg['From'] = GMAIL_USER; msg['To'] = RECEIVER_EMAIL
        msg.attach(MIMEText(html_content, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls(); server.login(GMAIL_USER, GMAIL_APP_PASS); server.send_message(msg)
        print(f"{GREEN}✅ Email Sent{RESET}")
        return True
    except Exception as e: print(f"Email error: {e}"); return False

def send_whatsapp_alert(bullish_sectors, top_picks, ist_time):
    if not TWILIO_SID: return False
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        body = f"Nifty Report {ist_time}\nBullish: {', '.join(bullish_sectors)}\nTop Pick: {top_picks[0]['symbol'] if top_picks else 'None'}"
        client.messages.create(from_=TWILIO_FROM, body=body, to=TWILIO_TO)
        print(f"{GREEN}✅ WhatsApp Sent{RESET}")
    except Exception as e: print(f"WhatsApp error: {e}")

def main():
    print(f"{CYAN}🎯 Starting Market Scanner...{RESET}")
    ist = pytz.timezone("Asia/Kolkata")
    ist_time_str = datetime.now(ist).strftime("%Y-%m-%d %H:%M IST")
    
    sector_analysis = {}
    bullish_sectors = []
    all_stocks = []

    for sector_name, config in sectors_config.items():
        idx_data = fetch_market_data(config['ticker'])
        if not idx_data: continue
        
        strength_score = calculate_index_strength(idx_data['rsi'], idx_data['week_chg_pct'])
        is_bullish = idx_data['rsi'] < 45
        
        if is_bullish:
            bullish_sectors.append(sector_name)
            stocks_list = []
            for ticker, info in config['stocks'].items():
                s_data = fetch_market_data(ticker)
                if s_data:
                    entry = {'symbol': ticker.replace('.NS',''), 'weight': info['weight'], 'industry': info['industry'], **s_data}
                    stocks_list.append(entry)
                    all_stocks.append({'symbol': entry['symbol'], 'score': entry['profit_score']})
            
            sector_analysis[sector_name] = {'index_data': idx_data, 'stocks': stocks_list, 'strength_score': strength_score}

    print(f"{MAGENTA}📊 Bullish Sectors: {len(bullish_sectors)}{RESET}")
    
    # Corrected the lambda function here
    top_picks = sorted(all_stocks, key=lambda x: x['score'], reverse=True)
    
    report_html = generate_executive_html_report(sector_analysis, bullish_sectors, ist_time_str)
    send_email_report(report_html, f"NIFTY Market Intelligence - {ist_time_str}")
    send_whatsapp_alert(bullish_sectors, top_picks, ist_time_str)

if __name__ == "__main__":
    main()
