from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List
import pandas as pd
import numpy as np
import osmnx as ox
import warnings
import time
import os
import openai

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure OSMnx
ox.config(use_cache=True, log_console=False)

# City bounding boxes (generous to cover whole cities)
CITY_BOUNDS = {
    'Paris': {'min_lat': 48.7, 'max_lat': 49.0, 'min_lon': 2.1, 'max_lon': 2.5},
    'Lille': {'min_lat': 50.5, 'max_lat': 50.8, 'min_lon': 2.9, 'max_lon': 3.2},
    'Bordeaux': {'min_lat': 44.7, 'max_lat': 45.0, 'min_lon': -0.7, 'max_lon': -0.4},
    'Strasbourg': {'min_lat': 48.4, 'max_lat': 48.7, 'min_lon': 7.6, 'max_lon': 7.9},
    'Toulouse': {'min_lat': 43.4, 'max_lat': 43.8, 'min_lon': 1.3, 'max_lon': 1.6}
}

def get_city_from_coordinates(lat, lon):
    """Determine which city a coordinate belongs to using bounding boxes"""
    for city, bounds in CITY_BOUNDS.items():
        if (bounds['min_lat'] <= lat <= bounds['max_lat'] and 
            bounds['min_lon'] <= lon <= bounds['max_lon']):
            return city
    return 'Paris'  # Default fallback

def load_city_normalization_values(city_name):
    """Load normalization values from city grid CSV"""
    try:
        # Try to load the city grid CSV
        csv_path = f"data/{city_name.lower()}_scored.csv"
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            
            # Calculate max values for normalization (mapping city grid column names)
            normalization_values = {
                'max_shops_total': df['shops_total'].max(),
                'max_shops_shoes': df['shops_shoes'].max(),
                'max_restaurants': df['restaurants'].max(),
                'max_hotels': df['hotels'].max(),
                'max_attractions': df['attractions'].max(),
                'max_museums': df['museums'].max(),
                'max_parks': df['parks'].max(),
                'max_banks': df['banks'].max(),
                'max_pharmacies': df['pharmacy'].max(),  # City grid uses 'pharmacy' not 'pharmacies'
                'max_tourism_total': df['total_pois'].max(),  # City grid uses 'total_pois' not 'tourism_total'
                'max_business_centers': df['business_centers'].max(),
                'max_metro_stations': df['metro_station'].max(),  # City grid uses 'metro_station' not 'metro_stations'
                'max_bus_stops': df['bus_stop'].max(),  # City grid uses 'bus_stop' not 'bus_stops'
                'max_parking': df['parking'].max(),
                'max_walkability': df['walkability_score'].max(),  # City grid uses 'walkability_score' not 'walkability'
                'max_residential': df['residential_buildings'].max()  # City grid uses 'residential_buildings' not 'residential'
            }
            return normalization_values
        else:
            print(f"Warning: City grid file not found for {city_name}, using default values")
            return None
    except Exception as e:
        print(f"Error loading city normalization for {city_name}: {e}")
        return None

app = FastAPI(
    title="Location Scoring API",
    description="API to score retail locations based on OSM data",
    version="1.0.0"
)

# CORS configuration
# Note: In production, restrict allowed origins to trusted domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development/demo
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[int] = 500

class Scores(BaseModel):
    attractiveness: float
    competition: float
    accessibility: float
    suitability: float
    global_score: float

class Features(BaseModel):
    restaurants: int
    metro_station: int
    bus_stop: int
    walkability_score: int
    shops_total: int
    shops_shoes: int
    parks: int

class LocationAnalysisRequest(BaseModel):
    latitude: float
    longitude: float
    city: str = "Unknown"
    scores: Scores
    features: Features

class LocationResponse(BaseModel):
    location: dict
    scores: dict
    features: dict
    timestamp: str
    processing_time: float

