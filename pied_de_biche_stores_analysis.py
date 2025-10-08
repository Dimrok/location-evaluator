#!/usr/bin/env python3
"""
Pied de Biche Stores Analysis Script
Extract OSM features and calculate scoring metrics for all Pied de Biche store locations.
"""

import pandas as pd
import numpy as np
import osmnx as ox
import warnings
import time
import os
from tqdm import tqdm

# Suppress OSMnx warnings
warnings.filterwarnings('ignore', category=UserWarning, module='osmnx')

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

def extract_enhanced_poi_features(lat, lon, radius=500):
    """Extract enhanced POI features around a point"""
    
    # Define comprehensive tags
    tags = {
        'shop': True,
        'amenity': ['restaurant', 'cafe', 'fast_food', 'bar', 'parking', 'bank', 'pharmacy', 'post_office'],
        'public_transport': True,
        'highway': ['bus_stop', 'platform', 'pedestrian', 'footway', 'cycleway'],
        'tourism': True,
        'leisure': True,
        'office': True
    }
    
    try:
        # Get POIs (using new API)
        pois = ox.features_from_point((lat, lon), dist=radius, tags=tags)
        
        # Initialize features
        features = {
            'shops_total': 0,
            'shops_shoes': 0,
            'restaurants': 0,
            'cafes': 0,
            'fast_food': 0,
            'bars': 0,
            'parking': 0,
            'banks': 0,
            'pharmacies': 0,
            'post_offices': 0,
            'metro_stations': 0,
            'bus_stops': 0,
            'tourism_total': 0,
            'hotels': 0,
            'attractions': 0,
            'museums': 0,
            'parks': 0,
            'business_centers': 0,
            'residential': 0,
            'walkability': 0
        }
        
        if len(pois) > 0:
            # Count shops
            shops = pois[pois['shop'].notna()]
            features['shops_total'] = len(shops)
            
            # Count shoe shops specifically
            shoe_shops = shops[shops['shop'] == 'shoes']
            features['shops_shoes'] = len(shoe_shops)
            
            # Count restaurants
            restaurants = pois[pois['amenity'] == 'restaurant']
            features['restaurants'] = len(restaurants)
            
            # Count cafes
            cafes = pois[pois['amenity'] == 'cafe']
            features['cafes'] = len(cafes)
            
            # Count fast food
            fast_food = pois[pois['amenity'] == 'fast_food']
            features['fast_food'] = len(fast_food)
            
            # Count bars
            bars = pois[pois['amenity'] == 'bar']
            features['bars'] = len(bars)
            
            # Count parking
            parking = pois[pois['amenity'] == 'parking']
            features['parking'] = len(parking)
            
            # Count banks
            banks = pois[pois['amenity'] == 'bank']
            features['banks'] = len(banks)
            
            # Count pharmacies
            pharmacies = pois[pois['amenity'] == 'pharmacy']
            features['pharmacies'] = len(pharmacies)
            
            # Count post offices
            post_offices = pois[pois['amenity'] == 'post_office']
            features['post_offices'] = len(post_offices)
            
            # Count metro stations
            metro = pois[pois['public_transport'] == 'station']
            features['metro_stations'] = len(metro)
            
            # Count bus stops
            bus_stops = pois[pois['highway'] == 'bus_stop']
            features['bus_stops'] = len(bus_stops)
            
            # Count tourism
            tourism = pois[pois['tourism'].notna()]
            features['tourism_total'] = len(tourism)
            
            # Count hotels
            hotels = pois[pois['tourism'] == 'hotel']
            features['hotels'] = len(hotels)
            
            # Count attractions
            attractions = pois[pois['tourism'] == 'attraction']
            features['attractions'] = len(attractions)
            
            # Count museums
            museums = pois[pois['tourism'] == 'museum']
            features['museums'] = len(museums)
            
            # Count parks (SAME as city grid)
            parks = pois[pois['leisure'] == 'park']
            features['parks'] = len(parks)
            
            # Count business centers
            business = pois[pois['office'].notna()]
            features['business_centers'] = len(business)
            
            # Count residential
            residential = pois[pois['amenity'] == 'residential']
            features['residential'] = len(residential)
            
            # Calculate walkability (SAME as city grid: count pedestrian infrastructure)
            walkable_features = ['pedestrian', 'footway', 'cycleway']
            walkability_count = sum(len(pois[pois['highway'] == feature]) for feature in walkable_features)
            features['walkability'] = walkability_count
        
        return features
        
    except Exception as e:
        print(f"Error extracting features for {lat}, {lon}: {e}")
        return None

