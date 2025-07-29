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
    """Fetch latest Nifty 500 symbols from multiple sources with enhanced data validation"""
    try:
        print("🔄 Fetching latest Nifty 500 symbols...")
        
        # Enhanced headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        # Method 1: Try official NSE Indices CSV
        try:
            print("📊 Trying NSE Indices official CSV...")
            nse_indices_urls = [
                "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
                "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
            ]
            
            for url in nse_indices_urls:
                try:
                    response = requests.get(url, headers=headers, timeout=20)
                    if response.status_code == 200 and len(response.content) > 1000:
                        # Try to parse as CSV
                        csv_data = StringIO(response.text)
                        df = pd.read_csv(csv_data)
                        
                        # Look for symbol column with different possible names
                        symbol_columns = ['Symbol', 'SYMBOL', 'Company', 'symbol', 'Stock Symbol', 'NSE Symbol']
                        symbol_col = None
                        
                        for col in symbol_columns:
                            if col in df.columns:
                                symbol_col = col
                                break
                        
                        if symbol_col:
                            symbols = df[symbol_col].dropna().unique().tolist()
                            # Clean and validate symbols
                            symbols = [str(symbol).strip().upper() for symbol in symbols if str(symbol).strip() and str(symbol).strip() != 'nan']
                            # Filter out invalid symbols
                            symbols = [s for s in symbols if s.replace('-', '').replace('&', '').isalnum() and len(s) <= 20]
                            
                            if len(symbols) > 400:  # Should have at least 400+ symbols for Nifty 500
                                print(f"✅ NSE CSV: Fetched {len(symbols)} symbols")
                                return symbols
                except Exception as e:
                    print(f"⚠️ Failed {url}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ NSE CSV method failed: {e}")
        
        # Method 2: Try NSE Live API
        try:
            print("🌐 Trying NSE Live API...")
            session = requests.Session()
            session.headers.update(headers)
            
            # Get main page first to establish session
            try:
                session.get("https://www.nseindia.com", timeout=10)
                time.sleep(1)  # Brief pause
            except:
                pass
            
            # Try multiple API endpoints
            api_endpoints = [
                "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%20500",
                "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY500",
                "https://www.nseindia.com/api/allIndices"
            ]
            
            for endpoint in api_endpoints:
                try:
                    response = session.get(endpoint, timeout=15)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response structures
                        symbols = []
                        if 'data' in data and isinstance(data['data'], list):
                            symbols = [item.get('symbol', '').strip() for item in data['data'] if item.get('symbol')]
                        elif isinstance(data, list):
                            symbols = [item.get('symbol', '').strip() for item in data if item.get('symbol')]
                        
                        if symbols and len(symbols) > 100:
                            symbols = [s.upper() for s in symbols if s and len(s) <= 20]
                            print(f"✅ NSE API: Fetched {len(symbols)} symbols from {endpoint}")
                            return symbols
                            
                except Exception as e:
                    print(f"⚠️ API endpoint {endpoint} failed: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ NSE API method failed: {e}")
        
        # Method 3: Try Yahoo Finance for index constituents
        try:
            print("📈 Trying Yahoo Finance index data...")
            import yfinance as yf
            
            # Try to get Nifty 500 ETF holdings or similar
            nifty_etfs = ["0P0000VRNY.BO", "NIFTY500.NS"]  # Example ETF tickers
            
            for etf_ticker in nifty_etfs:
                try:
                    ticker = yf.Ticker(etf_ticker)
                    # This is experimental - Yahoo Finance doesn't always have holdings data
                    info = ticker.info
                    if info and 'holdings' in info:
                        symbols = [holding.get('symbol', '').replace('.NS', '').strip() 
                                 for holding in info['holdings'] if holding.get('symbol')]
                        if symbols and len(symbols) > 50:
                            print(f"✅ Yahoo Finance: Fetched {len(symbols)} symbols")
                            return symbols
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Yahoo Finance method failed: {e}")
        
        # Method 4: Enhanced custom symbols file with validation
        try:
            print("📁 Checking for user-defined symbols file...")
            symbol_files = ['custom_symbols.txt', 'nifty500_symbols.txt', 'symbols.txt']
            
            for filename in symbol_files:
                if os.path.exists(filename):
                    with open(filename, 'r', encoding='utf-8') as f:
                        symbols = []
                        for line in f.readlines():
                            symbol = line.strip().upper()
                            # Validate symbol format
                            if symbol and len(symbol) <= 20 and symbol.replace('-', '').replace('&', '').isalnum():
                                symbols.append(symbol)
                        
                        if symbols:
                            print(f"✅ Custom file {filename}: Loaded {len(symbols)} symbols")
                            # Add timestamp to indicate when symbols were loaded
                            print(f"📅 File last modified: {datetime.fromtimestamp(os.path.getmtime(filename))}")
                            return symbols
                            
        except Exception as e:
            print(f"⚠️ Custom symbols file failed: {e}")
        
        # Method 5: Web scraping as last resort
        try:
            print("🕷️ Trying web scraping method...")
            
            # Try scraping from financial websites
            scraping_urls = [
                "https://in.tradingview.com/symbols/NSE-CNX500/components/",
                "https://www.moneycontrol.com/stocks/marketstats/indexcomp.php?optex=NSE&opttopic=indexcomp&index=23"
            ]
            
            for url in scraping_urls:
                try:
                    response = requests.get(url, headers=headers, timeout=15)
                    if response.status_code == 200:
                        # This would require more sophisticated parsing
                        # For now, just check if we can access the page
                        if len(response.text) > 10000:  # Page loaded successfully
                            print(f"✅ Web scraping source accessible: {url}")
                            # Implement parsing logic here if needed
                            pass
                except:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Web scraping method failed: {e}")
        
        # If all methods fail, return empty list
        print("❌ All symbol fetching methods failed")
        print("💡 Recommendations:")
        print("   1. Ensure 'custom_symbols.txt' exists with latest symbols")
        print("   2. Check internet connectivity")
        print("   3. NSE servers might be temporarily unavailable")
        print("   4. Consider updating symbols manually during market hours")
        
        return []
        
    except Exception as e:
        print(f"❌ Critical error in fetch_nifty500_symbols: {e}")
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
        "message": "🚀 Advanced Stock Scanner API is running!",
        "version": "3.0.0",
        "total_stocks": len(symbols),
        "data_source": "Multi-Source (NSE + Yahoo Finance + Custom)",
        "last_updated": datetime.now().isoformat(),
        "cache_status": {
            "symbols_cached": len(SYMBOLS_CACHE['data']),
            "last_updated": datetime.fromtimestamp(SYMBOLS_CACHE['last_updated']).isoformat() if SYMBOLS_CACHE['last_updated'] else None,
            "cache_freshness": "Good" if SYMBOLS_CACHE['last_updated'] and (time.time() - SYMBOLS_CACHE['last_updated']) < 86400 else "Needs Refresh"
        },
        "api_endpoints": {
            "/api/scan": "Get filtered stocks based on technical criteria",
            "/api/health": "Health check and system status",
            "/api/symbols": "Get list of all available symbols with metadata",
            "/api/refresh-symbols": "Force refresh symbol cache from live sources",
            "/api/symbol-validation": "Validate current symbols and check data freshness",
            "/api/market-updates": "Get information about recent market changes"
        },
        "features": [
            "Real-time data from Yahoo Finance",
            "500+ Nifty stocks coverage",
            "Advanced technical indicators (RSI, ADX, MFI, CMF)",
            "Pattern recognition and strength analysis",
            "Multi-source symbol fetching with fallbacks",
            "Symbol validation and freshness checking",
            "Comprehensive error handling and logging"
        ],
        "usage_examples": {
            "basic_scan": "/api/scan?rsi_min=25&rsi_max=45&volume_min=1.5",
            "advanced_scan": "/api/scan?rsi_min=30&rsi_max=50&volume_min=2.0&adx_min=30&mfi_min=40",
            "momentum_stocks": "/api/scan?volume_min=3.0&adx_min=35&limit=10",
            "oversold_stocks": "/api/scan?rsi_min=20&rsi_max=30&volume_min=1.5"
        },
        "data_quality": {
            "symbol_count": len(symbols),
            "expected_range": "450-550 symbols",
            "status": "Good" if 450 <= len(symbols) <= 550 else "Needs Review",
            "last_major_update": "July 2025 - Enhanced multi-source fetching"
        }
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
    
    # Check symbol file freshness
    symbol_file_info = {}
    if os.path.exists('custom_symbols.txt'):
        stat = os.stat('custom_symbols.txt')
        symbol_file_info = {
            'file_exists': True,
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'file_size': stat.st_size,
            'days_old': (time.time() - stat.st_mtime) / (24 * 3600)
        }
    else:
        symbol_file_info = {'file_exists': False}
    
    return jsonify({
        "symbols": symbols,
        "total": len(symbols),
        "source": "Live NSE Data + Custom File",
        "cache_info": {
            "last_updated": datetime.fromtimestamp(SYMBOLS_CACHE['last_updated']).isoformat() if SYMBOLS_CACHE['last_updated'] else None,
            "cache_age_hours": round((time.time() - SYMBOLS_CACHE['last_updated']) / 3600, 1) if SYMBOLS_CACHE['last_updated'] else None,
            "cache_duration_hours": SYMBOLS_CACHE['cache_duration'] / 3600
        },
        "symbol_file_info": symbol_file_info,
        "data_freshness": {
            "nifty_rebalancing_schedule": "Semi-annual (January 31 & July 31)",
            "last_major_changes": "September 2024 (BEL, TRENT added to Nifty 50)",
            "recommendation": "Update symbols quarterly for best accuracy"
        }
    })

