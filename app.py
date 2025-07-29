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
from io import StringIO

app = Flask(__name__)
CORS(app)

# Cache for symbols to avoid frequent API calls
SYMBOLS_CACHE = {
    'data': [],
    'last_updated': None,
    'cache_duration': 24 * 60 * 60  # 24 hours in seconds
}

def fetch_nifty500_symbols():
    """Fetch latest Nifty 500 symbols from multiple sources"""
    try:
        print("🔄 Fetching latest Nifty 500 symbols...")
        
        # Headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Method 1: Try NSE official CSV
        try:
            print("📊 Trying NSE official CSV...")
            nse_url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
            response = requests.get(nse_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                csv_data = StringIO(response.text)
                df = pd.read_csv(csv_data)
                
                if 'Symbol' in df.columns:
                    symbols = df['Symbol'].dropna().unique().tolist()
                    # Clean symbols (remove any whitespace)
                    symbols = [symbol.strip() for symbol in symbols if symbol.strip()]
                    print(f"✅ NSE CSV: Fetched {len(symbols)} symbols")
                    return symbols
        except Exception as e:
            print(f"⚠️ NSE CSV failed: {e}")
        
        # Method 2: Try NSE API with session
        try:
            print("🌐 Trying NSE API...")
            session = requests.Session()
            session.headers.update(headers)
            
            # Get main page first to establish session
            session.get("https://www.nseindia.com", timeout=10)
            
            # Try different API endpoints
            api_urls = [
                "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
                "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY500%20MULTICAP%2050%3A25%3A25"
            ]
            
            for url in api_urls:
                try:
                    response = session.get(url, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        symbols = [item['symbol'] for item in data.get('data', [])]
                        if symbols:
                            symbols = [symbol.strip() for symbol in symbols if symbol.strip()]
                            print(f"✅ NSE API: Fetched {len(symbols)} symbols")
                            return symbols
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ NSE API failed: {e}")
        
        # Method 3: Try financial data providers
        try:
            print("📈 Trying financial data providers...")
            
            # You can add API calls to financial data providers here
            # Example: Alpha Vantage, Financial Modeling Prep, IEX Cloud, etc.
            
            # For now, try to get symbols from Yahoo Finance search
            # This is a more complex implementation that would require
            # scraping or using their unofficial API
            
            pass
            
        except Exception as e:
            print(f"⚠️ Financial data providers failed: {e}")
        
        # Method 4: User-defined symbol file (optional)
        try:
            print("📁 Checking for user-defined symbols file...")
            if os.path.exists('custom_symbols.txt'):
                with open('custom_symbols.txt', 'r') as f:
                    symbols = [line.strip() for line in f.readlines() if line.strip()]
                    if symbols:
                        print(f"✅ Custom file: Loaded {len(symbols)} symbols")
                        return symbols
        except Exception as e:
            print(f"⚠️ Custom symbols file failed: {e}")
        
        # If all methods fail, return empty list (no hardcoded fallback)
        print("❌ All symbol fetching methods failed")
        print("💡 Consider:")
        print("   1. Create 'custom_symbols.txt' with your symbols")
        print("   2. Check your internet connection")
        print("   3. NSE website might be temporarily unavailable")
        
        return []
        
    except Exception as e:
        print(f"❌ Error in fetch_nifty500_symbols: {e}")
        return []

def get_symbols():
    """Get symbols with caching mechanism"""
    current_time = time.time()
    
    # Check if cache is valid
    if (SYMBOLS_CACHE['data'] and 
        SYMBOLS_CACHE['last_updated'] and 
        (current_time - SYMBOLS_CACHE['last_updated']) < SYMBOLS_CACHE['cache_duration']):
        print(f"📋 Using cached symbols ({len(SYMBOLS_CACHE['data'])} symbols)")
        return SYMBOLS_CACHE['data']
    
    # Fetch fresh data
    symbols = fetch_nifty500_symbols()
    
    if symbols:
        SYMBOLS_CACHE['data'] = symbols
        SYMBOLS_CACHE['last_updated'] = current_time
        print(f"✅ Symbol cache updated with {len(symbols)} symbols")
        return symbols
    else:
        # Return cached data if available, even if expired
        if SYMBOLS_CACHE['data']:
            print(f"⚠️ Using expired cache ({len(SYMBOLS_CACHE['data'])} symbols) due to fetch failure")
            return SYMBOLS_CACHE['data']
        else:
            print("❌ No symbols available - neither fresh nor cached")
            print("💡 Solutions:")
            print("   1. Check internet connection")
            print("   2. Create 'custom_symbols.txt' with your symbol list")
            print("   3. Try refreshing symbols later")
            return []

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
    symbols = get_symbols()
    return jsonify({
        "message": "🚀 Stock Scanner API is running!",
        "version": "2.0.0",
        "total_stocks": len(symbols),
        "data_source": "Live NSE Data",
        "cache_status": {
            "symbols_cached": len(SYMBOLS_CACHE['data']),
            "last_updated": datetime.fromtimestamp(SYMBOLS_CACHE['last_updated']).isoformat() if SYMBOLS_CACHE['last_updated'] else None
        },
        "endpoints": {
            "/api/scan": "Get filtered stocks based on momentum criteria",
            "/api/health": "Health check endpoint",
            "/api/symbols": "Get list of all symbols",
            "/api/refresh-symbols": "Refresh symbol cache from NSE"
        },
        "usage": "GET /api/scan?rsi_min=25&rsi_max=45&volume_min=1.5"
    })

@app.route('/api/health')
def health():
    symbols = get_symbols()
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "stocks_available": len(symbols),
        "cache_age_hours": round((time.time() - SYMBOLS_CACHE['last_updated']) / 3600, 1) if SYMBOLS_CACHE['last_updated'] else None
    })

