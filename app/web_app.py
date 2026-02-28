"""
Flask web application for Traffic Analyzer Dashboard
"""

import os
import logging
import requests as http_requests
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from traffic_analyzer import get_analyzer, RouteConfig
from email_service import get_email_service
from data_store import get_data_store

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler_jobs = {}


def run_analysis(send_email: bool = True):
    """Run traffic analysis and optionally send email"""
    logger.info("=" * 60)
    logger.info("Starting traffic analysis...")
    logger.info("=" * 60)
    
    try:
        store = get_data_store()
        route_dicts = store.get_routes()
        settings = store.get_settings()
        
        routes = [
            RouteConfig(
                name=r['name'],
                origin=r['origin'],
                destination=r['destination'],
                waypoints=r.get('waypoints', '')
            )
            for r in route_dicts if r.get('enabled', True)
        ]
        
        analyzer = get_analyzer()
        results = analyzer.analyze_all(routes)
        
        if results:
            # Save to data store
            store.save_results(results)
            
            # Send email if configured and enabled
            if send_email and settings.get('email_enabled', False):
                email_service = get_email_service()
                if email_service:
                    email_service.send(results)
            
            logger.info("✅ Analysis complete!")
            return results
        else:
            logger.error("❌ No results from analysis")
            return None
            
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        return None


def is_weekday():
    """Check if today is a weekday"""
    return datetime.now().weekday() < 5


def scheduled_analysis():
    """Wrapper for scheduled job - only runs on weekdays unless forced"""
    if is_weekday() or os.getenv("FORCE_RUN", "").lower() == "true":
        run_analysis(send_email=True)
    else:
        logger.info(f"Skipping analysis - weekend")


def update_scheduler():
    """Update scheduler based on saved settings"""
    global scheduler_jobs
    
    store = get_data_store()
    settings = store.get_settings()
    
    # Remove existing jobs
    for job_id in list(scheduler_jobs.keys()):
        try:
            scheduler.remove_job(job_id)
            del scheduler_jobs[job_id]
        except Exception:
            pass
    
    # Add new jobs if scheduler is enabled
    if settings.get('scheduler_enabled', False):
        schedule_times = settings.get('schedule_times', ['17:00', '18:00'])
        
        for time_str in schedule_times:
            try:
                hour, minute = time_str.strip().split(":")
                job_id = f"analysis_{hour}_{minute}"
                
                scheduler.add_job(
                    scheduled_analysis,
                    CronTrigger(hour=int(hour), minute=int(minute), day_of_week='mon-fri'),
                    id=job_id,
                    replace_existing=True
                )
                scheduler_jobs[job_id] = time_str
                logger.info(f"📅 Scheduled analysis at {time_str} (weekdays)")
            except Exception as e:
                logger.error(f"Failed to schedule {time_str}: {e}")
    else:
        logger.info("📅 Scheduler disabled")


# ==================== PAGE ROUTES ====================

@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')


# ==================== API ROUTES ====================

@app.route('/api/latest')
def api_latest():
    """Get latest analysis results"""
    store = get_data_store()
    latest = store.get_latest()
    
    if latest:
        return jsonify(latest)
    return jsonify({"error": "No data available"}), 404


@app.route('/api/history')
def api_history():
    """Get historical data"""
    days = request.args.get('days', 7, type=int)
    store = get_data_store()
    history = store.get_history(days)
    return jsonify(history)


@app.route('/api/stats')
def api_stats():
    """Get statistics"""
    days = request.args.get('days', 7, type=int)
    store = get_data_store()
    stats = store.get_stats(days)
    return jsonify(stats)


