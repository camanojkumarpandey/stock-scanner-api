from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import ta
import time
import os

app = Flask(__name__)
CORS(app)

# Complete Nifty 500 symbol list (Top 100 for faster processing)
NIFTY_500_SYMBOLS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK', 'BAJFINANCE', 'LT',
    'ITC', 'SBIN', 'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'AXISBANK', 'TITAN', 'NESTLEIND',
    'ULTRACEMCO', 'WIPRO', 'SUNPHARMA', 'POWERGRID', 'NTPC', 'JSWSTEEL', 'TECHM', 'INDUSINDBK',
    'TATAMOTORS', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'BAJAJFINSV', 'HCLTECH', 'BRITANNIA',
    'SHREECEM', 'CIPLA', 'GODREJCP', 'DIVISLAB', 'ADANIENTS', 'TATACONSUM', 'ADANIPORTS',
    'APOLLOHOSP', 'DABUR', 'GRASIM', 'SBILIFE', 'PIDILITIND', 'MCDOWELL-N', 'BAJAJ-AUTO',
    'HEROMOTOCO', 'TORNTPHARM', 'DMART', 'MINDTREE', 'MPHASIS', 'PERSISTENT', 'COFORGE',
    'LTIM', 'OFSS', 'FEDERALBNK', 'RBLBANK', 'IDFCFIRSTB', 'BANDHANBNK', 'LUPIN', 'BIOCON',
    'CADILAHC', 'AUBANK', 'BANKBARODA', 'PNB', 'CANBK', 'IOCL', 'BPCL', 'ONGC', 'GAIL',
    'HINDALCO', 'VEDL', 'TATASTEEL', 'SAIL', 'NMDC', 'JINDALSTEL', 'JSPL', 'TATAPOWER',
    'ADANIGREEN', 'RECLTD', 'PFC', 'IRCTC', 'CONCOR', 'ZEEL', 'STAR', 'SUNTV', 'PVRINOX',
    'NAUKRI', 'ZOMATO', 'PAYTM', 'POLICYBZR', 'MOTHERSON', 'ESCORTS', 'MAHINDRA', 'ASHOKLEY',
    'BALKRISIND', 'MRF', 'APOLLOTYRE', 'CEAT'
]

def calculate_score(rsi, volume_ratio, adx, mfi, cmf, rsi_min, rsi_max, volume_min, adx_min, mfi_min, cmf_min):
    """Calculate a composite score based on technical indicators"""
    score = 0
    
    # RSI Score (2 points max)
    if rsi_min <= rsi <= rsi_max:
        score += 2
    elif abs(rsi - (rsi_min + rsi_max) / 2) <= 10:
        score += 1
    
    # Volume Score (2 points max)
    if volume_ratio >= volume_min:
        score += min(2, volume_ratio / volume_min)
    
    # ADX Score (2 points max)
    if adx >= adx_min:
        score += min(2, adx / adx_min)
    
    # MFI Score (2 points max)
    if mfi >= mfi_min:
        score += min(2, mfi / 50)  # Normalize to 0-2 scale
    
    # CMF Score (2 points max)
    if cmf >= cmf_min:
        score += min(2, cmf * 10)  # Scale CMF to 0-2 range
    
    return min(score, 10)  # Cap at 10 points

def identify_pattern(df):
    """Identify basic chart patterns"""
    if len(df) < 20:
        return "Insufficient Data"
    
    recent_close = df['Close'].iloc[-5:].values
    recent_high = df['High'].iloc[-5:].max()
    recent_low = df['Low'].iloc[-5:].min()
    
    # Simple pattern recognition
    if recent_close[-1] > recent_close[-2] > recent_close[-3]:
        return "Uptrend"
    elif recent_close[-1] < recent_close[-2] < recent_close[-3]:
        return "Downtrend"
    elif abs(recent_high - recent_low) / recent_close[-1] < 0.02:
        return "Consolidation"
    else:
        return "Sideways"

def calculate_strength(rsi, volume_ratio, adx, cmf):
    """Calculate overall strength rating"""
    strength_score = 0
    
    # RSI contribution
    if 30 <= rsi <= 70:
        strength_score += 1
    
    # Volume contribution
    if volume_ratio > 1.5:
        strength_score += 1
    
    # ADX contribution
    if adx > 25:
        strength_score += 1
    
    # CMF contribution
    if cmf > 0:
        strength_score += 1
    
    strength_map = {0: "Weak", 1: "Low", 2: "Medium", 3: "Strong", 4: "Very Strong"}
    return strength_map.get(strength_score, "Unknown")

@app.route('/')
def home():
    return jsonify({
        "message": "🚀 Stock Scanner API is running!",
        "version": "1.0.0",
        "total_stocks": len(NIFTY_500_SYMBOLS),
        "endpoints": {
            "/api/scan": "Get filtered stocks based on momentum criteria",
            "/api/health": "Health check endpoint",
            "/api/symbols": "Get list of all symbols"
        },
        "usage": "GET /api/scan?rsi_min=25&rsi_max=45&volume_min=1.5"
    })

@app.route('/api/health')
def health():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "stocks_available": len(NIFTY_500_SYMBOLS)
    })

@app.route('/api/symbols')
def get_symbols():
    return jsonify({
        "symbols": NIFTY_500_SYMBOLS,
        "total": len(NIFTY_500_SYMBOLS)
    })

