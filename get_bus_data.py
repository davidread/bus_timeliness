#!/usr/bin/env python3
"""
Main script to collect bus location data from BODS API and track arrivals at stops.
Runs for 3 hours, polling every 2 minutes.
"""

import os
import sys
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import gspread
import requests

from config import GOOGLE_SHEET_ID, ROUTES_TO_ANALYZE


def load_bods_key():
    """Load BODS API key from file or environment variable."""
    try:
        with open(".bods_key") as f:
            return f.read().strip()
    except FileNotFoundError:
        key = os.getenv("BODS_KEY")
        if not key:
            raise ValueError("BODS API key not found in .bods_key file or BODS_KEY environment variable")
        return key


def get_bus_positions(api_key, line_ref):
    """Fetch current bus positions from BODS API."""
    import xml.etree.ElementTree as ET

    url = f"https://data.bus-data.dft.gov.uk/api/v1/datafeed/?api_key={api_key}&lineRef={line_ref}"

    response = requests.get(url)
    response.raise_for_status()

    print(f"Response status: {response.status_code}")
    print(f"Response content type: {response.headers.get('content-type')}")

    # Save response to disk for debugging
    with open(f"api_response_{line_ref}.xml", "w") as f:
        f.write(response.text)
    print(f"Saved API response to api_response_{line_ref}.xml")

    if not response.text.strip():
        print("Empty response from API")
        return {"entity": []}

    # Parse SIRI XML response
    try:
        root = ET.fromstring(response.text)
        ns = {"siri": "http://www.siri.org.uk/siri"}

        buses = []
        for vehicle_activity in root.findall(".//siri:VehicleActivity", ns):
            vehicle_ref = vehicle_activity.find(".//siri:VehicleRef", ns)
            line_ref_elem = vehicle_activity.find(".//siri:LineRef", ns)
            direction_ref = vehicle_activity.find(".//siri:DirectionRef", ns)
            latitude = vehicle_activity.find(".//siri:Latitude", ns)
            longitude = vehicle_activity.find(".//siri:Longitude", ns)
            recorded_time = vehicle_activity.find("siri:RecordedAtTime", ns)

            if (
                vehicle_ref is not None
                and line_ref_elem is not None
                and latitude is not None
                and longitude is not None
            ):
                bus_data = {
                    "vehicle": {
                        "vehicle": {"id": vehicle_ref.text},
                        "position": {
                            "latitude": float(latitude.text),
                            "longitude": float(longitude.text),
                        },
                        "timestamp": recorded_time.text if recorded_time is not None else "",
                        "trip": {
                            "route_id": line_ref_elem.text,
                            "trip_headsign": (
                                direction_ref.text if direction_ref is not None else ""
                            ),
                            "trip_id": f"{line_ref_elem.text}_{vehicle_ref.text}",
                        },
                    }
                }
                buses.append(bus_data)

        print(f"Parsed {len(buses)} buses from SIRI XML")
        return {"entity": buses}

    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return {"entity": []}


def get_route_stops(api_key, route_name, direction):
    """Get stops for a specific route and direction from BODS API."""
    # This would need the actual BODS API endpoint for route/stop data
    # For now, return empty list - will be populated from actual API
    # TODO: Implement actual API call to get stops for route/direction
    # This is a placeholder - actual implementation depends on BODS API structure
    return []


def validate_routes(api_key, target_routes):
    """Validate that all configured routes exist in the BODS data."""
    print("Validating configured routes...")

    # Get current bus data to check available routes
    # Use first route for validation
    first_route = target_routes[0]["route_name"]
    bus_data = get_bus_positions(api_key, first_route)

    available_routes = set()
    for bus in bus_data.get("entity", []):
        vehicle = bus.get("vehicle", {})
        trip = vehicle.get("trip", {})

        route_name = trip.get("route_id", "")
        direction = trip.get("trip_headsign", "")

        if route_name and direction:
            available_routes.add((route_name, direction))

    # Check each configured route
    for route_config in target_routes:
        route_name = route_config["route_name"]

        # Check if the route exists in any direction
        route_found = False
        for available_route, _available_direction in available_routes:
            if available_route == route_name:
                route_found = True
                break

        if not route_found:
            print(f"ERROR: Route '{route_name}' not found in current BODS data")
            print("Available routes:")
            for route_name_avail, direction in sorted(available_routes):
                print(f"  Route: {route_name_avail}, Direction: {direction}")
            sys.exit(1)

    print("All configured routes validated successfully")
    return True


