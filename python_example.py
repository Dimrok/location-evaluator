#!/usr/bin/env python3
"""
Location Scoring API - Python Integration Example
This script demonstrates how to integrate with the Location Scoring API from Python.
"""

import requests
import json
import time
from typing import Dict, Any, Optional

class LocationScoringAPI:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    def get_scores(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """Step 1: Get location scores (fast)"""
        try:
            response = requests.post(
                f"{self.base_url}/score-location",
                json={"latitude": latitude, "longitude": longitude},
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting scores: {e}")
            return None
    
    def get_insights(self, latitude: float, longitude: float, city: str, 
                    scores: Dict, features: Dict) -> Optional[Dict[str, Any]]:
        """Step 2: Get AI insights"""
        try:
            insights_request = {
                "latitude": latitude,
                "longitude": longitude,
                "city": city,
                "scores": scores,
                "features": features
            }
            
            response = requests.post(
                f"{self.base_url}/generate-insights",
                json=insights_request,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting insights: {e}")
            return None
    
    def get_complete_analysis(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        """One-step: Get complete analysis with AI insights"""
        try:
            response = requests.post(
                f"{self.base_url}/score-location-with-insights",
                json={"latitude": latitude, "longitude": longitude},
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"❌ Error getting complete analysis: {e}")
            return None

def print_scores(data: Dict[str, Any]):
    """Pretty print the scores"""
    print("📊 SCORES:")
    print(f"  Attractiveness: {data['scores']['attractiveness']:.1f}")
    print(f"  Competition: {data['scores']['competition']:.1f}")
    print(f"  Accessibility: {data['scores']['accessibility']:.1f}")
    print(f"  Suitability: {data['scores']['suitability']:.1f}")
    print(f"  Global Score: {data['scores']['global_score']:.1f}")
    print()

def print_features(data: Dict[str, Any]):
    """Pretty print the features"""
    print("🏪 FEATURES:")
    features = data['features']
    print(f"  Total Shops: {features['shops_total']}")
    print(f"  Shoe Stores: {features['shops_shoes']}")
    print(f"  Restaurants: {features['restaurants']}")
    print(f"  Metro Stations: {features['metro_station']}")
    print(f"  Bus Stops: {features['bus_stop']}")
    print(f"  Walkability: {features['walkability_score']}")
    print(f"  Parks: {features['parks']}")
    print()

def print_insights(data: Dict[str, Any]):
    """Pretty print the AI insights"""
    print("🤖 AI INSIGHTS:")
    print(data['insights'])
    print()

def demo_two_step_approach():
    """Demonstrate the two-step approach (recommended)"""
    print("🚀 DEMO: Two-Step Approach (Recommended)")
    print("=" * 50)
    
    api = LocationScoringAPI()
    
    # Test location: Paris Marais
    lat, lng = 48.861943, 2.365386
    
    print(f"📍 Analyzing location: {lat}, {lng}")
    print()
    
    # Step 1: Get scores
    print("Step 1: Getting scores...")
    start_time = time.time()
    scores_data = api.get_scores(lat, lng)
    step1_time = time.time() - start_time
    
    if not scores_data:
        return
    
    print(f"✅ Scores loaded in {step1_time:.2f}s")
    print_scores(scores_data)
    print_features(scores_data)
    
    # Step 2: Get AI insights
    print("Step 2: Getting AI insights...")
    start_time = time.time()
    insights_data = api.get_insights(
        lat, lng,
        scores_data['location']['city'],
        scores_data['scores'],
        scores_data['features']
    )
    step2_time = time.time() - start_time
    
    if insights_data:
        print(f"✅ AI insights loaded in {step2_time:.2f}s")
        print_insights(insights_data)
    
    total_time = step1_time + step2_time
    print(f"⏱️  Total time: {total_time:.2f}s")

def demo_one_step_approach():
    """Demonstrate the one-step approach (convenient)"""
    print("\n⚡ DEMO: One-Step Approach (Convenient)")
    print("=" * 50)
    
    api = LocationScoringAPI()
    
    # Test location: Bordeaux
    lat, lng = 44.837862, -0.571754
    
    print(f"📍 Analyzing location: {lat}, {lng}")
    print()
    
    print("Getting complete analysis...")
    start_time = time.time()
    complete_data = api.get_complete_analysis(lat, lng)
    total_time = time.time() - start_time
    
    if not complete_data:
        return
    
    print(f"✅ Complete analysis loaded in {total_time:.2f}s")
    print_scores(complete_data)
    print_features(complete_data)
    print_insights(complete_data)

def demo_batch_analysis():
    """Demonstrate batch analysis of multiple locations"""
    print("\n📊 DEMO: Batch Analysis")
    print("=" * 50)
    
    api = LocationScoringAPI()
    
    # Multiple test locations
    locations = [
        (48.861943, 2.365386, "Paris Marais"),
        (44.837862, -0.571754, "Bordeaux"),
        (48.8842, 2.3388, "Paris Montmartre"),
        (43.6021, 1.4470, "Toulouse")
    ]
    
    results = []
    
    for lat, lng, name in locations:
        print(f"📍 Analyzing {name}...")
        data = api.get_scores(lat, lng)
        
        if data:
            results.append({
                'name': name,
                'global_score': data['scores']['global_score'],
                'city': data['location']['city'],
                'processing_time': data['processing_time']
            })
            print(f"  Global Score: {data['scores']['global_score']:.1f}")
        else:
            print(f"  ❌ Failed to analyze {name}")
    
    print("\n📈 BATCH RESULTS:")
    print("-" * 30)
    for result in results:
        print(f"{result['name']:20} | Score: {result['global_score']:5.1f} | Time: {result['processing_time']:5.2f}s")

def main():
    """Main demo function"""
    print("🎯 Location Scoring API - Python Integration Demo")
    print("=" * 60)
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is running and ready!")
        else:
            print("❌ API is not responding properly")
            return
    except requests.exceptions.RequestException:
        print("❌ API is not running. Please start it with: ./run_api.sh")
        return
    
    print()
    
    # Run demos
    demo_two_step_approach()
    demo_one_step_approach()
    demo_batch_analysis()
    
    print("\n🎉 Demo completed!")
    print("\n💡 Tips:")
    print("  - Use two-step approach for better performance")
    print("  - Use one-step approach for convenience")
    print("  - Batch multiple requests for efficiency")
    print("  - Always handle errors gracefully")

if __name__ == "__main__":
    main()