# Scoring functions (copied from notebook)
def normalize_feature(value, max_val=None):
    """Normalize a feature to 0-1 scale - EXACT same as city grids"""
    if max_val is None:
        max_val = 1
    if max_val == 0:
        return 0
    return value / max_val

def extract_enhanced_poi_features(lat, lon, radius=500):
    """Extract enhanced POI features including residential and walkability"""
    
    features = {
        # Shops
        'shops_total': 0,
        'shops_shoes': 0,
        
        # Food
        'restaurants': 0,  # includes fast food
        
        # Services
        'banks': 0,
        'pharmacy': 0,
        
        # Transport
        'metro_station': 0,
        'bus_stop': 0,
        'parking': 0,
        
        # Tourism & Leisure
        'hotels': 0,
        'attractions': 0,
        'museums': 0,
        'parks': 0,
        
        # Business
        'business_centers': 0,
        
        # Residential & Walkability
        'residential_buildings': 0,
        'walkability_score': 0,
        
        # Total
        'total_pois': 0
    }
    
    try:
        # Enhanced OSM tags
        tags = {
            'shop': True,
            'amenity': ['restaurant', 'fast_food', 'bank', 'pharmacy', 'parking'],
            'public_transport': True,
            'highway': ['bus_stop', 'pedestrian', 'footway', 'cycleway'],
            'tourism': True,
            'leisure': True,
            'office': True,
            'railway': ['station'],
            'building': ['residential', 'office'],
            'landuse': ['residential']
        }
        
        # Get POIs (using new API)
        pois = ox.features_from_point((lat, lon), dist=radius, tags=tags)
        
        if len(pois) > 0:
            features['total_pois'] = len(pois)
            
            # Count shops
            if 'shop' in pois.columns:
                features['shops_total'] = pois['shop'].notna().sum()
                features['shops_shoes'] = pois[pois['shop'] == 'shoes'].shape[0]
            
            # Count amenities
            if 'amenity' in pois.columns:
                features['restaurants'] = pois[pois['amenity'].isin(['restaurant', 'fast_food'])].shape[0]
                features['banks'] = pois[pois['amenity'] == 'bank'].shape[0]
                features['pharmacy'] = pois[pois['amenity'] == 'pharmacy'].shape[0]
                features['parking'] = pois[pois['amenity'] == 'parking'].shape[0]
            
            # Count transport
            if 'railway' in pois.columns:
                features['metro_station'] = pois[pois['railway'] == 'station'].shape[0]
            
            if 'highway' in pois.columns:
                features['bus_stop'] = pois[pois['highway'] == 'bus_stop'].shape[0]
            
            # Count tourism
            if 'tourism' in pois.columns:
                features['hotels'] = pois[pois['tourism'] == 'hotel'].shape[0]
                features['attractions'] = pois[pois['tourism'] == 'attraction'].shape[0]
                features['museums'] = pois[pois['tourism'] == 'museum'].shape[0]
            
            # Count leisure
            if 'leisure' in pois.columns:
                features['parks'] = pois[pois['leisure'] == 'park'].shape[0]
            
            # Count business centers
            if 'office' in pois.columns:
                features['business_centers'] = pois[pois['office'].notna()].shape[0]
            
            # Count residential buildings
            if 'building' in pois.columns:
                features['residential_buildings'] = pois[pois['building'] == 'residential'].shape[0]
            
            if 'landuse' in pois.columns:
                features['residential_buildings'] += pois[pois['landuse'] == 'residential'].shape[0]
            
            # Calculate walkability score
            if 'highway' in pois.columns:
                walkable_features = ['pedestrian', 'footway', 'cycleway']
                walkability_count = sum(pois[pois['highway'] == feature].shape[0] for feature in walkable_features)
                features['walkability_score'] = walkability_count
                
    except Exception as e:
        print(f"Error extracting features at ({lat}, {lon}): {e}")
    
    return features

