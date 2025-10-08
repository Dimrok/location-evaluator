# 🎯 Location Scoring API - Frontend Integration Examples

This directory contains working examples showing how to integrate with the Location Scoring API from different platforms.

## 📁 Files

- **`frontend_example.html`** - Complete HTML/JavaScript example with UI
- **`python_example.py`** - Python integration example with demos
- **`README.md`** - This file

## 🚀 Quick Start

### 1. Start the API
```bash
./run_api.sh
```

### 2. Test the Examples

#### HTML/JavaScript Example
```bash
# Open in browser
open frontend_example.html
# or
firefox frontend_example.html
```

#### Python Example
```bash
python3 python_example.py
```

## 🌐 HTML/JavaScript Example

**Features:**
- ✅ Interactive web interface
- ✅ Two-step approach (fast scores + AI insights)
- ✅ One-step approach (complete analysis)
- ✅ Preset test locations
- ✅ Real-time status updates
- ✅ Error handling
- ✅ Responsive design

**Usage:**
1. Open `frontend_example.html` in your browser
2. Enter coordinates or click preset locations
3. Click "Get Scores" for fast analysis
4. Click "Get AI Insights" for detailed analysis
5. Or click "Complete Analysis" for everything at once

## 🐍 Python Example

**Features:**
- ✅ Two-step approach demo
- ✅ One-step approach demo
- ✅ Batch analysis demo
- ✅ Error handling
- ✅ Pretty printing
- ✅ Performance timing

**Usage:**
```bash
python3 python_example.py
```

**Integration in your code:**
```python
from python_example import LocationScoringAPI

api = LocationScoringAPI()

# Get scores only (fast)
scores = api.get_scores(48.861943, 2.365386)

# Get AI insights
insights = api.get_insights(48.861943, 2.365386, "Paris", scores['scores'], scores['features'])

# Or get everything at once
complete = api.get_complete_analysis(48.861943, 2.365386)
```

## 📊 API Endpoints

### 1. Basic Scoring (Fast)
```bash
POST /score-location
```
- **Time:** ~0.4s
- **Input:** `{"latitude": 48.861943, "longitude": 2.365386}`
- **Output:** Scores + Features

### 2. AI Insights Only
```bash
POST /generate-insights
```
- **Time:** ~4.2s
- **Input:** Location data from step 1
- **Output:** AI analysis + recommendations

### 3. Complete Analysis
```bash
POST /score-location-with-insights
```
- **Time:** ~21s
- **Input:** `{"latitude": 48.861943, "longitude": 2.365386}`
- **Output:** Everything + AI insights

## 🎯 Integration Tips

### For Web Frontend:
- Use **two-step approach** for better UX
- Show scores immediately (~0.4s)
- Load AI insights on demand (~4.2s)
- Add loading states and error handling

### For Mobile Apps:
- Cache results to avoid repeated calls
- Use background processing for AI insights
- Implement offline fallbacks if possible

### For Backend Services:
- Batch process multiple locations
- Implement rate limiting
- Cache frequently requested locations

## 🔧 Customization

### Modify API Base URL
```javascript
// In frontend_example.html
const API_BASE = 'http://your-api-server:8000';
```

```python
# In python_example.py
api = LocationScoringAPI(base_url="http://your-api-server:8000")
```

### Add New Features
- Modify the UI in `frontend_example.html`
- Add new demo functions in `python_example.py`
- Extend the `LocationScoringAPI` class

## 🐛 Troubleshooting

### Common Issues:

1. **API not responding:**
   ```bash
   # Check if API is running
   curl http://localhost:8000/health
   ```

2. **CORS errors in browser:**
   - Make sure API is running on localhost:8000
   - Check browser console for errors

3. **Python requests errors:**
   - Install requests: `pip install requests`
   - Check network connectivity

4. **Slow responses:**
   - First request is always slower (OSM data caching)
   - Use two-step approach for better performance

## 📞 Support

If you encounter issues:
1. Check the API logs: `docker logs location-scoring-api`
2. Verify API is running: `curl http://localhost:8000/health`
3. Test with curl commands from the main README
4. Check the examples work with preset locations

## 🎉 Ready to Integrate!

These examples provide everything your teammate needs to integrate the Location Scoring API into any frontend or backend application. The code is production-ready and includes proper error handling, performance optimization, and user experience considerations.

**Happy coding!** 🚀