def normalize_feature(value, max_val):
    """Normalize a feature to 0-1 scale - EXACT same as city grids"""
    if max_val == 0:
        return 0
    return value / max_val

def calculate_scores_with_city_specific_normalization(store_data):
    """Calculate scores using city-specific normalization like the API"""
    
    print("Calculating scores using city-specific normalization...")
    
    for i, store in enumerate(store_data):
        # Determine city for this store
        city_name = get_city_from_coordinates(store['lat'], store['lon'])
        
        # Load city-specific normalization values
        norm_values = load_city_normalization_values(city_name)
        
        print(f"  {store['store_name']} ({city_name}): {'city-specific' if norm_values else 'default'} normalization")
        
        # Calculate scores using city-specific normalization
        if norm_values:
            # Attractiveness (EXACT same as city grids)
            food_entertainment = normalize_feature(
                store['restaurants'] + store['hotels'] + store['attractions'] + store['museums'],
                norm_values['max_restaurants'] + norm_values['max_hotels'] + norm_values['max_attractions'] + norm_values['max_museums']
            ) * 100
            
            services = normalize_feature(
                store['banks'] + store['pharmacies'],
                norm_values['max_banks'] + norm_values['max_pharmacies']
            ) * 100
            
            parks = normalize_feature(store['parks'], norm_values['max_parks']) * 100
            business = normalize_feature(store['business_centers'], norm_values['max_business_centers']) * 100
            
            attractiveness = (0.30 * food_entertainment + 0.25 * services + 0.25 * parks + 0.20 * business)
            
            # Competition (EXACT same as city grids)
            shoes_comp = normalize_feature(store['shops_shoes'], norm_values['max_shops_shoes']) * 70
            general_comp = normalize_feature(store['shops_total'], norm_values['max_shops_total']) * 30
            competition = shoes_comp + general_comp
            
            # Accessibility (EXACT same as city grids)
            metro_score = normalize_feature(store['metro_stations'], norm_values['max_metro_stations']) * 40
            walkability_score = normalize_feature(store['walkability'], norm_values['max_walkability']) * 30
            bus_score = normalize_feature(store['bus_stops'], norm_values['max_bus_stops']) * 20
            parking_score = normalize_feature(store['parking'], norm_values['max_parking']) * 10
            accessibility = metro_score + walkability_score + bus_score + parking_score
            
            # Suitability (EXACT same as city grids)
            shoe_comp_score = (100 - min(competition, 100)) * 0.4
            retail_env = normalize_feature(
                store['shops_total'] + store['restaurants'],
                norm_values['max_shops_total'] + norm_values['max_restaurants']
            ) * 30
            accessibility_component = accessibility * 0.2
            customer_base = normalize_feature(
                store['residential'] + store['business_centers'],
                norm_values['max_residential'] + norm_values['max_business_centers']
            ) * 10
            suitability = shoe_comp_score + retail_env + accessibility_component + customer_base
            
        else:
            # Fallback to reasonable defaults (same as API)
            food_entertainment = normalize_feature(store['restaurants'] + store['hotels'] + store['attractions'] + store['museums'], 500) * 100
            services = normalize_feature(store['banks'] + store['pharmacies'], 50) * 100
            parks = normalize_feature(store['parks'], 100) * 100
            business = normalize_feature(store['business_centers'], 100) * 100
            attractiveness = (0.30 * food_entertainment + 0.25 * services + 0.25 * parks + 0.20 * business)
            
            shoes_comp = normalize_feature(store['shops_shoes'], 100) * 70
            general_comp = normalize_feature(store['shops_total'], 1500) * 30
            competition = shoes_comp + general_comp
            
            metro_score = normalize_feature(store['metro_stations'], 10) * 40
            walkability_score = normalize_feature(store['walkability'], 10) * 30
            bus_score = normalize_feature(store['bus_stops'], 50) * 20
            parking_score = normalize_feature(store['parking'], 100) * 10
            accessibility = metro_score + walkability_score + bus_score + parking_score
            
            shoe_comp_score = (100 - min(competition, 100)) * 0.4
            retail_env = normalize_feature(store['shops_total'] + store['restaurants'], 1800) * 30
            accessibility_component = accessibility * 0.2
            customer_base = normalize_feature(store['residential'] + store['business_centers'], 200) * 10
            suitability = shoe_comp_score + retail_env + accessibility_component + customer_base
        
        # Update store data with scores
        store_data[i]['attractiveness_score'] = min(100, max(0, attractiveness))
        store_data[i]['competition_score'] = min(100, max(1, competition))
        store_data[i]['accessibility_score'] = min(100, max(0, accessibility))
        store_data[i]['suitability_score'] = min(100, max(0, suitability))
        store_data[i]['normalization_used'] = 'city_specific' if norm_values else 'default'
    
    return store_data