def calculate_attractiveness(features, norm_values):
    """Calculate attractiveness score (0-100) - using city-specific normalization"""
    if norm_values:
        # Use city-specific max values
        food_entertainment = normalize_feature(
            features['restaurants'] + features['hotels'] + features['attractions'] + features['museums'],
            norm_values['max_restaurants'] + norm_values['max_hotels'] + norm_values['max_attractions'] + norm_values['max_museums']
        ) * 100
        
        services = normalize_feature(
            features['banks'] + features['pharmacy'],
            norm_values['max_banks'] + norm_values['max_pharmacies']
        ) * 100
        
        parks = normalize_feature(features['parks'], norm_values['max_parks']) * 100
        business = normalize_feature(features['business_centers'], norm_values['max_business_centers']) * 100
    else:
        # Fallback to reasonable defaults
        food_entertainment = normalize_feature(features['restaurants'] + features['hotels'] + features['attractions'] + features['museums'], 500) * 100
        services = normalize_feature(features['banks'] + features['pharmacy'], 50) * 100
        parks = normalize_feature(features['parks'], 100) * 100
        business = normalize_feature(features['business_centers'], 100) * 100
    
    attractiveness = (
        0.30 * food_entertainment +
        0.25 * services +
        0.25 * parks +
        0.20 * business
    )
    
    return min(100, attractiveness)

def calculate_competition(features, norm_values):
    """Calculate competition score (1-100) - using city-specific normalization"""
    if norm_values:
        # Use city-specific max values
        shoes_comp = normalize_feature(features['shops_shoes'], norm_values['max_shops_shoes']) * 70
        general_comp = normalize_feature(features['shops_total'], norm_values['max_shops_total']) * 30
    else:
        # Fallback to reasonable defaults
        shoes_comp = normalize_feature(features['shops_shoes'], 100) * 70
        general_comp = normalize_feature(features['shops_total'], 1500) * 30
    
    competition = shoes_comp + general_comp
    
    return min(100, max(1, competition))

def calculate_accessibility(features, norm_values):
    """Calculate accessibility score (0-100) - using city-specific normalization"""
    if norm_values:
        # Use city-specific max values
        metro_score = normalize_feature(features['metro_station'], norm_values['max_metro_stations']) * 40
        walkability_score = normalize_feature(features['walkability_score'], norm_values['max_walkability']) * 30
        bus_score = normalize_feature(features['bus_stop'], norm_values['max_bus_stops']) * 20
        parking_score = normalize_feature(features['parking'], norm_values['max_parking']) * 10
    else:
        # Fallback to reasonable defaults
        metro_score = normalize_feature(features['metro_station'], 10) * 40
        walkability_score = normalize_feature(features['walkability_score'], 10) * 30
        bus_score = normalize_feature(features['bus_stop'], 50) * 20
        parking_score = normalize_feature(features['parking'], 100) * 10
    
    accessibility = metro_score + walkability_score + bus_score + parking_score
    
    return min(100, accessibility)

def calculate_suitability(features, attractiveness, competition, accessibility, norm_values):
    """Calculate suitability score (0-100) - using city-specific normalization"""
    if norm_values:
        # Use city-specific max values
        retail_env = normalize_feature(
            features['shops_total'] + features['restaurants'],
            norm_values['max_shops_total'] + norm_values['max_restaurants']
        ) * 30
        
        customer_base = normalize_feature(
            features['residential_buildings'] + features['business_centers'],
            norm_values['max_residential'] + norm_values['max_business_centers']
        ) * 10
    else:
        # Fallback to reasonable defaults
        retail_env = normalize_feature(features['shops_total'] + features['restaurants'], 1800) * 30
        customer_base = normalize_feature(features['residential_buildings'] + features['business_centers'], 200) * 10
    
    suitability = (
        0.4 * (100 - min(competition, 100)) +  # Lower competition = higher suitability
        retail_env +  # Retail environment
        0.2 * accessibility +  # Accessibility
        customer_base  # Customer base
    )
    
    return min(100, suitability)