@app.route('/api/scan', methods=['GET'])
def scan_stocks():
    try:
        start_time = time.time()
        
        # Get filter parameters from query string
        rsi_min = float(request.args.get('rsi_min', 25))
        rsi_max = float(request.args.get('rsi_max', 45))
        volume_min = float(request.args.get('volume_min', 1.5))
        adx_min = float(request.args.get('adx_min', 25))
        mfi_min = float(request.args.get('mfi_min', 30))
        cmf_min = float(request.args.get('cmf_min', 0.1))
        max_stocks = int(request.args.get('limit', 50))  # Reduced for faster processing
        
        print(f"🔍 Starting scan with filters:")
        print(f"   RSI: {rsi_min}-{rsi_max}")
        print(f"   Volume: {volume_min}x")
        print(f"   ADX: {adx_min}+")
        print(f"   MFI: {mfi_min}+")
        print(f"   CMF: {cmf_min}+")
        
        results = []
        processed = 0
        errors = 0
        
        # Process stocks with rate limiting
        for i, symbol in enumerate(NIFTY_500_SYMBOLS[:max_stocks]):
            try:
                # Add .NS suffix for Yahoo Finance
                yahoo_symbol = f"{symbol}.NS"
                
                # Fetch stock data using yfinance
                stock = yf.Ticker(yahoo_symbol)
                
                # Get 3 months of historical data
                hist = stock.history(period="3mo", interval="1d")
                
                if len(hist) < 20:
                    print(f"⚠️  {symbol}: Insufficient data")
                    continue
                
                # Get current info (with timeout)
                try:
                    info = stock.info
                except:
                    info = {"longName": f"{symbol} Ltd", "sector": "Unknown"}
                
                # Calculate technical indicators
                df = hist.copy()
                
                # RSI (14-period)
                df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
                
                # Volume ratio (current vs 20-day average)
                df['Volume_20MA'] = df['Volume'].rolling(window=20).mean()
                current_volume_ratio = df['Volume'].iloc[-1] / df['Volume_20MA'].iloc[-1] if df['Volume_20MA'].iloc[-1] > 0 else 1
                
                # Money Flow Index
                df['MFI'] = ta.volume.MFIIndicator(
                    high=df['High'], 
                    low=df['Low'], 
                    close=df['Close'], 
                    volume=df['Volume'],
                    window=14
                ).money_flow_index()
                
                # ADX (Average Directional Index)
                df['ADX'] = ta.trend.ADXIndicator(
                    high=df['High'], 
                    low=df['Low'], 
                    close=df['Close'],
                    window=14
                ).adx()
                
                # Chaikin Money Flow
                df['CMF'] = ta.volume.ChaikinMoneyFlowIndicator(
                    high=df['High'], 
                    low=df['Low'], 
                    close=df['Close'], 
                    volume=df['Volume'],
                    window=20
                ).chaikin_money_flow()
                
                # Get current values (handle NaN)
                current_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
                current_mfi = df['MFI'].iloc[-1] if not pd.isna(df['MFI'].iloc[-1]) else 50
                current_adx = df['ADX'].iloc[-1] if not pd.isna(df['ADX'].iloc[-1]) else 20
                current_cmf = df['CMF'].iloc[-1] if not pd.isna(df['CMF'].iloc[-1]) else 0
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
                change_percent = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
                
                # Apply scoring system (flexible criteria)
                score = calculate_score(current_rsi, current_volume_ratio, current_adx, current_mfi, current_cmf, 
                                      rsi_min, rsi_max, volume_min, adx_min, mfi_min, cmf_min)
                
                # Check if stock meets minimum criteria (60% of max score)
                if score >= 6.0:  # Out of 10 possible points
                    
                    pattern = identify_pattern(df)
                    strength = calculate_strength(current_rsi, current_volume_ratio, current_adx, current_cmf)
                    
                    stock_result = {
                        'symbol': symbol,
                        'name': info.get('longName', f"{symbol} Ltd")[:50],
                        'price': round(current_price, 2),
                        'change': round(current_price - prev_price, 2),
                        'changePercent': round(change_percent, 2),
                        'volume': int(df['Volume'].iloc[-1]),
                        'rsi': round(current_rsi, 1),
                        'volumeRatio': round(current_volume_ratio, 2),
                        'mfi': round(current_mfi, 1),
                        'adx': round(current_adx, 1),
                        'cmf': round(current_cmf, 3),
                        'pattern': pattern,
                        'strength': strength,
                        'score': round(score, 1),
                        'sector': info.get('sector', 'Unknown'),
                        'source': 'Yahoo Finance Live',
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    results.append(stock_result)
                    print(f"✅ {symbol}: Score {score:.1f} - {strength}")
                
                processed += 1
                
                # Progress update and rate limiting
                if processed % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"📊 Progress: {processed}/{max_stocks} stocks, {len(results)} matches, {elapsed:.1f}s")
                    time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                errors += 1
                print(f"❌ Error processing {symbol}: {str(e)}")
                if errors > 10:  # Stop if too many errors
                    print("🛑 Too many errors, stopping scan")
                    break
                continue
        
        # Sort results by score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        elapsed_time = time.time() - start_time
        
        scan_summary = {
            "scan_time": round(elapsed_time, 2),
            "stocks_processed": processed,
            "matches_found": len(results),
            "errors": errors,
            "filters_applied": {
                "rsi_range": f"{rsi_min}-{rsi_max}",
                "volume_min": volume_min,
                "adx_min": adx_min,
                "mfi_min": mfi_min,
                "cmf_min": cmf_min
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "summary": scan_summary,
            "results": results[:20],  # Limit to top 20 results
            "total_results": len(results)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/api/health", "/api/symbols", "/api/scan"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
