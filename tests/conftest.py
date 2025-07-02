"""
Pytest configuration and fixtures.
"""

import os
import sys

import pytest

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def clear_state():
    """Clear global state before each test."""
    # Clear the bus state tracking
    from get_bus_data import _bus_previous_state, _stops_cache

    _bus_previous_state.clear()
    _stops_cache.clear()


@pytest.fixture
def sample_bus_data():
    """Sample bus data for testing."""
    return {
        "entity": [
            {
                "vehicle": {
                    "vehicle": {"id": "BUS001"},
                    "position": {"latitude": 51.5074, "longitude": -0.1278},
                    "timestamp": "2025-01-01T12:00:00",
                    "trip": {
                        "route_id": "TUBE",
                        "trip_headsign": "inbound",
                        "trip_id": "TUBE_BUS001",
                    },
                }
            },
            {
                "vehicle": {
                    "vehicle": {"id": "BUS002"},
                    "position": {"latitude": 0.0, "longitude": 0.0},
                    "timestamp": "2025-01-01T12:01:00",
                    "trip": {
                        "route_id": "TUBE",
                        "trip_headsign": "outbound",
                        "trip_id": "TUBE_BUS002",
                    },
                }
            },
        ]
    }


@pytest.fixture
def sample_stops():
    """Sample stop data for testing."""
    return [
        {
            "name": "Victoria Green Line Coach St",
            "lat": 51.49283,
            "lon": -0.14757,
            "atco_code": "49000748010",
        },
        {
            "name": "Gloucester Grn [2/3]",
            "lat": 51.75385,
            "lon": -1.26254,
            "atco_code": "34000000003",
        },
    ]


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return [
        {
            "route_name": "TUBE",
            "directions": ["inbound", "outbound"],
            "timetable_download_url": "https://example.com/timetable.xml",
        }
    ]
