"""
Traffic Route Analyzer
Compares multiple routes and finds the fastest commute using Google Maps API.
"""

import requests
import json
import os
import logging
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class RouteResult:
    """Data class for route analysis results"""
    name: str
    duration_seconds: int
    duration_text: str
    distance_meters: int
    distance_text: str
    has_traffic_data: bool
    timestamp: str
    legs: list
    overview_polyline: str = ""
    waypoint_coordinates: list = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass
class RouteConfig:
    """Configuration for a single route"""
    name: str
    origin: str
    destination: str
    waypoints: Optional[str] = None


class TrafficAnalyzer:
    """Main traffic analysis class"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://maps.googleapis.com/maps/api/directions/json"
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(requests.exceptions.RequestException)
    )
    def _fetch_route(self, route: RouteConfig) -> dict:
        """Fetch route data from Google Maps API with retry logic"""
        params = {
            "origin": route.origin,
            "destination": route.destination,
            "departure_time": "now",
            "traffic_model": "best_guess",
            "key": self.api_key
        }
        
        if route.waypoints:
            params["waypoints"] = route.waypoints
        
        response = requests.get(self.base_url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()
    
    def analyze_route(self, route: RouteConfig) -> Optional[RouteResult]:
        """Analyze a single route and return results"""
        try:
            data = self._fetch_route(route)
        except Exception as e:
            logger.error(f"Failed to fetch route {route.name}: {e}")
            return None
        
        if data.get("status") != "OK":
            logger.warning(f"API error for {route.name}: {data.get('error_message', 'Unknown')}")
            return None
        
        routes = data.get("routes", [])
        if not routes:
            return None
        
        api_route = routes[0]
        legs = api_route.get("legs", [])
        
        if not legs:
            return None
        
        # Sum all legs
        total_duration = 0
        total_distance = 0
        has_traffic = False
        leg_details = []
        
        for leg in legs:
            if "duration_in_traffic" in leg:
                total_duration += leg["duration_in_traffic"]["value"]
                has_traffic = True
            else:
                total_duration += leg["duration"]["value"]
            
            total_distance += leg.get("distance", {}).get("value", 0)
            
            leg_details.append({
                "start": leg.get("start_address", "Unknown"),
                "end": leg.get("end_address", "Unknown"),
                "distance": leg.get("distance", {}).get("text", "N/A"),
                "duration": leg.get("duration_in_traffic", leg.get("duration", {})).get("text", "N/A")
            })
        
        # Extract overview polyline
        overview_polyline = api_route.get("overview_polyline", {}).get("points", "")
        
        # Extract waypoint coordinates from legs
        waypoint_coords = []
        waypoint_coords.append({
            "lat": legs[0]["start_location"]["lat"],
            "lng": legs[0]["start_location"]["lng"],
            "label": legs[0].get("start_address", "Origin")
        })
        for leg in legs[:-1]:
            waypoint_coords.append({
                "lat": leg["end_location"]["lat"],
                "lng": leg["end_location"]["lng"],
                "label": leg.get("end_address", "Waypoint")
            })
        waypoint_coords.append({
            "lat": legs[-1]["end_location"]["lat"],
            "lng": legs[-1]["end_location"]["lng"],
            "label": legs[-1].get("end_address", "Destination")
        })
        
        duration_mins = total_duration // 60
        
        return RouteResult(
            name=route.name,
            duration_seconds=total_duration,
            duration_text=f"{duration_mins} mins",
            distance_meters=total_distance,
            distance_text=f"{total_distance / 1000:.1f} km",
            has_traffic_data=has_traffic,
            timestamp=datetime.now().isoformat(),
            legs=leg_details,
            overview_polyline=overview_polyline,
            waypoint_coordinates=waypoint_coords
        )
    
    def analyze_all(self, routes: list[RouteConfig]) -> list[RouteResult]:
        """Analyze all routes and return sorted results (fastest first)"""
        results = []
        
        for i, route in enumerate(routes, 1):
            logger.info(f"[{i}/{len(routes)}] Analyzing {route.name}...")
            result = self.analyze_route(route)
            
            if result:
                results.append(result)
                icon = "🚦" if result.has_traffic_data else "⏱️"
                logger.info(f"  {icon} {result.duration_text} ({result.distance_text})")
            else:
                logger.warning(f"  ✗ Failed to get data")
        
        # Sort by duration
        results.sort(key=lambda x: x.duration_seconds)
        
        if results:
            logger.info(f"✅ Best route: {results[0].name} ({results[0].duration_text})")
        
        return results


# Default route configurations
DEFAULT_ROUTES = [
    RouteConfig(
        name="Route 1: Via Mombasa Road",
        origin="-1.28812113660239, 36.80085249503632",
        destination="-1.3049907297236871, 36.90839036620082",
        waypoints=(
            "-1.2894753498615559, 36.80966957239692|"
            "-1.2892811011120753, 36.811962288274586|"
            "-1.2902426323550562, 36.81434243825769|"
            "-1.293156361053483, 36.81647971579386|"
            "-1.2926804522692732, 36.81994793433433|"
            "-1.2932925485284323, 36.82085045219245|"
            "-1.3046072892851817, 36.826476038784726|"
            "-1.31913153429785, 36.83783842766832|"
            "-1.3307557488439687, 36.88785508310046"
        )
    ),
    RouteConfig(
        name="Route 2: Via Expressway",
        origin="-1.28812113660239, 36.80085249503632",
        destination="-1.3049907297236871, 36.90839036620082",
        waypoints=(
            "-1.2894753498615559, 36.80966957239692|"
            "-1.2892811011120753, 36.811962288274586|"
            "-1.2902426323550562, 36.81434243825769|"
            "-1.293156361053483, 36.81647971579386|"
            "-1.2926804522692732, 36.81994793433433|"
            "-1.2936641005884062, 36.82124041293404|"
            "-1.329371054019762, 36.88516007025618|"
            "-1.3307557488439687, 36.88785508310046"
        )
    ),
    RouteConfig(
        name="Route 3: Via Likoni & Lunga Lunga",
        origin="-1.28812113660239, 36.80085249503632",
        destination="-1.3049907297236871, 36.90839036620082",
        waypoints=(
            "-1.2894753498615559, 36.80966957239692|"
            "-1.2892811011120753, 36.811962288274586|"
            "-1.2902426323550562, 36.81434243825769|"
            "-1.293156361053483, 36.81647971579386|"
            "-1.2926804522692732, 36.81994793433433|"
            "-1.2932925485284323, 36.82085045219245|"
            "-1.3046072892851817, 36.826476038784726|"
            "-1.31913153429785, 36.83783842766832|"
            "-1.3226380696690379, 36.84825835726657|"
            "-1.308195172672703, 36.86648647501131|"
            "-1.3144344959629324, 36.89416643492551|"
            "-1.3077776114319017, 36.903872887018046"
        )
    )
]


def get_analyzer() -> TrafficAnalyzer:
    """Factory function to create analyzer with API key from environment"""
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable not set")
    return TrafficAnalyzer(api_key)