def score_location(lat, lon, radius=500):
    """
    Score any location on the map using city-specific normalization
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        radius (int): Search radius in meters (default: 500m)
    
    Returns:
        dict: Dictionary with scores and metadata
    """
    # Determine which city this location belongs to
    city_name = get_city_from_coordinates(lat, lon)
    print(f"Detected city: {city_name}")
    
    # Load city-specific normalization values
    norm_values = load_city_normalization_values(city_name)
    
    # Extract POI features
    features = extract_enhanced_poi_features(lat, lon, radius)
    
    # Calculate individual scores using city-specific normalization
    attractiveness = calculate_attractiveness(features, norm_values)
    competition = calculate_competition(features, norm_values)
    accessibility = calculate_accessibility(features, norm_values)
    suitability = calculate_suitability(features, attractiveness, competition, accessibility, norm_values)
    
    # Calculate global score
    global_score = (attractiveness + competition + accessibility + suitability) / 4
    
    # Convert numpy types to Python native types for JSON serialization
    def convert_numpy_types(obj):
        if isinstance(obj, dict):
            return {k: convert_numpy_types(v) for k, v in obj.items()}
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return obj
    
    # Prepare result
    result = {
        'location': {
            'latitude': lat,
            'longitude': lon,
            'city': city_name,
            'radius_meters': radius
        },
        'scores': {
            'attractiveness': round(attractiveness, 2),
            'competition': round(competition, 2),
            'accessibility': round(accessibility, 2),
            'suitability': round(suitability, 2),
            'global_score': round(global_score, 2)
        },
        'features': convert_numpy_types(features),
        'normalization_used': 'city_specific' if norm_values else 'default',
        'timestamp': pd.Timestamp.now().isoformat()
    }
    
    return result

# API Routes
@app.get("/")
async def root():
    return {"message": "Location Scoring API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": pd.Timestamp.now().isoformat()}

@app.post("/score-location", response_model=LocationResponse)
async def score_location_endpoint(request: LocationRequest):
    """
    Score a location based on OSM data
    
    Args:
        request: LocationRequest with latitude, longitude, and optional radius
    
    Returns:
        LocationResponse with scores and features
    """
    try:
        # Validate coordinates
        if not (-90 <= request.latitude <= 90):
            raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
        if not (-180 <= request.longitude <= 180):
            raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
        if not (100 <= request.radius <= 2000):
            raise HTTPException(status_code=400, detail="Radius must be between 100 and 2000 meters")
        
        # Measure processing time
        start_time = time.time()
        
        # Score the location
        result = score_location(request.latitude, request.longitude, request.radius)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Add processing time to result
        result['processing_time'] = round(processing_time, 3)
        
        return LocationResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing location: {str(e)}")

# LLM Integration for Location Insights
class CityDataLoader:
    def __init__(self):
        self.city_data = {}
        self.feature_descriptions = ""
        self.load_data()
    
    def load_data(self):
        """Load city CSVs and feature descriptions"""
        try:
            # Load feature descriptions
            with open('data/features_desc.txt', 'r', encoding='utf-8') as f:
                self.feature_descriptions = f.read()
            
            # Load city CSVs
            cities = ['Paris', 'Lille', 'Bordeaux', 'Strasbourg', 'Toulouse']
            for city in cities:
                csv_path = f'data/{city.lower()}_scored.csv'
                if os.path.exists(csv_path):
                    df = pd.read_csv(csv_path)
                    self.city_data[city] = df
                    print(f"Loaded {city} data: {len(df)} points")
            
            print(f"✅ Loaded {len(self.city_data)} cities and feature descriptions")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
    
    def get_city_stats(self, city_name: str) -> Dict:
        """Get statistical summary for a city"""
        if city_name not in self.city_data:
            return {}
        
        df = self.city_data[city_name]
        stats = {
            'total_points': len(df),
            'avg_attractiveness': df['attractiveness_score'].mean(),
            'avg_competition': df['competition_score'].mean(),
            'avg_accessibility': df['accessibility_score'].mean(),
            'avg_suitability': df['suitability_score'].mean(),
            'avg_global_score': df['global_score'].mean(),
            'top_10_percent_threshold': df['global_score'].quantile(0.9),
            'bottom_10_percent_threshold': df['global_score'].quantile(0.1)
        }
        return stats