@app.route('/api/analyze', methods=['POST'])
def api_analyze():
    """Trigger manual analysis"""
    send_email = request.json.get('send_email', False) if request.json else False
    
    try:
        results = run_analysis(send_email=send_email)
        
        if results:
            return jsonify({
                "success": True,
                "results": [r.to_dict() for r in results],
                "best_route": results[0].name,
                "best_time": results[0].duration_text
            })
        
        return jsonify({"success": False, "error": "No results"}), 500
        
    except Exception as e:
        logger.error(f"Manual analysis failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== ROUTES MANAGEMENT ====================

@app.route('/api/routes', methods=['GET'])
def api_get_routes():
    """Get all routes"""
    store = get_data_store()
    routes = store.get_routes()
    return jsonify(routes)


@app.route('/api/routes', methods=['POST'])
def api_add_route():
    """Add a new route"""
    route = request.json
    
    if not route:
        return jsonify({"error": "No route data provided"}), 400
    
    # Validate required fields
    required = ['name', 'origin', 'destination']
    for field in required:
        if field not in route:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Set defaults
    route.setdefault('enabled', True)
    route.setdefault('waypoints', '')
    route.setdefault('origin_name', '')
    route.setdefault('destination_name', '')
    
    store = get_data_store()
    if store.add_route(route):
        return jsonify({"success": True, "route": route})
    
    return jsonify({"error": "Failed to save route"}), 500


@app.route('/api/routes/<route_id>', methods=['PUT'])
def api_update_route(route_id):
    """Update an existing route"""
    route = request.json
    
    if not route:
        return jsonify({"error": "No route data provided"}), 400
    
    store = get_data_store()
    if store.update_route(route_id, route):
        return jsonify({"success": True})
    
    return jsonify({"error": "Route not found"}), 404


@app.route('/api/routes/<route_id>', methods=['DELETE'])
def api_delete_route(route_id):
    """Delete a route"""
    store = get_data_store()
    if store.delete_route(route_id):
        return jsonify({"success": True})
    
    return jsonify({"error": "Route not found"}), 404


@app.route('/api/routes/<route_id>/toggle', methods=['POST'])
def api_toggle_route(route_id):
    """Toggle route enabled status"""
    store = get_data_store()
    routes = store.get_routes()
    
    for route in routes:
        if route.get('id') == route_id:
            route['enabled'] = not route.get('enabled', True)
            store.save_routes(routes)
            return jsonify({"success": True, "enabled": route['enabled']})
    
    return jsonify({"error": "Route not found"}), 404


# ==================== SETTINGS ====================

@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get application settings"""
    store = get_data_store()
    settings = store.get_settings()
    settings['scheduler_running'] = scheduler.running
    settings['scheduled_jobs'] = list(scheduler_jobs.values())
    return jsonify(settings)


@app.route('/api/settings', methods=['POST'])
def api_save_settings():
    """Save application settings"""
    settings = request.json
    
    if not settings:
        return jsonify({"error": "No settings provided"}), 400
    
    store = get_data_store()
    if store.save_settings(settings):
        # Update scheduler if needed
        update_scheduler()
        return jsonify({"success": True})
    
    return jsonify({"error": "Failed to save settings"}), 500


@app.route('/api/settings/scheduler', methods=['POST'])
def api_toggle_scheduler():
    """Toggle scheduler on/off"""
    store = get_data_store()
    settings = store.get_settings()
    
    settings['scheduler_enabled'] = not settings.get('scheduler_enabled', False)
    store.save_settings(settings)
    
    update_scheduler()
    
    return jsonify({
        "success": True,
        "scheduler_enabled": settings['scheduler_enabled']
    })


# ==================== GOOGLE MAPS PROXY ====================

@app.route('/api/geocode/reverse')
def api_reverse_geocode():
    """Reverse geocode lat/lng to address"""
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    
    if not lat or not lng:
        return jsonify({"error": "lat and lng required"}), 400
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    try:
        res = http_requests.get("https://maps.googleapis.com/maps/api/geocode/json", params={
            "latlng": f"{lat},{lng}",
            "key": api_key
        }, timeout=10)
        data = res.json()
        
        if data.get("status") == "OK" and data.get("results"):
            result = data["results"][0]
            return jsonify({
                "address": result.get("formatted_address", ""),
                "lat": float(lat),
                "lng": float(lng),
                "place_id": result.get("place_id", "")
            })
        
        return jsonify({"error": "No results", "status": data.get("status")}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/places/autocomplete')
def api_places_autocomplete():
    """Proxy Google Places Autocomplete"""
    query = request.args.get('query', '')
    
    if not query or len(query) < 2:
        return jsonify([])
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    try:
        res = http_requests.get("https://maps.googleapis.com/maps/api/place/autocomplete/json", params={
            "input": query,
            "location": "-1.2921,36.8219",
            "radius": 50000,
            "key": api_key
        }, timeout=10)
        data = res.json()
        
        predictions = []
        for p in data.get("predictions", []):
            predictions.append({
                "description": p.get("description", ""),
                "place_id": p.get("place_id", ""),
                "main_text": p.get("structured_formatting", {}).get("main_text", ""),
                "secondary_text": p.get("structured_formatting", {}).get("secondary_text", "")
            })
        
        return jsonify(predictions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/places/details')
def api_place_details():
    """Get place details (coordinates) from place_id"""
    place_id = request.args.get('place_id', '')
    
    if not place_id:
        return jsonify({"error": "place_id required"}), 400
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    try:
        res = http_requests.get("https://maps.googleapis.com/maps/api/place/details/json", params={
            "place_id": place_id,
            "fields": "geometry,formatted_address,name",
            "key": api_key
        }, timeout=10)
        data = res.json()
        
        if data.get("status") == "OK":
            result = data["result"]
            loc = result.get("geometry", {}).get("location", {})
            return jsonify({
                "name": result.get("name", ""),
                "address": result.get("formatted_address", ""),
                "lat": loc.get("lat"),
                "lng": loc.get("lng")
            })
        
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/directions/preview')
def api_directions_preview():
    """Preview route and return polyline for map display"""
    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')
    waypoints = request.args.get('waypoints', '')
    
    if not origin or not destination:
        return jsonify({"error": "origin and destination required"}), 400
    
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key
    }
    if waypoints:
        params["waypoints"] = waypoints
    
    try:
        res = http_requests.get("https://maps.googleapis.com/maps/api/directions/json",
                                params=params, timeout=20)
        data = res.json()
        
        if data.get("status") == "OK" and data.get("routes"):
            route = data["routes"][0]
            legs = route.get("legs", [])
            total_distance = sum(l.get("distance", {}).get("value", 0) for l in legs)
            total_duration = sum(l.get("duration", {}).get("value", 0) for l in legs)
            
            return jsonify({
                "polyline": route.get("overview_polyline", {}).get("points", ""),
                "distance_text": f"{total_distance / 1000:.1f} km",
                "duration_text": f"{total_duration // 60} mins",
                "bounds": route.get("bounds", {})
            })
        
        return jsonify({"error": data.get("status", "Unknown error")}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== HEALTH ====================

@app.route('/api/health')
def health():
    """Health check endpoint"""
    store = get_data_store()
    settings = store.get_settings()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scheduler_running": scheduler.running,
        "scheduler_enabled": settings.get('scheduler_enabled', False),
        "scheduled_jobs": list(scheduler_jobs.values())
    })


# ==================== STARTUP ====================

def setup_scheduler():
    """Setup scheduled jobs from saved settings"""
    scheduler.start()
    update_scheduler()


if __name__ == '__main__':
    # Setup scheduler
    setup_scheduler()
    
    # Run initial analysis if requested
    if os.getenv("RUN_ON_START", "").lower() == "true":
        logger.info("Running initial analysis on startup...")
        run_analysis(send_email=False)
    
    # Start Flask
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "").lower() == "true"
    
    app.run(host='0.0.0.0', port=port, debug=debug)