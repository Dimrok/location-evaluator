# 🚀 Location Scoring API - Quick Start Guide

## 🏃‍♂️ **GET STARTED IN 30 SECONDS**

### 1. **Start the API**
```bash
./run_api.sh
```
✅ API will be running on `http://localhost:8000`

### 2. **Test Basic Scoring (No AI)**
```bash
curl -X POST 'http://localhost:8000/score-location' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'
```

### 3. **Test AI Insights**
```bash
curl -X POST 'http://localhost:8000/score-location-with-insights' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'
```

---

## 📍 **TEST LOCATIONS**

### **Paris Locations:**
```json
{"latitude": 48.8625, "longitude": 2.3472}   // Châtelet
{"latitude": 48.8566, "longitude": 2.3522}   // Notre-Dame
{"latitude": 48.8842, "longitude": 2.3387}   // Montmartre
```

### **Bordeaux Locations:**
```json
{"latitude": 44.8379, "longitude": -0.5718}  // City Center
{"latitude": 44.8400, "longitude": -0.5800}  // Shopping Area
```

### **Other Cities:**
```json
{"latitude": 50.6387, "longitude": 3.0624}   // Lille
{"latitude": 48.5828, "longitude": 7.7514}   // Strasbourg
{"latitude": 43.6021, "longitude": 1.4470}   // Toulouse
```

---

## 🔧 **API ENDPOINTS**

### **1. Basic Scoring (Fast, No AI)**
```bash
POST /score-location
```
**Input:**
```json
{
  "latitude": 48.8625,
  "longitude": 2.3472,
  "radius": 500
}
```
**Output:** Scores + Features + Processing Time (~0.2s)

### **2. AI Insights Only**
```bash
POST /generate-insights
```
**Input:** Location data from step 1 + city name
**Output:** AI analysis + recommendations (~2.1s)

### **3. Complete Analysis (Two-Step Internally)**
```bash
POST /score-location-with-insights
```
**Input:** Just coordinates
**Output:** Everything + AI insights (~146s - uses both endpoints internally)

---

## 📊 **UNDERSTANDING THE SCORES**

### **Scoring Metrics (0-100 scale):**
- **🎯 Attractiveness:** Commercial environment quality
- **🏪 Competition:** Retail density and competition level  
- **🚇 Accessibility:** Public transport and walkability
- **👟 Suitability:** Overall retail potential
- **🌍 Global Score:** Average of all 4 scores

### **Score Interpretation:**
- **80-100:** Excellent location
- **60-79:** Good location  
- **40-59:** Moderate location
- **20-39:** Poor location
- **0-19:** Very poor location

---

## 🎯 **COMMON USE CASES**

### **Real Estate Analysis (Fast):**
```bash
# Quick scoring for property evaluation (~0.2s)
curl -X POST 'http://localhost:8000/score-location' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'
```

### **Retail Planning (Two-Step - Recommended):**
```bash
# Step 1: Get scores (~0.2s)
curl -X POST 'http://localhost:8000/score-location' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'

# Step 2: Get AI insights (~2.1s)
curl -X POST 'http://localhost:8000/generate-insights' \
  -H 'Content-Type: application/json' \
  -d '{ /* data from step 1 */ }'
```

### **Retail Planning (One-Step - Convenient):**
```bash
# Complete analysis with AI recommendations (~146s)
curl -X POST 'http://localhost:8000/score-location-with-insights' \
  -H 'Content-Type: application/json' \
  -d '{"latitude": 48.8625, "longitude": 2.3472}'
```

### **Batch Analysis:**
```bash
# Process multiple locations efficiently
for lat in 48.8625 48.8566 48.8842; do
  curl -X POST 'http://localhost:8000/score-location' \
    -H 'Content-Type: application/json' \
    -d "{\"latitude\": $lat, \"longitude\": 2.3472}"
done
```

---

## 🔍 **API DOCUMENTATION**

### **Interactive Docs:**
Visit `http://localhost:8000/docs` for:
- Complete API documentation
- Interactive testing interface
- Request/response examples
- Schema definitions

### **Health Check:**
```bash
curl http://localhost:8000/health
```

---

## ⚡ **PERFORMANCE TIPS**

### **For Speed:**
- Use `/score-location` for fast scoring (~0.2s)
- Use `/generate-insights` only when AI needed (~2.1s)
- **Best:** Use both steps separately (total ~2.3s)

### **For Convenience:**
- Use `/score-location-with-insights` for one-step analysis (~146s)
- **Note:** Slower due to internal API calls between endpoints

### **For Accuracy:**
- All endpoints use identical scoring methodology
- Check city detection in response
- Verify normalization method used

---

## 🐳 **DOCKER COMMANDS**

### **Start API:**
```bash
./run_api.sh
```

### **Stop API:**
```bash
docker compose -f docker-compose.api.yml down
```

### **View Logs:**
```bash
docker logs hackathon-api-1 --tail 20
```

### **Rebuild:**
```bash
docker compose -f docker-compose.api.yml down && ./run_api.sh
```

---

## 🚨 **TROUBLESHOOTING**

### **API Not Responding:**
```bash
# Check if running
docker ps | grep hackathon-api

# Restart if needed
docker compose -f docker-compose.api.yml down && ./run_api.sh
```

### **Slow Responses:**
- First request is always slower (OSM data caching)
- Subsequent requests are faster
- **Two-step approach:** ~2.3s total (recommended)
- **One-step approach:** ~146s (convenient but slower)

### **City Not Detected:**
- Check coordinates are within supported cities
- Supported: Paris, Lille, Bordeaux, Strasbourg, Toulouse
- Uses default normalization if city unknown

---

## 📈 **EXAMPLE RESPONSES**

### **Basic Scoring Response:**
```json
{
  "location": {
    "latitude": 48.8625,
    "longitude": 2.3472,
    "city": "Paris",
    "radius_meters": 500
  },
  "scores": {
    "attractiveness": 75.2,
    "competition": 68.4,
    "accessibility": 82.1,
    "suitability": 71.8,
    "global_score": 74.4
  },
  "features": {
    "restaurants": 45,
    "shops_total": 120,
    "metro_station": 2,
    "walkability_score": 180
  },
  "processing_time": 8.2
}
```

### **AI Insights Response:**
```json
{
  "insights": "This location in Paris shows excellent potential...",
  "city": "Paris",
  "processing_time": 3.4
}
```

---

## 🎉 **YOU'RE READY!**

Your Location Scoring API is now running and ready to analyze any location in France! 

**Start with:** `./run_api.sh`  
**Test with:** `http://localhost:8000/docs`  
**Analyze:** Any coordinates in supported cities

### **🚀 RECOMMENDED WORKFLOW:**
1. **Fast scoring:** Use `/score-location` (~0.2s)
2. **AI insights:** Use `/generate-insights` when needed (~2.1s)
3. **Total time:** ~2.3s for complete analysis

**Happy analyzing!** 🚀