@app.route('/api/symbols')
def get_symbols_endpoint():
    symbols = get_symbols()
    return jsonify({
        "symbols": symbols,
        "total": len(symbols),
        "source": "NSE Live Data",
        "last_updated": datetime.fromtimestamp(SYMBOLS_CACHE['last_updated']).isoformat() if SYMBOLS_CACHE['last_updated'] else None
    })

@app.route('/api/refresh-symbols', methods=['POST'])
def refresh_symbols():
    """Force refresh of symbols cache"""
    try:
        print("🔄 Force refreshing symbols cache...")
        SYMBOLS_CACHE['last_updated'] = None  # Force refresh
        symbols = get_symbols()
        
        return jsonify({
            "success": True,
            "message": "Symbols cache refreshed successfully",
            "total_symbols": len(symbols),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/scan', methods=['GET'])
def scan_stocks():
    try:
        start_time = time.time()
        
        # Get current symbols
        symbols = get_symbols()
        if not symbols:
            return jsonify({
                "success": False,
                "error": "No symbols available. Please try refreshing symbols cache.",
                "timestamp": datetime.now().isoformat()
            }), 500
        
        # Get filter parameters from query string
        rsi_min = float(request.args.get('rsi_min', 25))
        rsi_max = float(request.args.get('rsi_max', 45))
        volume_min = float(request.args.get('volume_min', 1.5))
        adx_min = float(request.args.get('adx_min', 25))
        mfi_min = float(request.args.get('mfi_min', 30))
        cmf_min = float(request.args.get('cmf_min', 0.1))
        max_stocks = int(request.args.get('limit', 100))
        
        print(f"🔍 Starting scan with filters:")
        print(f"   RSI: {rsi_min}-{rsi_max}")
        print(f"   Volume: {volume_min}x")
        print(f"   ADX: {adx_min}+")
        print(f"   MFI: {mfi_min}+")
        print(f"   CMF: {cmf_min}+")
        print(f"   Total symbols to scan: {min(len(symbols), max_stocks)}")
        
        results = []
        processed = 0
        errors = 0
        
        # Process stocks with rate limiting
        for i, symbol in enumerate(symbols[:max_stocks]):
            try:
                # Add .NS suffix for Yahoo Finance
                yahoo_symbol = f"{symbol}.NS"
                
                # Fetch stock data using yfinance
                stock = yf.Ticker(yahoo_symbol)
                
                # Get 3 months of historical data
                hist = stock.history(period="3mo", interval="1d")
                
                if len(hist) < 20:
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
                
                # Apply scoring system
                score = calculate_score(current_rsi, current_volume_ratio, current_adx, current_mfi, current_cmf, 
                                      rsi_min, rsi_max, volume_min, adx_min, mfi_min, cmf_min)
                
                # Check if stock meets minimum criteria
                if score >= 6.0:
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
                    print(f"📊 Progress: {processed}/{min(len(symbols), max_stocks)} stocks, {len(results)} matches, {elapsed:.1f}s")
                    time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                errors += 1
                print(f"❌ Error processing {symbol}: {str(e)}")
                if errors > 20:  # Stop if too many errors
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
            "total_symbols_available": len(symbols),
            "filters_applied": {
                "rsi_range": f"{rsi_min}-{rsi_max}",
                "volume_min": volume_min,
                "adx_min": adx_min,
                "mfi_min": mfi_min,
                "cmf_min": cmf_min
            },
            "data_source": "NSE Live + Yahoo Finance",
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "summary": scan_summary,
            "results": results[:25],  # Top 25 results
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
        "available_endpoints": ["/", "/api/health", "/api/symbols", "/api/scan", "/api/refresh-symbols"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error",
        "message": "Please try again later"
    }), 500

if __name__ == '__main__':
    print("🚀 Starting Stock Scanner with Dynamic Symbol Fetching...")
    
    # Initialize symbols cache on startup
    symbols = get_symbols()
    print(f"📋 Loaded {len(symbols)} symbols for scanning")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
