# 🚀 Stock Scanner API

A powerful Flask-based REST API for scanning and filtering Indian stocks using technical indicators. Built with real-time data from Yahoo Finance and comprehensive Nifty 500 coverage.

## ✨ Features

- **Real-time Stock Data**: Live prices and technical indicators from Yahoo Finance
- **Advanced Filtering**: Filter stocks by RSI, Volume Ratio, ADX, MFI, and CMF
- **Technical Analysis**: Built-in calculations for momentum and trend indicators
- **Pattern Recognition**: Identify chart patterns and strength ratings
- **Nifty 500 Coverage**: Scan 500+ top Indian companies
- **RESTful API**: Clean JSON responses with comprehensive data
- **High Performance**: Optimized scanning with caching and rate limiting

## 🌐 Live Demo

**API Base URL**: https://stock-scanner-api.onrender.com

## 📚 API Endpoints

### 🏠 Health Check
```
GET /api/health
```
Returns API status and system information.

### 📊 Get Available Symbols
```
GET /api/symbols
```
Returns list of all available stock symbols for scanning.

### 🔍 Scan Stocks
```
GET /api/scan?rsi_min=30&rsi_max=50&volume_min=1.5&adx_min=25&limit=20
```

**Query Parameters:**
- `rsi_min` (default: 25) - Minimum RSI value
- `rsi_max` (default: 45) - Maximum RSI value  
- `volume_min` (default: 1.5) - Minimum volume ratio
- `adx_min` (default: 25) - Minimum ADX value
- `mfi_min` (default: 30) - Minimum Money Flow Index
- `cmf_min` (default: 0.1) - Minimum Chaikin Money Flow
- `limit` (default: 50) - Maximum stocks to scan

### 🔄 Refresh Symbols
```
POST /api/refresh-symbols
```
Force refresh the symbols cache from data sources.

## 📈 Sample Response

```json
{
  "success": true,
  "summary": {
    "scan_time": 45.2,
    "stocks_processed": 100,
    "matches_found": 12,
    "filters_applied": {
      "rsi_range": "30-50",
      "volume_min": 1.5,
      "adx_min": 25
    }
  },
  "results": [
    {
      "symbol": "RELIANCE",
      "name": "Reliance Industries Ltd",
      "price": 2450.75,
      "change": 25.30,
      "changePercent": 1.04,
      "rsi": 42.5,
      "volumeRatio": 2.1,
      "adx": 28.7,
      "mfi": 55.2,
      "cmf": 0.15,
      "pattern": "Uptrend",
      "strength": "Strong",
      "score": 8.5,
      "sector": "Energy"
    }
  ]
}
```

## 🛠️ Technical Indicators

| Indicator | Description | Usage |
|-----------|-------------|--------|
| **RSI** | Relative Strength Index (14-period) | Identify overbought/oversold conditions |
| **Volume Ratio** | Current vs 20-day average volume | Detect unusual trading activity |
| **ADX** | Average Directional Index | Measure trend strength |
| **MFI** | Money Flow Index | Volume-weighted momentum indicator |
| **CMF** | Chaikin Money Flow | Accumulation/distribution indicator |

## 🚀 Quick Start

### Using the API

```bash
# Check API health
curl https://stock-scanner-api.onrender.com/api/health

# Get available symbols
curl https://stock-scanner-api.onrender.com/api/symbols

# Scan for momentum stocks
curl "https://stock-scanner-api.onrender.com/api/scan?rsi_min=30&rsi_max=50&volume_min=2.0&limit=10"
```

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/camanojkumarpandey/stock-scanner-api.git
cd stock-scanner-api
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Run the application**
```bash
python app.py
```

4. **Test locally**
```bash
curl http://localhost:5000/api/health
```

## 🐳 Docker Deployment

```bash
# Build image
docker build -t stock-scanner-api .

# Run container
docker run -p 5000:5000 stock-scanner-api
```

## ☁️ Cloud Deployment

### Render (Recommended)
1. Connect your GitHub repository to Render
2. Select "Web Service" 
3. Use auto-detected Python environment
4. Deploy automatically

### Heroku
```bash
heroku create your-app-name
git push heroku main
```

## 📊 Supported Stocks

- **Nifty 500 Companies**: Complete coverage of top Indian stocks
- **All Sectors**: Banking, IT, Pharma, Auto, Energy, FMCG, etc.
- **Market Caps**: Large-cap, mid-cap, and small-cap stocks
- **Live Data**: Real-time prices and volumes from Yahoo Finance

## 🔧 Configuration

### Environment Variables
- `PORT` - Server port (default: 5000)
- `FLASK_ENV` - Environment mode (production/development)

### Custom Symbols
Add your own symbols by editing `custom_symbols.txt`:
```
RELIANCE
TCS
HDFCBANK
INFY
...
```

## 📈 Use Cases

- **Day Trading**: Find momentum stocks for intraday trading
- **Swing Trading**: Identify stocks in strong trends
- **Portfolio Screening**: Filter stocks by technical criteria
- **Research**: Analyze market conditions across sectors
- **Algorithmic Trading**: Integrate with trading systems

## 🛡️ Rate Limiting

- Automatic rate limiting to prevent API abuse
- Caching mechanism for symbol data (24-hour cache)
- Optimized scanning with progress tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/new-feature`)
5. Create a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Yahoo Finance** for providing free stock data API
- **NSE India** for market indices and stock listings
- **TA-Lib** for technical analysis indicators
- **Flask** for the web framework

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/camanojkumarpandey/stock-scanner-api/issues)
- **Email**: [your-email@example.com]
- **LinkedIn**: [Your LinkedIn Profile]

## 📊 API Status

![API Status](https://img.shields.io/website?url=https%3A//stock-scanner-api.onrender.com/api/health)
![Python](https://img.shields.io/badge/python-3.9+-blue.svg)
![Flask](https://img.shields.io/badge/flask-2.3+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

---

⭐ **Star this repository if you find it useful!**

Built with ❤️ for the Indian stock market community.
