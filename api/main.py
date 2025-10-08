from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import osmnx as ox
import warnings
import time
import os

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

# Pydantic models
class LocationRequest(BaseModel):
    latitude: float
    longitude: float
    radius: Optional[int] = 500

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
            'suitability': round(suitability, 2)
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