def filter_target_routes(bus_data, target_routes):
    """Filter bus data for only the routes we want to analyze."""
    filtered_buses = []

    for bus in bus_data.get("entity", []):
        vehicle = bus.get("vehicle", {})
        trip = vehicle.get("trip", {})

        route_short_name = trip.get("route_id", "")
        direction = trip.get("trip_headsign", "")

        for target in target_routes:
            if route_short_name == target["route_name"]:
                filtered_buses.append(
                    {
                        "bus_id": vehicle.get("vehicle", {}).get("id", ""),
                        "route": route_short_name,
                        "direction": direction,
                        "latitude": vehicle.get("position", {}).get("latitude"),
                        "longitude": vehicle.get("position", {}).get("longitude"),
                        "timestamp": vehicle.get("timestamp"),
                        "trip_id": trip.get("trip_id", ""),
                    }
                )

    return filtered_buses


def setup_google_sheets():
    """Initialize Google Sheets connection with multiple tabs."""

    credentials_path = os.path.expanduser("~/.gcloud/scraper-service-account-key.json")

    # Try file-based credentials first, then environment variable
    if os.path.exists(credentials_path):
        gc = gspread.service_account(filename=credentials_path)
    else:
        # Try environment variable
        credentials_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
        if not credentials_json:
            raise ValueError("Google service account credentials not found in file or GOOGLE_SERVICE_ACCOUNT_KEY environment variable")

        import json
        credentials_dict = json.loads(credentials_json)
        gc = gspread.service_account_from_dict(credentials_dict)

    # Use sheet ID from config
    sheet = gc.open_by_key(GOOGLE_SHEET_ID)
    print(f"Opened configured Google Sheet: https://docs.google.com/spreadsheets/d/{sheet.id}")

    # Setup tabs
    worksheets = {}

    # Raw data tab
    try:
        worksheets["raw_data"] = sheet.worksheet("Raw_Data")
    except gspread.WorksheetNotFound:
        worksheets["raw_data"] = sheet.add_worksheet(title="Raw_Data", rows="1000", cols="10")
        # Add header
        header = [
            "Timestamp",
            "Bus_ID",
            "Route",
            "Direction",
            "Latitude",
            "Longitude",
            "Trip_ID",
            "Nearest_Stop",
            "Distance_Metres",
        ]
        worksheets["raw_data"].append_row(header)

    # Route-specific tabs (will be created later when we have stop data)
    return worksheets, sheet


# Global cache for stops data
_stops_cache = {}

# Global state tracking for bus arrivals
_bus_previous_state = {}