# Initialize data loader
city_loader = CityDataLoader()

def generate_location_insights(location_data: Dict, city_name: str) -> str:
    """Generate AI-powered insights for a location"""
    
    # Get city statistics for comparison
    city_stats = city_loader.get_city_stats(city_name)
    
    if not city_stats:
        return "Unable to generate insights: City data not available."
    
    # Prepare context for LLM
    # The location_data comes from basic_result.dict() which has the structure:
    # {'location': {...}, 'scores': {...}, 'features': {...}, ...}
    scores = location_data['scores']
    features = location_data['features']
    
    # Add global_score if not present
    if 'global_score' not in scores:
        scores['global_score'] = (scores['attractiveness'] + scores['competition'] + 
                                 scores['accessibility'] + scores['suitability']) / 4
    
    # Create prompt
    prompt = f"""
You are a retail location analysis expert. Analyze this location's scores compared to the city's data and provide actionable insights.

LOCATION DATA:
- Coordinates: {location_data['location']['latitude']:.6f}, {location_data['location']['longitude']:.6f}
- City: {city_name}

SCORES (0-100 scale):
- Attractiveness: {scores['attractiveness']:.1f}
- Competition: {scores['competition']:.1f}  
- Accessibility: {scores['accessibility']:.1f}
- Suitability: {scores['suitability']:.1f}
- Global Score: {scores['global_score']:.1f}

KEY FEATURES:
- Restaurants: {features['restaurants']}
- Metro stations: {features['metro_station']}
- Bus stops: {features['bus_stop']}
- Walkability: {features['walkability_score']}
- Shops total: {features['shops_total']}
- Shoe shops: {features['shops_shoes']}
- Parks: {features['parks']}

CITY COMPARISON DATA ({city_name}):
- Average Global Score: {city_stats['avg_global_score']:.1f}
- Top 10% threshold: {city_stats['top_10_percent_threshold']:.1f}
- Bottom 10% threshold: {city_stats['bottom_10_percent_threshold']:.1f}
- Total analyzed points: {city_stats['total_points']:,}

FEATURE DESCRIPTIONS:
{city_loader.feature_descriptions}

Provide a concise analysis (2-3 paragraphs) covering:
1. How this location ranks compared to the city average
2. Key strengths and weaknesses
3. Specific recommendations for retail success

Focus on actionable insights for opening a shoe store.
"""

    try:
        # Use OpenAI API (you can replace with local model)
        print(f"🤖 Calling OpenAI API for {city_name}...")
        
        # Try the older API format first
        openai.api_key = 'INSERT_OPENAI_API_KEY_HERE'
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a retail location analysis expert specializing in urban commercial real estate."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        print(f"✅ OpenAI API response received ({len(result)} chars)")
        return result
        
    except Exception as e:
        print(f"❌ OpenAI API failed: {str(e)}")
        # Fallback to simple analysis if LLM fails
        return generate_fallback_insights(location_data, city_stats)

