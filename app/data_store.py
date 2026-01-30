"""
Data storage service for traffic analysis history and route configuration
"""

import json
import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from threading import Lock

logger = logging.getLogger(__name__)


class DataStore:
    """Thread-safe storage for traffic analysis results and route configuration"""
    
    def __init__(self, data_dir: str = "/app/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._latest_results = None
        self._latest_timestamp = None
        self._routes_cache = None
        self._settings_cache = None
    
    @property
    def latest_file(self) -> Path:
        return self.data_dir / "latest.json"
    
    @property
    def routes_file(self) -> Path:
        return self.data_dir / "routes.json"
    
    @property
    def settings_file(self) -> Path:
        return self.data_dir / "settings.json"
    
    def history_file(self, date: datetime) -> Path:
        return self.data_dir / f"history_{date.strftime('%Y%m')}.json"
    
    # ==================== SETTINGS ====================
    
    def get_settings(self) -> dict:
        """Get application settings"""
        with self._lock:
            if self._settings_cache:
                return self._settings_cache
            
            if self.settings_file.exists():
                try:
                    with open(self.settings_file, 'r') as f:
                        self._settings_cache = json.load(f)
                        return self._settings_cache
                except Exception as e:
                    logger.error(f"Failed to load settings: {e}")
            
            # Default settings
            return {
                "scheduler_enabled": False,
                "schedule_times": ["17:00", "18:00"],
                "email_enabled": False
            }
    
    def save_settings(self, settings: dict) -> bool:
        """Save application settings"""
        with self._lock:
            try:
                with open(self.settings_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                self._settings_cache = settings
                return True
            except Exception as e:
                logger.error(f"Failed to save settings: {e}")
                return False
    
    # ==================== ROUTES ====================
    
    def get_routes(self) -> list:
        """Get saved routes"""
        with self._lock:
            if self._routes_cache:
                return self._routes_cache
            
            if self.routes_file.exists():
                try:
                    with open(self.routes_file, 'r') as f:
                        self._routes_cache = json.load(f)
                        return self._routes_cache
                except Exception as e:
                    logger.error(f"Failed to load routes: {e}")
            
            # Return default routes if none saved
            return self._get_default_routes()
    
    def save_routes(self, routes: list) -> bool:
        """Save routes configuration"""
        with self._lock:
            try:
                with open(self.routes_file, 'w') as f:
                    json.dump(routes, f, indent=2)
                self._routes_cache = routes
                return True
            except Exception as e:
                logger.error(f"Failed to save routes: {e}")
                return False
    
    def add_route(self, route: dict) -> bool:
        """Add a new route"""
        routes = self.get_routes()
        
        # Generate ID if not provided
        if 'id' not in route:
            route['id'] = f"route_{int(datetime.now().timestamp())}"
        
        routes.append(route)
        return self.save_routes(routes)
    
    def update_route(self, route_id: str, route: dict) -> bool:
        """Update an existing route"""
        routes = self.get_routes()
        
        for i, r in enumerate(routes):
            if r.get('id') == route_id:
                route['id'] = route_id
                routes[i] = route
                return self.save_routes(routes)
        
        return False
    
    def delete_route(self, route_id: str) -> bool:
        """Delete a route"""
        routes = self.get_routes()
        routes = [r for r in routes if r.get('id') != route_id]
        return self.save_routes(routes)
    
    def _get_default_routes(self) -> list:
        """Get default route configurations"""
        return [
            {
                "id": "route_1",
                "name": "Route 1: Via Mombasa Road",
                "origin": "-1.28812113660239, 36.80085249503632",
                "destination": "-1.3049907297236871, 36.90839036620082",
                "origin_name": "Pitman House",
                "destination_name": "Home (South C)",
                "waypoints": (
                    "-1.2894753498615559, 36.80966957239692|"
                    "-1.2892811011120753, 36.811962288274586|"
                    "-1.2902426323550562, 36.81434243825769|"
                    "-1.293156361053483, 36.81647971579386|"
                    "-1.2926804522692732, 36.81994793433433|"
                    "-1.2932925485284323, 36.82085045219245|"
                    "-1.3046072892851817, 36.826476038784726|"
                    "-1.31913153429785, 36.83783842766832|"
                    "-1.3307557488439687, 36.88785508310046"
                ),
                "enabled": True
            },
            {
                "id": "route_2",
                "name": "Route 2: Via Expressway",
                "origin": "-1.28812113660239, 36.80085249503632",
                "destination": "-1.3049907297236871, 36.90839036620082",
                "origin_name": "Pitman House",
                "destination_name": "Home (South C)",
                "waypoints": (
                    "-1.2894753498615559, 36.80966957239692|"
                    "-1.2892811011120753, 36.811962288274586|"
                    "-1.2902426323550562, 36.81434243825769|"
                    "-1.293156361053483, 36.81647971579386|"
                    "-1.2926804522692732, 36.81994793433433|"
                    "-1.2936641005884062, 36.82124041293404|"
                    "-1.329371054019762, 36.88516007025618|"
                    "-1.3307557488439687, 36.88785508310046"
                ),
                "enabled": True
            },
            {
                "id": "route_3",
                "name": "Route 3: Via Likoni & Lunga Lunga",
                "origin": "-1.28812113660239, 36.80085249503632",
                "destination": "-1.3049907297236871, 36.90839036620082",
                "origin_name": "Pitman House",
                "destination_name": "Home (South C)",
                "waypoints": (
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
                ),
                "enabled": True
            }
        ]
    
    # ==================== RESULTS ====================
    
    def save_results(self, results: list) -> bool:
        """Save analysis results to storage"""
        if not results:
            return False
        
        timestamp = datetime.now()
        
        data = {
            "timestamp": timestamp.isoformat(),
            "day_of_week": timestamp.strftime("%A"),
            "time": timestamp.strftime("%I:%M %p"),
            "best_route": results[0].name,
            "best_time": results[0].duration_text,
            "routes": [r.to_dict() for r in results]
        }
        
        with self._lock:
            # Save latest
            try:
                with open(self.latest_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Update in-memory cache
                self._latest_results = data
                self._latest_timestamp = timestamp
                
            except Exception as e:
                logger.error(f"Failed to save latest: {e}")
                return False
            
            # Append to history
            try:
                history_file = self.history_file(timestamp)
                
                if history_file.exists():
                    with open(history_file, 'r') as f:
                        history = json.load(f)
                else:
                    history = []
                
                history.append(data)
                
                with open(history_file, 'w') as f:
                    json.dump(history, f, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to save history: {e}")
        
        logger.info(f"📝 Results saved")
        return True
    
    def get_latest(self) -> Optional[dict]:
        """Get most recent analysis results"""
        with self._lock:
            # Return cached if available and recent
            if self._latest_results:
                return self._latest_results
            
            # Load from file
            if self.latest_file.exists():
                try:
                    with open(self.latest_file, 'r') as f:
                        self._latest_results = json.load(f)
                        return self._latest_results
                except Exception as e:
                    logger.error(f"Failed to load latest: {e}")
            
            return None
    
    def get_history(self, days: int = 7) -> list:
        """Get historical data for the past N days"""
        history = []
        
        # Get unique months to check
        today = datetime.now()
        months_to_check = set()
        for i in range(days):
            date = today - timedelta(days=i)
            months_to_check.add(date.strftime('%Y%m'))
        
        cutoff = today - timedelta(days=days)
        
        with self._lock:
            for month in months_to_check:
                history_file = self.data_dir / f"history_{month}.json"
                if history_file.exists():
                    try:
                        with open(history_file, 'r') as f:
                            month_data = json.load(f)
                            for entry in month_data:
                                entry_time = datetime.fromisoformat(entry['timestamp'])
                                if entry_time >= cutoff:
                                    history.append(entry)
                    except Exception as e:
                        logger.error(f"Failed to load history {month}: {e}")
        
        # Sort by timestamp descending
        history.sort(key=lambda x: x['timestamp'], reverse=True)
        return history
    
    def get_stats(self, days: int = 7) -> dict:
        """Calculate statistics from historical data"""
        history = self.get_history(days)
        
        if not history:
            return {}
        
        # Count route wins
        route_wins = {}
        total_analyses = len(history)
        
        for entry in history:
            best = entry.get('best_route', 'Unknown')
            route_wins[best] = route_wins.get(best, 0) + 1
        
        # Calculate average times per route
        route_times = {}
        for entry in history:
            for route in entry.get('routes', []):
                name = route['name']
                if name not in route_times:
                    route_times[name] = []
                route_times[name].append(route['duration_seconds'])
        
        avg_times = {}
        for name, times in route_times.items():
            avg_seconds = sum(times) / len(times)
            avg_times[name] = {
                'avg_minutes': round(avg_seconds / 60, 1),
                'min_minutes': round(min(times) / 60, 1),
                'max_minutes': round(max(times) / 60, 1),
                'samples': len(times)
            }
        
        return {
            'total_analyses': total_analyses,
            'route_wins': route_wins,
            'avg_times': avg_times,
            'days': days
        }


# Global instance
_data_store = None


def get_data_store() -> DataStore:
    """Get or create global data store instance"""
    global _data_store
    if _data_store is None:
        data_dir = os.getenv("DATA_DIR", "/app/data")
        _data_store = DataStore(data_dir)
    return _data_store