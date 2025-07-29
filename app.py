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

def load_symbols_from_file():
    """Load symbols from custom file - fastest method"""
    try:
        symbol_files = ['custom_symbols.txt', 'nifty500_symbols.txt', 'symbols.txt']
        
        for filename in symbol_files:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    symbols = []
                    for line in f.readlines():
                        symbol = line.strip().upper()
                        # Skip comments and empty lines
                        if symbol and not symbol.startswith('#') and len(symbol) <= 20:
                            symbols.append(symbol)
                    
                    if symbols:
                        print(f"✅ Loaded {len(symbols)} symbols from {filename}")
                        return symbols
        
        # If no file found, return a minimal working set
        print("⚠️ No symbol file found, using minimal set")
        return [
            'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'HINDUNILVR', 'ICICIBANK', 
            'BAJFINANCE', 'LT', 'ITC', 'SBIN', 'BHARTIARTL', 'ASIANPAINT',
            'MARUTI', 'AXISBANK', 'TITAN', 'NESTLEIND', 'ULTRACEMCO', 'WIPRO',
            'SUNPHARMA', 'POWERGRID', 'NTPC', 'JSWSTEEL', 'TECHM', 'INDUSINDBK'
        ]
                        
    except Exception as e:
        print(f"❌ Error loading symbols: {e}")
        return []

def get_symbols():
    """Get symbols with lazy loading"""
    current_time = time.time()
    
    # Check if cache is valid
    if (SYMBOLS_CACHE['data'] and 
        SYMBOLS_CACHE['last_updated'] and 
        (current_time - SYMBOLS_CACHE['last_updated']) < SYMBOLS_CACHE['cache_duration']):
        return SYMBOLS_CACHE['data']
    
    # Load symbols from file (fast operation)
    symbols = load_symbols_from_file()
    
    if symbols:
        SYMBOLS_CACHE['data'] = symbols
        SYMBOLS_CACHE['last_updated'] = current_time
        return symbols
    else:
        # Return cached data if available
        if SYMBOLS_CACHE['data']:
            return SYMBOLS_CACHE['data']
        else:
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
        score += min(2, mfi / 50)
    
    # CMF Score (2 points max)
    if cmf >= cmf_min:
        score += min(2, cmf * 10)
    
    return min(score, 10)

def identify_pattern(df):
    """Identify basic chart patterns"""
    try:
        if len(df) < 5:
            return "Insufficient Data"
        
        recent_close = df['Close'].iloc[-5:].values
        
        if len(recent_close) >= 3:
            if recent_close[-1] > recent_close[-2] > recent_close[-3]:
                return "Uptrend"
            elif recent_close[-1] < recent_close[-2] < recent_close[-3]:
                return "Downtrend"
            else:
                return "Sideways"
        else:
            return "Sideways"
    except:
        return "Unknown"

def calculate_strength(rsi, volume_ratio, adx, cmf):
    """Calculate overall strength rating"""
    try:
        strength_score = 0
        
        if 30 <= rsi <= 70:
            strength_score += 1
        if volume_ratio > 1.5:
            strength_score += 1
        if adx > 25:
            strength_score += 1
        if cmf > 0:
            strength_score += 1
        
        strength_map = {0: "Weak", 1: "Low", 2: "Medium", 3: "Strong", 4: "Very Strong"}
        return strength_map.get(strength_score, "Unknown")
    except:
        return "Unknown"

@app.route('/')
def home():
    symbols = get_symbols()
    return jsonify({
        "message": "🚀 Stock Scanner API is running!",
        "version": "3.1.0",
        "total_stocks": len(symbols),
        "status": "Healthy",
        "api_endpoints": {
            "/api/scan": "Scan stocks with technical filters",
            "/api/health": "Health check",
            "/api/symbols": "Get available symbols",
            "/api/symbol-count-analysis": "Analyze symbol count"
        },
        "usage": "/api/scan?rsi_min=25&rsi_max=45&volume_min=1.5&limit=20"
    })

@app.route('/api/health')
def health():
    symbols = get_symbols()
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "stocks_available": len(symbols),
        "memory_usage": "optimized",
        "cache_status": "active" if SYMBOLS_CACHE['data'] else "empty"
    })

@app.route('/api/symbols')
def get_symbols_endpoint():
    symbols = get_symbols()
    
    file_info = "No file found"
    if os.path.exists('custom_symbols.txt'):
        stat = os.stat('custom_symbols.txt')
        file_info = f"File exists, {stat.st_size} bytes"
    
    return jsonify({
        "symbols": symbols[:50],  # Return first 50 for quick response
        "total": len(symbols),
        "file_info": file_info,
        "note": "Showing first 50 symbols. Full list available for scanning."
    })

