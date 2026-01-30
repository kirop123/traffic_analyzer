import requests
import json
import os

# --- CONFIGURATION ---
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")

# Your exact coordinates
WORK_LOCATION = "-1.28812113660239, 36.80085249503632"
HOME_LOCATION = "-1.3049907297236871, 36.90839036620082"

# Test with Route 1 first (simplest)
test_route = {
    "name": "Route 1: Via Mombasa Road",
    "origin": WORK_LOCATION,
    "destination": HOME_LOCATION,
    "waypoints": (
        "-1.2894753498615559, 36.80966957239692|"  # Integrity straight
        "-1.2892811011120753, 36.811962288274586|"  # Sarova Corner
        "-1.2902426323550562, 36.81434243825769|"  # Community to Uhuru Park turn
        "-1.293156361053483, 36.81647971579386|"   # Uhuru park corner to haile selassie
        "-1.2926804522692732, 36.81994793433433|"  # Haile Selassie roundabout
        "-1.2932925485284323, 36.82085045219245|"  # Uhuru Highway towards Mega
        "-1.3046072892851817, 36.826476038784726|" # Nyayo roundabout
        "-1.31913153429785, 36.83783842766832|"    # Bellevue
        "-1.3307557488439687, 36.88785508310046"   # Cabanas to Airport North Road
    )
}

print("="*70)
print("TRAFFIC ANALYZER - DEBUG MODE")
print("="*70)
print(f"\nOrigin: {WORK_LOCATION}")
print(f"Destination: {HOME_LOCATION}")
print(f"\nNumber of waypoints: {len(test_route['waypoints'].split('|'))}")
print(f"\nWaypoints:")
for i, wp in enumerate(test_route['waypoints'].split('|'), 1):
    print(f"  {i}. {wp}")

# Test API call
url = "https://maps.googleapis.com/maps/api/directions/json"

params = {
    "origin": test_route["origin"],
    "destination": test_route["destination"],
    "departure_time": "now",
    "traffic_model": "best_guess",
    "waypoints": test_route["waypoints"],
    "key": API_KEY
}

print(f"\n{'='*70}")
print("Making API Request...")
print(f"{'='*70}")

try:
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    data = response.json()
    
    print(f"\nAPI Status: {data.get('status')}")
    
    if data.get('status') != 'OK':
        print(f"Error: {data.get('error_message', 'Unknown error')}")
        print(f"\nFull response:")
        print(json.dumps(data, indent=2))
    else:
        routes = data.get('routes', [])
        print(f"Number of routes returned: {len(routes)}")
        
        if routes:
            route = routes[0]
            legs = route.get('legs', [])
            
            print(f"\n{'='*70}")
            print(f"ROUTE ANALYSIS")
            print(f"{'='*70}")
            print(f"Number of legs: {len(legs)}")
            
            total_distance = 0
            total_duration = 0
            
            for i, leg in enumerate(legs, 1):
                distance = leg.get('distance', {})
                duration = leg.get('duration', {})
                duration_traffic = leg.get('duration_in_traffic', {})
                
                print(f"\nLeg {i}:")
                print(f"  From: {leg.get('start_address', 'Unknown')}")
                print(f"  To: {leg.get('end_address', 'Unknown')}")
                print(f"  Distance: {distance.get('text', 'N/A')} ({distance.get('value', 0)} meters)")
                print(f"  Duration: {duration.get('text', 'N/A')}")
                if duration_traffic:
                    print(f"  Duration in traffic: {duration_traffic.get('text', 'N/A')}")
                
                total_distance += distance.get('value', 0)
                total_duration += duration_traffic.get('value', 0) if duration_traffic else duration.get('value', 0)
            
            print(f"\n{'='*70}")
            print(f"TOTAL ROUTE")
            print(f"{'='*70}")
            print(f"Total Distance: {total_distance} meters ({total_distance/1000:.2f} km)")
            print(f"Total Duration: {total_duration//60} minutes")
            
            # Check if Google is using all waypoints
            waypoint_order = route.get('waypoint_order', [])
            print(f"\nWaypoint order from Google: {waypoint_order}")
            
            # Save full response for inspection
            with open('/tmp/debug_response.json', 'w') as f:
                json.dump(data, f, indent=2)
            print(f"\nFull API response saved to: /tmp/debug_response.json")
            
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{'='*70}")
print("Debug complete!")
print(f"{'='*70}")