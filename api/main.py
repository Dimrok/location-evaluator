from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import pandas as pd
import numpy as np
import osmnx as ox
import warnings
import time

# Suppress warnings
warnings.filterwarnings('ignore')

# Configure OSMnx
ox.config(use_cache=True, log_console=False)

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
    """Normalize a feature to 0-1 scale"""
    if max_val is None:
        max_val = 1
    if max_val == 0:
        return 0
    return min(1, value / max_val)

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

def calculate_attractiveness(features):
    """Calculate attractiveness score (0-100) - normalized features"""
    attractiveness = (
        # Shops (30% weight) - Most important for retail
        0.3 * normalize_feature(features['shops_total'], 50) * 100 +  # 0-30 points
        
        # Restaurants (25% weight) - High foot traffic
        0.25 * normalize_feature(features['restaurants'], 20) * 100 +  # 0-25 points
        
        # Banks (20% weight) - Financial services
        0.2 * normalize_feature(features['banks'], 10) * 100 +        # 0-20 points
        
        # Hotels (15% weight) - Tourism
        0.15 * normalize_feature(features['hotels'], 5) * 100 +       # 0-15 points
        
        # Attractions (10% weight) - Tourism
        0.1 * normalize_feature(features['attractions'], 10) * 100    # 0-10 points
    )
    
    return min(100, attractiveness)

def calculate_competition(features):
    """Calculate competition score (1-100) - normalized features"""
    competition = (
        # Shoe shops (60% weight) - Direct competition
        0.6 * normalize_feature(features['shops_shoes'], 5) * 100 +   # 0-60 points
        
        # Total shops (40% weight) - General retail competition
        0.4 * normalize_feature(features['shops_total'], 50) * 100    # 0-40 points
    )
    
    return min(100, max(1, competition))

def calculate_accessibility(features):
    """Calculate accessibility score (0-100) - normalized features"""
    accessibility = (
        # Metro stations (40% weight) - Most important
        0.4 * normalize_feature(features['metro_station'], 3) * 100 +  # 0-40 points
        
        # Walkability (30% weight) - More important
        0.3 * normalize_feature(features['walkability_score'], 20) * 100 +  # 0-30 points
        
        # Bus stops (20% weight)
        0.2 * normalize_feature(features['bus_stop'], 10) * 100 +        # 0-20 points
        
        # Parking (10% weight) - Least important
        0.1 * normalize_feature(features['parking'], 20) * 100           # 0-10 points
    )
    
    return min(100, accessibility)

def calculate_suitability(features, attractiveness, competition, accessibility):
    """Calculate suitability score (0-100) - shoe store specific"""
    suitability = (
        # Attractiveness (40% weight) - Overall location quality
        0.4 * attractiveness +
        
        # Accessibility (30% weight) - Customer reach
        0.3 * accessibility +
        
        # Low competition (20% weight) - Less competition is better
        0.2 * (100 - competition) +
        
        # Residential density (10% weight) - Local customers
        0.1 * normalize_feature(features['residential_buildings'], 30) * 100
    )
    
    return min(100, suitability)

def score_location(lat, lon, radius=500):
    """
    Score any location on the map
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        radius (int): Search radius in meters (default: 500m)
    
    Returns:
        dict: Dictionary with scores and metadata
    """
    # Extract POI features
    features = extract_enhanced_poi_features(lat, lon, radius)
    
    # Calculate individual scores
    attractiveness = calculate_attractiveness(features)
    competition = calculate_competition(features)
    accessibility = calculate_accessibility(features)
    suitability = calculate_suitability(features, attractiveness, competition, accessibility)
    
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
            'radius_meters': radius
        },
        'scores': {
            'attractiveness': round(attractiveness, 2),
            'competition': round(competition, 2),
            'accessibility': round(accessibility, 2),
            'suitability': round(suitability, 2)
        },
        'features': convert_numpy_types(features),
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