def extract_stops_from_xml(route_name, direction):
    """Extract stops from downloaded TransXChange XML file for specific route/direction."""
    import xml.etree.ElementTree as ET

    # Check cache first
    cache_key = f"{route_name}_{direction}"
    if cache_key in _stops_cache:
        return _stops_cache[cache_key]

    # Load the XML file
    xml_file = f"timetable-{route_name}.xml"
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Define namespace
    ns = {"txc": "http://www.transxchange.org.uk/"}

    # Get all stop points with their names
    stops_dict = {}
    for stop_point in root.findall(".//txc:AnnotatedStopPointRef", ns):
        stop_ref = stop_point.find("txc:StopPointRef", ns).text
        common_name = stop_point.find("txc:CommonName", ns).text
        stops_dict[stop_ref] = {"name": common_name, "lat": None, "lon": None}

    # Get coordinates from RouteLinks - map stops to their approximate locations
    stop_coordinates = {}
    for route_link in root.findall(".//txc:RouteLink", ns):
        from_stop = route_link.find(".//txc:From/txc:StopPointRef", ns)
        to_stop = route_link.find(".//txc:To/txc:StopPointRef", ns)

        # Get first coordinate from the track mapping for this route link
        first_location = route_link.find(".//txc:Track/txc:Mapping/txc:Location[1]", ns)
        if first_location is not None:
            longitude = first_location.find("txc:Longitude", ns)
            latitude = first_location.find("txc:Latitude", ns)

            if longitude is not None and latitude is not None:
                coord = (float(latitude.text), float(longitude.text))

                # Assign this coordinate to the from_stop
                if from_stop is not None:
                    stop_id = from_stop.text
                    if stop_id not in stop_coordinates:
                        stop_coordinates[stop_id] = coord

        # Get last coordinate for the to_stop
        last_location = route_link.find(".//txc:Track/txc:Mapping/txc:Location[last()]", ns)
        if last_location is not None:
            longitude = last_location.find("txc:Longitude", ns)
            latitude = last_location.find("txc:Latitude", ns)

            if longitude is not None and latitude is not None:
                coord = (float(latitude.text), float(longitude.text))

                # Assign this coordinate to the to_stop
                if to_stop is not None:
                    stop_id = to_stop.text
                    if stop_id not in stop_coordinates:
                        stop_coordinates[stop_id] = coord

    # Update stops_dict with coordinates
    for stop_id, coord in stop_coordinates.items():
        if stop_id in stops_dict:
            stops_dict[stop_id]["lat"] = coord[0]
            stops_dict[stop_id]["lon"] = coord[1]

    # Get stops for the requested direction
    direction_stops = []

    for jp_section in root.findall(".//txc:JourneyPatternSection", ns):
        for timing_link in jp_section.findall(".//txc:JourneyPatternTimingLink", ns):
            # Check From and To stops
            for stop_elem in [
                timing_link.find(".//txc:From", ns),
                timing_link.find(".//txc:To", ns),
            ]:
                if stop_elem is not None:
                    dest_display = stop_elem.find("txc:DynamicDestinationDisplay", ns)
                    stop_ref_elem = stop_elem.find("txc:StopPointRef", ns)

                    if dest_display is not None and stop_ref_elem is not None:
                        dest_text = dest_display.text
                        stop_id = stop_ref_elem.text

                        if stop_id in stops_dict:
                            stop_data = stops_dict[stop_id]
                            stop_info = {
                                "name": stop_data["name"],
                                "atco_code": stop_id,
                                "lat": stop_data["lat"],
                                "lon": stop_data["lon"],
                            }

                            # Determine if this stop matches our direction
                            direction_match = False
                            if direction == "inbound" and ("oxford" in dest_text.lower()):
                                direction_match = True
                            elif direction == "outbound" and (
                                "london" in dest_text.lower() or "victoria" in dest_text.lower()
                            ):
                                direction_match = True

                            if direction_match and stop_info not in direction_stops:
                                direction_stops.append(stop_info)

    # Cache the result
    _stops_cache[cache_key] = direction_stops
    print(f"Cached {len(direction_stops)} stops for {route_name} {direction} with coordinates")

    return direction_stops


