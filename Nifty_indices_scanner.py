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
GMAIL_APP_PASS = os.getenv('GMAIL_APP_PASSWORD') 
RECEIVER_EMAIL = os.getenv('RECIPIENT_EMAIL', 'krishnateja.sapbasis@gmail.com')
TWILIO_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM = os.getenv('TWILIO_FROM_NUMBER', 'whatsapp:+14155238886')
TWILIO_TO = os.getenv('TWILIO_TO_NUMBER', 'whatsapp:+17372876924')

@contextlib.contextmanager
def suppress_stdout():
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        yield

# --- ANSI COLORS ---
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BLUE = "\033[94m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

sectors_config = {
    "Nifty Bank": {"ticker": "^NSEBANK", "stocks": {"HDFCBANK.NS": {"weight": 28.1, "industry": "Private Bank"}, "ICICIBANK.NS": {"weight": 19.3, "industry": "Private Bank"}, "SBIN.NS": {"weight": 18.9, "industry": "PSU Bank"}}},
    "Nifty IT": {"ticker": "^CNXIT", "stocks": {"INFY.NS": {"weight": 27.0, "industry": "IT Services"}, "TCS.NS": {"weight": 22.0, "industry": "IT Services"}}},
    "Nifty Pharma": {"ticker": "^CNXPHARMA", "stocks": {"SUNPHARMA.NS": {"weight": 21.3, "industry": "Pharma"}, "DIVISLAB.NS": {"weight": 9.7, "industry": "Pharma API"}}},
    "Nifty Realty": {"ticker": "^CNXREALTY", "stocks": {"DLF.NS": {"weight": 21.1, "industry": "Real Estate"}, "LODHA.NS": {"weight": 14.2, "industry": "Real Estate"}}},
    "Nifty Metal": {"ticker": "^CNXMETAL", "stocks": {"TATASTEEL.NS": {"weight": 17.0, "industry": "Steel"}, "HINDALCO.NS": {"weight": 15.0, "industry": "Aluminum"}}},
    "Nifty Auto": {"ticker": "^CNXAUTO", "stocks": {"MARUTI.NS": {"weight": 20.0, "industry": "Auto"}, "TATAMOTORS.NS": {"weight": 15.0, "industry": "Auto"}}}
}

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_profit_potential(ltp, high_52w, low_52w, rsi):
    score = 0
    if rsi < 30: score += 40
    elif rsi < 45: score += 20
    dist_from_high = ((high_52w - ltp) / ltp) * 100
    if dist_from_high > 15: score += 30
    return {"score": min(score, 100), "target": ltp * 1.10, "stop_loss": ltp * 0.95}

def fetch_market_data(ticker):
    try:
        with suppress_stdout():
            data = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if data.empty: return None
        ltp = float(data['Close'].iloc[-1])
        rsi_val = float(calculate_rsi(data['Close']).iloc[-1])
        return {
            "ltp": ltp, "rsi": rsi_val, "high_52w": float(data['High'].max()),
            "low_52w": float(data['Low'].min()), "day_chg": ((ltp - float(data['Close'].iloc[-2]))/float(data['Close'].iloc[-2]))*100
        }
    except: return None

def generate_executive_html_report(sector_analysis, ist_time):
    html = f"""<html><body style="font-family: Arial; padding: 20px; background: #f4f4f4;">
    <div style="background: white; padding: 20px; border-radius: 10px;">
    <h1 style="color: #2c3e50; text-align: center;">Market Intelligence Report</h1>
    <p style="text-align: center; color: #7f8c8d;">{ist_time}</p><hr>"""
    
    for sector, data in sector_analysis.items():
        rsi = data['index']['rsi']
        status = "BULLISH" if rsi < 45 else "NEUTRAL" if rsi < 65 else "BEARISH"
        color = "green" if status == "BULLISH" else "orange" if status == "NEUTRAL" else "red"
        
        html += f"""<h2 style="color: {color};">{sector} ({status} - RSI: {rsi:.1f})</h2>
        <table border="1" style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        <tr style="background: #ecf0f1;"><th>Stock</th><th>LTP</th><th>RSI</th><th>Score</th><th>Target</th></tr>"""
        
        for s in data['stocks']:
            html += f"<tr><td>{s['symbol']}</td><td>₹{s['ltp']:.2f}</td><td>{s['rsi']:.1f}</td><td>{s['score']}/100</td><td>₹{s['target']:.2f}</td></tr>"
        html += "</table>"
    
    html += "</div></body></html>"
    return html

def main():
    print(f"{CYAN}🚀 Initializing Nifty Scanner...{RESET}")
    ist = pytz.timezone("Asia/Kolkata")
    ist_time_str = datetime.now(ist).strftime("%Y-%m-%d %H:%M IST")
    
    sector_analysis = {}
    all_stocks = []

    for sector_name, config in sectors_config.items():
        print(f"{YELLOW}Scanning {sector_name}...{RESET}")
        idx = fetch_market_data(config['ticker'])
        if not idx: continue
        
        stocks_data = []
        for ticker, info in config['stocks'].items():
            s = fetch_market_data(ticker)
            if s:
                p = calculate_profit_potential(s['ltp'], s['high_52w'], s['low_52w'], s['rsi'])
                entry = {"symbol": ticker.replace(".NS",""), "ltp": s['ltp'], "rsi": s['rsi'], **p}
                stocks_data.append(entry)
                all_stocks.append(entry)
        
        sector_analysis[sector_name] = {"index": idx, "stocks": stocks_data}

    # Formatting and Sending
    top_picks = sorted(all_stocks, key=lambda x: x['score'], reverse=True)
    report_html = generate_executive_html_report(sector_analysis, ist_time_str)
    
    # Send Email
    try:
        msg = MIMEMultipart()
        msg['Subject'] = f"Market Report - {ist_time_str}"
        msg['From'] = GMAIL_USER
        msg['To'] = RECEIVER_EMAIL
        msg.attach(MIMEText(report_html, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_APP_PASS)
            server.send_message(msg)
        print(f"{GREEN}✅ Email Sent!{RESET}")
    except Exception as e:
        print(f"{RED}❌ Email Error: {e}{RESET}")

    # WhatsApp via Twilio
    if TWILIO_SID:
        try:
            client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(from_=TWILIO_FROM, body=f"Market Scan Complete. Top Pick: {top_picks[0]['symbol'] if top_picks else 'N/A'}", to=TWILIO_TO)
            print(f"{GREEN}✅ WhatsApp Sent!{RESET}")
        except: pass

if __name__ == "__main__":
    main()