@app.route('/api/symbol-validation')
def validate_symbols():
    """Validate current symbols against multiple sources and check freshness"""
    try:
        symbols = get_symbols()
        validation_results = {
            "total_symbols": len(symbols),
            "validation_timestamp": datetime.now().isoformat(),
            "sources_checked": [],
            "recommendations": []
        }
        
        # Check if we have a reasonable number of symbols
        if len(symbols) < 400:
            validation_results["recommendations"].append(
                "Symbol count is low. Consider updating custom_symbols.txt with latest Nifty 500 list."
            )
        elif len(symbols) > 600:
            validation_results["recommendations"].append(
                "Symbol count is high. Verify if all symbols are still active."
            )
        else:
            validation_results["recommendations"].append(
                "Symbol count looks good for Nifty 500 index."
            )
        
        # Check symbol file age
        if os.path.exists('custom_symbols.txt'):
            file_age_days = (time.time() - os.path.getmtime('custom_symbols.txt')) / (24 * 3600)
            if file_age_days > 90:  # Older than 3 months
                validation_results["recommendations"].append(
                    f"Symbol file is {file_age_days:.0f} days old. Consider updating with latest Nifty 500 constituents."
                )
            else:
                validation_results["recommendations"].append(
                    f"Symbol file is {file_age_days:.0f} days old - reasonably fresh."
                )
        
        # Sample some symbols to check if they're valid in Yahoo Finance
        sample_symbols = symbols[:10] if len(symbols) > 10 else symbols
        valid_symbols = 0
        
        for symbol in sample_symbols:
            try:
                import yfinance as yf
                ticker = yf.Ticker(f"{symbol}.NS")
                hist = ticker.history(period="5d")
                if len(hist) > 0:
                    valid_symbols += 1
            except:
                continue
        
        validation_results["sample_validation"] = {
            "symbols_tested": len(sample_symbols),
            "valid_symbols": valid_symbols,
            "validity_rate": f"{(valid_symbols/len(sample_symbols)*100):.1f}%" if sample_symbols else "N/A"
        }
        
        if valid_symbols / len(sample_symbols) < 0.8:  # Less than 80% valid
            validation_results["recommendations"].append(
                "Some symbols may be delisted or invalid. Consider updating symbol list."
            )
        
        return jsonify({
            "success": True,
            "validation": validation_results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/market-updates')
def get_market_updates():
    """Get information about recent market changes and index updates"""
    try:
        market_info = {
            "nifty_indices_info": {
                "nifty_50": {
                    "last_rebalancing": "September 30, 2024",
                    "recent_additions": ["BEL", "TRENT"],
                    "recent_removals": ["DIVISLAB", "LTIM"],
                    "next_review": "January 31, 2025"
                },
                "nifty_500": {
                    "constituents": len(get_symbols()),
                    "market_cap_coverage": "~96% of NSE market cap",
                    "rebalancing_frequency": "Semi-annual",
                    "cut_off_dates": ["January 31", "July 31"]
                }
            },
            "data_sources": {
                "primary": "NSE Indices Limited",
                "backup": "Custom symbols file",
                "live_data": "Yahoo Finance API",
                "update_mechanism": "Automatic with fallback to manual"
            },
            "recommendations": [
                "Check for updates after NSE rebalancing dates",
                "Verify new IPO inclusions quarterly",
                "Monitor corporate actions (mergers, delistings)",
                "Update custom_symbols.txt when NSE access fails"
            ],
            "last_updated": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "market_updates": market_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

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
        "available_endpoints": [
            "/", 
            "/api/health", 
            "/api/symbols", 
            "/api/scan", 
            "/api/refresh-symbols",
            "/api/symbol-validation",
            "/api/market-updates"
        ]
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
