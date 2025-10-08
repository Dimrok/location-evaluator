#!/usr/bin/env python3
"""
Multi-City POI Grid Extraction Script

Extracts POI features for multiple French cities using multiprocessing.
Cities: Paris, Lille, Bordeaux, Strasbourg, Toulouse
"""

import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
from shapely.geometry import Point
import time
import multiprocessing as mp
from multiprocessing import Pool, Manager
import logging
import os
from datetime import datetime
import sys
import warnings

# Suppress OSMnx warnings
warnings.filterwarnings('ignore', category=UserWarning, module='osmnx')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extraction.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configure OSMnx
ox.config(use_cache=True, log_console=False)

# City configurations
CITIES = {
    'Paris': {'country': 'France', 'grid_size': 250},
    'Lille': {'country': 'France', 'grid_size': 250},
    'Bordeaux': {'country': 'France', 'grid_size': 250},
    'Strasbourg': {'country': 'France', 'grid_size': 250},
    'Toulouse': {'country': 'France', 'grid_size': 250}
}

# Use 20 cores (leave 4 for system)
NUM_CORES = 20

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
        logger.warning(f"Error extracting features at ({lat}, {lon}): {e}")
    
    return features

def process_point(args):
    """Process a single grid point - designed for multiprocessing"""
    point, city_name, point_index, total_points = args
    
    try:
        features = extract_enhanced_poi_features(point['lat'], point['lon'])
        features.update({
            'lat': point['lat'],
            'lon': point['lon'],
            'point_id': point['point_id'],
            'city': city_name
        })
        
        # Log progress
        logger.info(f"{city_name}: Processed point {point_index + 1}/{total_points} ({point['point_id']})")
        
        return features
    except Exception as e:
        logger.error(f"Error processing point {point['point_id']} in {city_name}: {e}")
        return None

def create_city_grid(city_name, country, grid_size):
    """Create grid for a specific city"""
    logger.info(f"Creating grid for {city_name}")
    
    try:
        # Get city boundary
        city_boundary = ox.geocode_to_gdf(f"{city_name}, {country}", which_result=1)
        city_polygon = city_boundary.geometry.iloc[0]
        bounds = city_polygon.bounds
        
        logger.info(f"{city_name} bounds: {bounds}")
        
        # Convert to degrees
        lat_deg_per_m = 1/111000
        lon_deg_per_m = 1/(111000 * np.cos(np.radians(bounds[1] + bounds[3]) / 2))
        
        # Create expanded bounds (2km buffer)
        buffer_km = 2
        west, south, east, north = bounds
        lat_buffer = buffer_km * 1000 * lat_deg_per_m
        lon_buffer = buffer_km * 1000 * lon_deg_per_m
        
        expanded_bounds = {
            'west': west - lon_buffer,
            'south': south - lat_buffer,
            'east': east + lon_buffer,
            'north': north + lat_buffer
        }
        
        # Generate grid points
        lat_range = np.arange(expanded_bounds['south'], expanded_bounds['north'] + lat_deg_per_m, grid_size * lat_deg_per_m)
        lon_range = np.arange(expanded_bounds['west'], expanded_bounds['east'] + lon_deg_per_m, grid_size * lon_deg_per_m)
        
        # Create all grid points
        all_grid_points = []
        for lat in lat_range:
            for lon in lon_range:
                all_grid_points.append({
                    'lat': lat,
                    'lon': lon,
                    'point_id': f"{city_name}_{lat:.6f}_{lon:.6f}"
                })
        
        # Filter points inside city
        city_points = []
        for point in all_grid_points:
            point_geom = Point(point['lon'], point['lat'])
            if city_polygon.contains(point_geom):
                city_points.append(point)
        
        logger.info(f"{city_name}: Created {len(city_points)} grid points")
        return city_points, city_polygon
        
    except Exception as e:
        logger.error(f"Error creating grid for {city_name}: {e}")
        return [], None

def process_city(city_name, city_config):
    """Process a single city with multiprocessing"""
    logger.info(f"Starting processing for {city_name}")
    start_time = time.time()
    
    # Create grid
    grid_points, city_polygon = create_city_grid(
        city_name, 
        city_config['country'], 
        city_config['grid_size']
    )
    
    if not grid_points:
        logger.error(f"No grid points created for {city_name}")
        return None
    
    # Prepare arguments for multiprocessing
    args_list = [(point, city_name, idx, len(grid_points)) for idx, point in enumerate(grid_points)]
    
    # Process with multiprocessing
    logger.info(f"Processing {len(grid_points)} points for {city_name} using {NUM_CORES} cores")
    
    with Pool(NUM_CORES) as pool:
        results = pool.map(process_point, args_list)
    
    # Filter out None results
    valid_results = [r for r in results if r is not None]
    
    if not valid_results:
        logger.error(f"No valid results for {city_name}")
        return None
    
    # Create DataFrame
    df = pd.DataFrame(valid_results)
    
    # Save to CSV
    output_file = f"data/{city_name.lower()}_grid.csv"
    df.to_csv(output_file, index=False)
    
    processing_time = time.time() - start_time
    logger.info(f"{city_name} completed in {processing_time:.2f} seconds")
    logger.info(f"{city_name} results saved to {output_file}")
    logger.info(f"{city_name} final shape: {df.shape}")
    
    return df

def main():
    """Main function to process all cities"""
    logger.info("Starting multi-city POI extraction")
    logger.info(f"Using {NUM_CORES} CPU cores")
    logger.info(f"Processing cities: {list(CITIES.keys())}")
    
    # Create data directory
    os.makedirs('data', exist_ok=True)
    
    # Process each city
    all_results = {}
    total_start_time = time.time()
    
    for city_name, city_config in CITIES.items():
        try:
            result = process_city(city_name, city_config)
            if result is not None:
                all_results[city_name] = result
        except Exception as e:
            logger.error(f"Failed to process {city_name}: {e}")
    
    total_time = time.time() - total_start_time
    
    # Summary
    logger.info("=" * 50)
    logger.info("EXTRACTION COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Total processing time: {total_time:.2f} seconds ({total_time/3600:.2f} hours)")
    logger.info(f"Cities processed: {len(all_results)}")
    
    for city_name, df in all_results.items():
        logger.info(f"{city_name}: {df.shape[0]} points, {df.shape[1]} features")
    
    logger.info("All results saved to data/ directory")

if __name__ == "__main__":
    main()