def create_route_tab_with_stops(sheet, route_config, stops):
    """Create a route-specific tab with actual stop names as columns."""
    tab_name = f"{route_config['route_name']}_{route_config['direction']}"

    try:
        worksheet = sheet.worksheet(tab_name)
        return worksheet
    except gspread.WorksheetNotFound:
        worksheet = sheet.add_worksheet(title=tab_name, rows="1000", cols=max(10, len(stops) + 3))

        # Create header with actual stop names
        header = ["Date", "Bus_ID", "Trip_ID"] + [stop["name"] for stop in stops]
        worksheet.append_row(header)

        return worksheet


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in meters using Haversine formula."""
    import math

    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Radius of earth in meters
    r = 6371000
    return c * r


def find_nearest_stop(bus_lat, bus_lon, route_name, direction):
    """Find the nearest stop to a bus and return stop name and distance."""
    stops = extract_stops_from_xml(route_name, direction)

    if not stops:
        return "No stops found", float("inf")

    # Find the nearest stop with coordinates
    nearest_stop = None
    nearest_distance = float("inf")

    for stop in stops:
        if stop["lat"] is not None and stop["lon"] is not None:
            # Calculate distance using Haversine formula
            distance = calculate_distance(bus_lat, bus_lon, stop["lat"], stop["lon"])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_stop = stop["name"]

    # If no stops with coordinates found, return first stop
    if nearest_stop is None:
        nearest_stop = stops[0]["name"] if stops else "Unknown"
        nearest_distance = 0  # Unknown distance

    return nearest_stop, nearest_distance


def print_bus_locations(filtered_buses):
    """Print current locations of all buses with nearest stops."""
    valid_buses = [
        bus for bus in filtered_buses if not (bus["latitude"] == 0 and bus["longitude"] == 0)
    ]
    invalid_buses = [
        bus for bus in filtered_buses if bus["latitude"] == 0 and bus["longitude"] == 0
    ]

    print(
        f"\n=== Current Bus Locations ({len(valid_buses)} valid, {len(invalid_buses)} invalid) ==="
    )

    for bus in valid_buses:
        bus_id = bus["bus_id"]
        route = bus["route"]
        direction = bus["direction"]
        lat = bus["latitude"]
        lon = bus["longitude"]

        # Find nearest stop
        nearest_stop, distance = find_nearest_stop(lat, lon, route, direction)

        print(
            f"Bus {bus_id}: {lat:.6f}, {lon:.6f} | {direction} | Nearest: {nearest_stop} ({distance:.0f}m)"
        )

    # Report invalid buses separately
    if invalid_buses:
        print(f"\nSkipped {len(invalid_buses)} buses with invalid GPS coordinates:")
        for bus in invalid_buses:
            print(f"  Bus {bus['bus_id']}: (0,0) - Invalid GPS data")


def update_raw_data_sheet(worksheet, bus_data):
    """Update raw data sheet with current bus positions."""
    timestamp = datetime.now(ZoneInfo("Europe/London")).isoformat()

    rows_to_add = []
    for bus in bus_data:
        # Find nearest stop and distance
        nearest_stop, distance = find_nearest_stop(
            bus["latitude"], bus["longitude"], bus["route"], bus["direction"]
        )

        rows_to_add.append(
            [
                timestamp,
                bus["bus_id"],
                bus["route"],
                bus["direction"],
                bus["latitude"],
                bus["longitude"],
                bus["trip_id"],
                nearest_stop,
                round(distance) if distance != float("inf") else "",
            ]
        )

    if rows_to_add:
        worksheet.append_rows(rows_to_add)


def detect_stop_arrivals(filtered_buses, arrival_threshold_meters=100):
    """Detect when buses actually arrive at stops (transition from not at stop to at stop)."""
    global _bus_previous_state
    arrivals = []

    for bus in filtered_buses:
        bus_id = bus["bus_id"]
        route = bus["route"]
        direction = bus["direction"]
        lat = bus["latitude"]
        lon = bus["longitude"]
        trip_id = bus["trip_id"]

        # Skip buses with invalid coordinates
        if lat == 0 and lon == 0:
            print(f"Skipping bus {bus_id} with invalid coordinates (0,0)")
            continue

        # Get all stops for this route/direction
        stops = extract_stops_from_xml(route, direction)

        # Find which stop (if any) this bus is currently at
        current_stop_at = None
        current_distance = float("inf")

        for stop in stops:
            if stop["lat"] is not None and stop["lon"] is not None:
                distance = calculate_distance(lat, lon, stop["lat"], stop["lon"])

                # If bus is within threshold distance, it's "at" this stop
                if distance <= arrival_threshold_meters:
                    if distance < current_distance:
                        current_stop_at = stop
                        current_distance = distance

        # Check previous state for this bus
        bus_key = f"{bus_id}_{trip_id}"
        previous_stop = _bus_previous_state.get(bus_key, None)

        # If bus is now at a stop but wasn't at this stop before, it's an arrival
        if current_stop_at is not None:
            current_stop_name = current_stop_at["name"]

            # This is an arrival ONLY if:
            # 1. Bus was previously not at any stop, OR
            # 2. Bus was at a different stop before
            # (NOT if previous_stop is None - that means first observation, we don't know if it's an arrival)
            if previous_stop == "not_at_stop" or (
                previous_stop is not None and previous_stop != current_stop_name
            ):
                print(
                    f"ARRIVAL DETECTED: Bus {bus_id} arrived at {current_stop_name} (was: {previous_stop})"
                )

                arrivals.append(
                    {
                        "timestamp": datetime.now(ZoneInfo("Europe/London")).isoformat(),
                        "bus_id": bus_id,
                        "trip_id": trip_id,
                        "route": route,
                        "direction": direction,
                        "stop_name": current_stop_at["name"],
                        "stop_code": current_stop_at["atco_code"],
                        "distance_meters": round(current_distance),
                        "bus_lat": lat,
                        "bus_lon": lon,
                        "stop_lat": current_stop_at["lat"],
                        "stop_lon": current_stop_at["lon"],
                    }
                )
            elif previous_stop is None:
                print(
                    f"FIRST OBSERVATION: Bus {bus_id} observed at {current_stop_name} (not counting as arrival)"
                )

            # Update state - bus is now at this stop
            _bus_previous_state[bus_key] = current_stop_name
        else:
            # Bus is not at any stop
            if previous_stop is None:
                print(f"FIRST OBSERVATION: Bus {bus_id} not at any stop")
            _bus_previous_state[bus_key] = "not_at_stop"

    return arrivals


def update_route_specific_sheet(worksheet, arrivals, stops):
    """Update route-specific sheet with bus arrival times at stops."""
    if not arrivals:
        return

    from collections import defaultdict
    from datetime import datetime, timedelta

    # Group arrivals by date and bus, but track journey times
    arrivals_by_date_bus = defaultdict(lambda: defaultdict(dict))

    for arrival in arrivals:
        date = arrival["timestamp"][:10]  # Extract date part
        bus_id = arrival["bus_id"]
        stop_name = arrival["stop_name"]
        time = arrival["timestamp"][11:19]  # Extract time part

        # Store the arrival time for this bus at this stop
        arrivals_by_date_bus[date][bus_id][stop_name] = time

    # Get current sheet data to find existing rows to update or determine journey separation
    try:
        existing_data = worksheet.get_all_records()
        existing_rows = {}  # {(date, bus_id, journey_group): row_index}
        bus_journey_times = {}  # {(date, bus_id): [list of earliest times from existing rows]}
        
        for i, row in enumerate(existing_data):
            date = row.get("Date", "")
            bus_id = row.get("Bus_ID", "")
            if date and bus_id:
                # Find the earliest time in this row (first non-empty stop time)
                earliest_time = None
                for stop in stops:
                    stop_time = row.get(stop["name"], "")
                    if stop_time:
                        earliest_time = stop_time
                        break
                
                if earliest_time:
                    if (date, bus_id) not in bus_journey_times:
                        bus_journey_times[(date, bus_id)] = []
                    bus_journey_times[(date, bus_id)].append({
                        "earliest_time": earliest_time,
                        "row_index": i + 2  # +2 because sheets are 1-indexed and have header
                    })
    except Exception:
        existing_rows = {}
        bus_journey_times = {}

    def is_same_journey(new_time, existing_time):
        """Check if two times are within 3 hours (same journey)."""
        try:
            new_dt = datetime.strptime(new_time, "%H:%M:%S")
            existing_dt = datetime.strptime(existing_time, "%H:%M:%S")
            
            # Handle day boundary crossings
            if abs((new_dt - existing_dt).total_seconds()) > 12 * 3600:  # More than 12 hours apart
                # One is likely from previous/next day, adjust
                if new_dt.hour < 12 and existing_dt.hour > 12:
                    new_dt += timedelta(days=1)
                elif existing_dt.hour < 12 and new_dt.hour > 12:
                    existing_dt += timedelta(days=1)
            
            time_diff = abs((new_dt - existing_dt).total_seconds())
            return time_diff < 3 * 3600  # Less than 3 hours = same journey
        except ValueError:
            return False

    stop_names = [stop["name"] for stop in stops]
    rows_to_add = []
    rows_to_update = []

    for date, buses in arrivals_by_date_bus.items():
        for bus_id, stop_arrivals in buses.items():
            # Find a trip_id from any arrival for this bus
            trip_id = ""
            for arrival in arrivals:
                if arrival["bus_id"] == bus_id:
                    trip_id = arrival["trip_id"]
                    break

            # Find the earliest time in the new arrivals
            new_earliest_time = None
            for stop_name in stop_names:
                if stop_name in stop_arrivals:
                    new_earliest_time = stop_arrivals[stop_name]
                    break

            if not new_earliest_time:
                continue  # No arrival times for this bus

            # Check if this should update an existing row or create a new one
            update_row_index = None
            if (date, bus_id) in bus_journey_times:
                for journey_info in bus_journey_times[(date, bus_id)]:
                    if is_same_journey(new_earliest_time, journey_info["earliest_time"]):
                        update_row_index = journey_info["row_index"]
                        break

            if update_row_index:
                # Update existing row with new arrival times
                updates = []
                for col_index, stop_name in enumerate(stop_names):
                    if stop_name in stop_arrivals:
                        # Column D is first stop (A=Date, B=Bus_ID, C=Trip_ID, D=first stop)
                        cell_address = f"{chr(68 + col_index)}{update_row_index}"
                        updates.append({"range": cell_address, "values": [[stop_arrivals[stop_name]]]})

                if updates:
                    rows_to_update.extend(updates)
                    print(f"Updating existing journey for bus {bus_id} (same journey as {journey_info['earliest_time']})")
            else:
                # Create new row - this is a separate journey
                row = [date, bus_id, trip_id]
                # Add arrival times for each stop (empty if no arrival recorded)
                for stop_name in stop_names:
                    arrival_time = stop_arrivals.get(stop_name, "")
                    row.append(arrival_time)
                rows_to_add.append(row)
                print(f"Creating new journey row for bus {bus_id} starting at {new_earliest_time}")

    # Add new rows to sheet
    if rows_to_add:
        worksheet.append_rows(rows_to_add)
        print(f"Added {len(rows_to_add)} new bus journey records to route sheet")

    # Update existing rows with new arrival times
    if rows_to_update:
        for update in rows_to_update:
            worksheet.update(update["range"], update["values"])
        print(f"Updated {len(rows_to_update)} stop arrivals in existing journey rows")


def initialize_tracking_session(target_routes):
    """Initialize the tracking session with API validation and Google Sheets setup."""
    # Load API key
    api_key = load_bods_key()

    # Validate configured routes exist
    validate_routes(api_key, target_routes)

    # Setup sheets
    worksheets, sheet = setup_google_sheets()

    # Get stop data for each route and create route tabs
    for route_config in target_routes:
        route_name = route_config["route_name"]
        for direction in route_config["directions"]:
            stops = extract_stops_from_xml(route_name, direction)
            if stops:
                # Create a modified route config for this specific direction
                direction_config = {"route_name": route_name, "direction": direction}
                route_tab = create_route_tab_with_stops(sheet, direction_config, stops)
                worksheets[f"{route_name}_{direction}"] = route_tab

    return api_key, worksheets


def collect_bus_data(api_key, target_routes):
    """Collect bus position data from BODS API for all target routes."""
    all_buses = []
    for route_config in target_routes:
        route_name = route_config["route_name"]
        try:
            bus_data = get_bus_positions(api_key, route_name)
            all_buses.extend(bus_data.get("entity", []))
        except Exception as e:
            print(f"BODS API error for route {route_name}: {e}")
            continue
    
    return all_buses


def process_bus_data(filtered_buses, worksheets):
    """Process bus data, detect arrivals, and update Google Sheets."""
    if not filtered_buses:
        return []

    # Print bus locations
    print_bus_locations(filtered_buses)

    # Detect stop arrivals
    arrivals = detect_stop_arrivals(filtered_buses, arrival_threshold_meters=100)
    if arrivals:
        print(f"Detected {len(arrivals)} stop arrivals:")
        for arrival in arrivals:
            print(
                f"  Bus {arrival['bus_id']} at {arrival['stop_name']} ({arrival['distance_meters']}m)"
            )

    # Update raw data sheet
    try:
        update_raw_data_sheet(worksheets["raw_data"], filtered_buses)
        print("Updated raw data sheet")
    except Exception as e:
        print(f"Google Sheets error: {e}")

    # Update route-specific sheets with arrivals
    if arrivals:
        update_route_specific_sheets(arrivals, worksheets)

    return arrivals


def update_route_specific_sheets(arrivals, worksheets):
    """Update route-specific Google Sheets with arrival data."""
    try:
        # Group arrivals by route and direction
        arrivals_by_route_direction = {}
        for arrival in arrivals:
            key = f"{arrival['route']}_{arrival['direction']}"
            if key not in arrivals_by_route_direction:
                arrivals_by_route_direction[key] = []
            arrivals_by_route_direction[key].append(arrival)

        # Update each route-specific sheet
        for key, route_arrivals in arrivals_by_route_direction.items():
            if key in worksheets:
                route_name, direction = key.split("_", 1)
                stops = extract_stops_from_xml(route_name, direction)
                update_route_specific_sheet(
                    worksheets[key], route_arrivals, stops
                )

    except Exception as e:
        print(f"Route-specific sheets error: {e}")


def run_tracking_loop(api_key, worksheets, target_routes, duration_hours=3):
    """Run the main tracking loop for the specified duration."""
    start_time = datetime.now(ZoneInfo("Europe/London"))
    end_time = start_time + timedelta(hours=duration_hours)
    poll_count = 0

    print(f"Starting tracking loop until {end_time}")

    while datetime.now(ZoneInfo("Europe/London")) < end_time:
        poll_count += 1
        current_time = datetime.now(ZoneInfo("Europe/London"))

        print(f"Poll #{poll_count} at {current_time}")

        try:
            # Collect bus data from API
            all_buses = collect_bus_data(api_key, target_routes)

            # Filter for target routes
            filtered_buses = filter_target_routes({"entity": all_buses}, target_routes)
            print(f"Found {len(filtered_buses)} buses on target routes")

            # Process the data and update sheets
            process_bus_data(filtered_buses, worksheets)

        except Exception as e:
            print(f"General error in poll #{poll_count}: {e}")

        # Sleep for 1 minute before next poll
        print("...")
        time.sleep(60)

    return poll_count


def main():
    """Main execution function - runs for 3 hours."""
    start_time = datetime.now(ZoneInfo("Europe/London"))
    
    print(f"Starting bus tracking at {start_time}")

    try:
        # Initialize the tracking session
        api_key, worksheets = initialize_tracking_session(ROUTES_TO_ANALYZE)

        # Run the main tracking loop
        poll_count = run_tracking_loop(api_key, worksheets, ROUTES_TO_ANALYZE, duration_hours=3)

        print(f"Completed {poll_count} polls. Tracking session ended at {datetime.now(ZoneInfo('Europe/London'))}")

    except Exception as e:
        print(f"Fatal error: {e}")
        raise


if __name__ == "__main__":
    main()