def generate_fallback_insights(location_data: Dict, city_stats: Dict) -> str:
    """Generate simple insights without LLM"""
    scores = location_data['scores']
    # Calculate global score if not present
    global_score = scores.get('global_score', 
                             (scores['attractiveness'] + scores['competition'] + 
                              scores['accessibility'] + scores['suitability']) / 4)
    city_avg = city_stats['avg_global_score']
    
    if global_score > city_stats['top_10_percent_threshold']:
        ranking = "excellent (top 10%)"
    elif global_score > city_avg:
        ranking = "above average"
    elif global_score > city_stats['bottom_10_percent_threshold']:
        ranking = "below average"
    else:
        ranking = "poor (bottom 10%)"
    
    insights = f"""
LOCATION ANALYSIS:

This location has a {ranking} global score of {global_score:.1f} compared to the city average of {city_avg:.1f}.

Key Observations:
- Attractiveness: {scores['attractiveness']:.1f}/100 - {'Strong' if scores['attractiveness'] > 60 else 'Moderate' if scores['attractiveness'] > 40 else 'Weak'} commercial environment
- Competition: {scores['competition']:.1f}/100 - {'High' if scores['competition'] > 70 else 'Moderate' if scores['competition'] > 40 else 'Low'} competition level
- Accessibility: {scores['accessibility']:.1f}/100 - {'Excellent' if scores['accessibility'] > 60 else 'Good' if scores['accessibility'] > 40 else 'Limited'} transport access
- Suitability: {scores['suitability']:.1f}/100 - {'High' if scores['suitability'] > 60 else 'Moderate' if scores['suitability'] > 40 else 'Low'} retail potential

Recommendation: {'Strong potential' if global_score > city_avg else 'Consider carefully'} for retail development.
"""
    return insights.strip()

# New endpoint for scores + insights
@app.post("/score-location-with-insights")
async def score_location_with_insights(request: LocationRequest):
    """Score a location and provide AI-powered insights (uses /score-location endpoint internally)"""
    try:
        start_time = time.time()
        
        # Step 1: Get basic scores using the /score-location endpoint
        basic_response = await score_location_endpoint(request)
        
        # Convert Pydantic response to dict for easier handling
        basic_data = basic_response.dict()
        
        # Step 2: Generate AI insights using the /generate-insights endpoint
        insights_request = LocationAnalysisRequest(
            latitude=request.latitude,
            longitude=request.longitude,
            city=basic_data['location']['city'],
            scores=Scores(
                attractiveness=basic_data['scores']['attractiveness'],
                competition=basic_data['scores']['competition'],
                accessibility=basic_data['scores']['accessibility'],
                suitability=basic_data['scores']['suitability'],
                global_score=basic_data['scores']['global_score']
            ),
            features=Features(
                restaurants=basic_data['features']['restaurants'],
                metro_station=basic_data['features']['metro_station'],
                bus_stop=basic_data['features']['bus_stop'],
                walkability_score=basic_data['features']['walkability_score'],
                shops_total=basic_data['features']['shops_total'],
                shops_shoes=basic_data['features']['shops_shoes'],
                parks=basic_data['features']['parks']
            )
        )
        
        insights_data = await generate_insights(insights_request)
        
        # Combine results
        basic_data['insights'] = insights_data['insights']
        basic_data['city'] = insights_data['city']
        
        processing_time = time.time() - start_time
        basic_data['processing_time'] = round(processing_time, 3)
        
        return basic_data
        
    except Exception as e:
        print(f"Error in combined endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing location with insights: {str(e)}")

@app.post("/generate-insights")
async def generate_insights(request: LocationAnalysisRequest):
    """Generate AI insights from existing location analysis data"""
    try:
        start_time = time.time()
        
        # Convert request to the format expected by generate_location_insights
        location_data = {
            'location': {
                'latitude': request.latitude,
                'longitude': request.longitude
            },
            'scores': {
                'attractiveness': request.scores.attractiveness,
                'competition': request.scores.competition,
                'accessibility': request.scores.accessibility,
                'suitability': request.scores.suitability,
                'global_score': request.scores.global_score
            },
            'features': {
                'restaurants': request.features.restaurants,
                'metro_station': request.features.metro_station,
                'bus_stop': request.features.bus_stop,
                'walkability_score': request.features.walkability_score,
                'shops_total': request.features.shops_total,
                'shops_shoes': request.features.shops_shoes,
                'parks': request.features.parks
            }
        }
        
        insights = generate_location_insights(location_data, request.city)
        
        processing_time = time.time() - start_time
        
        return {
            "insights": insights,
            "city": request.city,
            "processing_time": round(processing_time, 3)
        }
        
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error generating insights: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
