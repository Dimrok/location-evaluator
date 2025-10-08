# 🤖 LLM-Powered Location Analysis

## Overview
The API now includes AI-powered location insights that analyze your location scores compared to city-wide data and provide actionable recommendations.

## New Endpoint

### `/score-location-with-insights`
**POST** endpoint that returns both scores and AI-generated insights.

#### Request
```json
{
  "latitude": 44.837862,
  "longitude": -0.571754
}
```

#### Response
```json
{
  "latitude": 44.837862,
  "longitude": -0.571754,
  "city": "Bordeaux",
  "scores": {
    "attractiveness": 61.28,
    "competition": 65.39,
    "accessibility": 19.58,
    "suitability": 46.06,
    "global_score": 48.08
  },
  "features": {
    "restaurants": 317,
    "metro_station": 0,
    "bus_stop": 10,
    "walkability_score": 355,
    "shops_total": 679,
    "shops_shoes": 23,
    "parks": 3
  },
  "insights": "LOCATION ANALYSIS:\n\nThis location has a below average global score of 48.1 compared to the city average of 52.3...",
  "processing_time": 12.456
}
```

## Features

### 🧠 AI Insights Include:
- **City Comparison**: How the location ranks vs city average
- **Strengths & Weaknesses**: Detailed analysis of each score
- **Actionable Recommendations**: Specific advice for retail success
- **Context-Aware**: Uses actual city data for comparison

### 📊 Data Sources:
- **City CSVs**: All 5 cities (Paris, Lille, Bordeaux, Strasbourg, Toulouse)
- **Feature Descriptions**: Complete OSM documentation
- **Statistical Analysis**: Percentiles, averages, thresholds

### 🔄 Fallback System:
- If LLM fails, provides rule-based insights
- Always returns useful analysis
- No external dependencies required for basic functionality

## Setup

### Option 1: OpenAI API (Recommended)
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Option 2: Local Model
Replace the OpenAI client in `api/main.py` with your preferred local LLM.

### Option 3: Fallback Only
Works without any LLM setup - uses rule-based analysis.

## Usage Examples

### cURL
```bash
curl -X POST 'http://localhost:8000/score-location-with-insights' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'
```

### Python
```python
import requests

response = requests.post(
    'http://localhost:8000/score-location-with-insights',
    json={"latitude": 48.8625, "longitude": 2.3472}
)
data = response.json()
print(data['insights'])
```

### JavaScript
```javascript
fetch('http://localhost:8000/score-location-with-insights', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({latitude: 48.8625, longitude: 2.3472})
})
.then(response => response.json())
.then(data => console.log(data.insights));
```

## Performance
- **Processing Time**: ~10-15 seconds (includes OSM data extraction + LLM analysis)
- **Caching**: City data loaded once at startup
- **Reliability**: Fallback system ensures always returns insights

## Integration
Perfect for:
- **Frontend Dashboards**: Display both scores and insights
- **Mobile Apps**: Rich location analysis
- **Business Intelligence**: Automated location reports
- **Real Estate**: Property evaluation tools

---

**Ready for your hackathon demo! 🚀**