def main():
    """Main function to process all Pied de Biche stores"""
    
    # Pied de Biche store locations
    stores = [
        {
            'store_name': 'Paris Marais',
            'address': '5 rue Commines 75003 Paris',
            'lat': 48.86194340587166,
            'lon': 2.365386057479095,
            'city': 'Paris'
        },
        {
            'store_name': 'Paris Montmartre',
            'address': '9 rue des Abbesses 75018 Paris',
            'lat': 48.88398435254506,
            'lon': 2.3388138268114025,
            'city': 'Paris'
        },
        {
            'store_name': 'Paris Saint-Germain-des-Prés',
            'address': '53 rue du Four 75006 Paris',
            'lat': 48.852149127909634,
            'lon': 2.3304371313157537,
            'city': 'Paris'
        },
        {
            'store_name': 'Bordeaux',
            'address': '80 rue du Pas-Saint-Georges 33000 Bordeaux',
            'lat': 44.837862054432115,
            'lon': -0.57175373163398,
            'city': 'Bordeaux'
        },
        {
            'store_name': 'Strasbourg',
            'address': 'Rue des Juifs 2, 67000 Strasbourg',
            'lat': 48.58278963803519,
            'lon': 7.751400197967557,
            'city': 'Strasbourg'
        },
        {
            'store_name': 'Lille',
            'address': 'Rue Lepelletier 34, 59800 Lille',
            'lat': 50.63872270229288,
            'lon': 3.0624484336298208,
            'city': 'Lille'
        },
        {
            'store_name': 'Toulouse',
            'address': 'Rue de la Pomme 6, 31000 Toulouse',
            'lat': 43.602107793277455,
            'lon': 1.447046689217142,
            'city': 'Toulouse'
        }
    ]
    
    print(f"Found {len(stores)} Pied de Biche stores")
    for store in stores:
        print(f"- {store['store_name']}: {store['address']}")
    
    print("\nExtracting OSM features for all Pied de Biche stores...")
    print("This may take a few minutes...")
    
    store_data = []
    
    for i, store in enumerate(tqdm(stores, desc="Processing stores")):
        print(f"\nProcessing {store['store_name']} ({i+1}/{len(stores)})...")
        
        # Extract features
        features = extract_enhanced_poi_features(store['lat'], store['lon'])
        
        if features:
            # Add store information
            features.update({
                'store_name': store['store_name'],
                'address': store['address'],
                'lat': store['lat'],
                'lon': store['lon'],
                'city': store['city']
            })
            
            store_data.append(features)
            print(f"✓ Successfully extracted features for {store['store_name']}")
        else:
            print(f"✗ Failed to extract features for {store['store_name']}")
        
        # Small delay to avoid overwhelming OSM servers
        time.sleep(1)
    
    print(f"\nCompleted! Successfully processed {len(store_data)} stores.")
    
    # Calculate scores using city-specific normalization (same as API)
    store_data = calculate_scores_with_city_specific_normalization(store_data)
    
    # Display scores
    for store in store_data:
        print(f"{store['store_name']}: A={store['attractiveness_score']:.1f}, C={store['competition_score']:.1f}, Acc={store['accessibility_score']:.1f}, S={store['suitability_score']:.1f} ({store['normalization_used']})")
    
    # Create DataFrame
    df_stores = pd.DataFrame(store_data)
    
    # Reorder columns
    column_order = [
        'store_name', 'address', 'lat', 'lon', 'city',
        'shops_total', 'shops_shoes', 'restaurants', 'cafes', 'fast_food', 'bars',
        'parking', 'banks', 'pharmacies', 'post_offices',
        'metro_stations', 'bus_stops',
        'tourism_total', 'hotels', 'attractions', 'museums', 'parks',
        'business_centers', 'residential', 'walkability',
        'attractiveness_score', 'competition_score', 'accessibility_score', 'suitability_score',
        'normalization_used'
    ]
    
    df_stores = df_stores[column_order]
    
    print(f"\nFinal DataFrame shape: {df_stores.shape}")
    print(f"Columns: {list(df_stores.columns)}")
    
    # Display detailed results
    print("\n=== PIED DE BICHE STORES ANALYSIS ===")
    print(f"Total stores analyzed: {len(df_stores)}")
    print(f"Cities covered: {df_stores['city'].nunique()}")
    print(f"Cities: {', '.join(df_stores['city'].unique())}")
    
    print("\n=== SCORE SUMMARY ===")
    score_cols = ['attractiveness_score', 'competition_score', 'accessibility_score', 'suitability_score']
    for col in score_cols:
        print(f"{col.replace('_score', '').title()}: {df_stores[col].mean():.1f} avg, {df_stores[col].min():.1f}-{df_stores[col].max():.1f} range")
    
    print("\n=== DETAILED BREAKDOWN BY STORE ===")
    for _, store in df_stores.iterrows():
        print(f"\n{store['store_name']} ({store['city']}):")
        print(f"  Address: {store['address']}")
        print(f"  Coordinates: {store['lat']:.6f}, {store['lon']:.6f}")
        print(f"  Shops: {store['shops_total']} total, {store['shops_shoes']} shoes")
        print(f"  Food: {store['restaurants']} restaurants, {store['cafes']} cafes, {store['fast_food']} fast food")
        print(f"  Transport: {store['metro_stations']} metro, {store['bus_stops']} bus stops")
        print(f"  Tourism: {store['tourism_total']} total, {store['hotels']} hotels")
        print(f"  Walkability: {store['walkability']:.1f}")
        print(f"  Scores: A={store['attractiveness_score']:.1f}, C={store['competition_score']:.1f}, Acc={store['accessibility_score']:.1f}, S={store['suitability_score']:.1f}")
    
    # Save to CSV
    output_file = 'pied_de_biche_stores_with_scores.csv'
    df_stores.to_csv(output_file, index=False)
    print(f"\n✅ Data saved to: {output_file}")
    print(f"File size: {df_stores.memory_usage(deep=True).sum() / 1024:.1f} KB")
    
    return df_stores

if __name__ == "__main__":
    df_stores = main()