@app.route('/api/symbol-count-analysis')
def symbol_count_analysis():
    """Analyze symbol count"""
    try:
        symbols = get_symbols()
        current_count = len(symbols)
        
        if current_count >= 400:
            status = "Excellent"
            message = "Great symbol coverage for Nifty 500 scanning"
        elif current_count >= 200:
            status = "Good"
            message = "Good coverage of major Indian stocks"
        elif current_count >= 50:
            status = "Basic"
            message = "Basic coverage - suitable for testing"
        else:
            status = "Minimal"
            message = "Very limited symbols - needs update"
        
        return jsonify({
            "success": True,
            "analysis": {
                "current_count": current_count,
                "status": status,
                "message": message,
                "explanation": "Symbol count varies based on available data sources and market conditions",
                "recommendation": "Add custom_symbols.txt file for complete Nifty 500 coverage"
            }
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/scan', methods=['GET'])
def scan_stocks():
    try:
        start_time = time.time()
        
        # Get symbols (fast file-based loading)
        symbols = get_symbols()
        if not symbols:
            return jsonify({
                "success": False,
                "error": "No symbols available. Please add custom_symbols.txt file."
            }), 400
        
        # Get parameters with defaults
        rsi_min = float(request.args.get('rsi_min', 25))
        rsi_max = float(request.args.get('rsi_max', 45))
        volume_min = float(request.args.get('volume_min', 1.5))
        adx_min = float(request.args.get('adx_min', 25))
        mfi_min = float(request.args.get('mfi_min', 30))
        cmf_min = float(request.args.get('cmf_min', 0.1))
        max_stocks = min(int(request.args.get('limit', 50)), 100)  # Cap at 100 for performance
        
        print(f"🔍 Scanning {max_stocks} stocks with RSI {rsi_min}-{rsi_max}")
        
        results = []
        processed = 0
        errors = 0
        
        # Process stocks with timeout protection
        for symbol in symbols[:max_stocks]:
            try:
                # Timeout check - stop if taking too long
                if time.time() - start_time > 25:  # 25 second limit
                    print("⏰ Timeout reached, stopping scan")
                    break
                
                yahoo_symbol = f"{symbol}.NS"
                stock = yf.Ticker(yahoo_symbol)
                
                # Get recent data only (faster)
                hist = stock.history(period="2mo", interval="1d")
                
                if len(hist) < 15:
                    continue
                
                # Calculate indicators efficiently
                df = hist.copy()
                
                # Essential indicators only
                df['RSI'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
                df['Volume_MA'] = df['Volume'].rolling(window=10).mean()
                
                # Current values
                current_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
                current_price = df['Close'].iloc[-1]
                prev_price = df['Close'].iloc[-2] if len(df) > 1 else current_price
                volume_ratio = df['Volume'].iloc[-1] / df['Volume_MA'].iloc[-1] if df['Volume_MA'].iloc[-1] > 0 else 1
                
                # Quick scoring (simplified for speed)
                score = 0
                if rsi_min <= current_rsi <= rsi_max:
                    score += 3
                if volume_ratio >= volume_min:
                    score += 2
                
                # Only include if meets basic criteria
                if score >= 3:
                    change_percent = ((current_price - prev_price) / prev_price) * 100 if prev_price > 0 else 0
                    
                    results.append({
                        'symbol': symbol,
                        'price': round(current_price, 2),
                        'changePercent': round(change_percent, 2),
                        'rsi': round(current_rsi, 1),
                        'volumeRatio': round(volume_ratio, 2),
                        'score': round(score, 1),
                        'pattern': 'Uptrend' if change_percent > 0 else 'Downtrend',
                        'strength': 'Strong' if score > 4 else 'Medium'
                    })
                    
                    print(f"✅ {symbol}: ₹{current_price:.1f} RSI:{current_rsi:.1f}")
                
                processed += 1
                
                # Brief pause every 10 stocks
                if processed % 10 == 0:
                    time.sleep(0.2)
                
            except Exception as e:
                errors += 1
                if errors > 10:
                    break
                continue
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        elapsed_time = time.time() - start_time
        
        return jsonify({
            "success": True,
            "summary": {
                "scan_time": round(elapsed_time, 1),
                "stocks_processed": processed,
                "matches_found": len(results),
                "errors": errors,
                "filters": f"RSI {rsi_min}-{rsi_max}, Volume {volume_min}x"
            },
            "results": results[:20]  # Top 20 results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found",
        "available": ["/", "/api/health", "/api/symbols", "/api/scan", "/api/symbol-count-analysis"]
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "error": "Internal server error"
    }), 500

if __name__ == '__main__':
    print("🚀 Starting Stock Scanner (Optimized)...")
    
    # Quick symbol check without heavy operations
    symbols = get_symbols()
    print(f"📋 Ready with {len(symbols)} symbols")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
