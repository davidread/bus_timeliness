"""
Test data filtering and validation functions.
"""

import pytest

from get_bus_data import filter_target_routes, print_bus_locations


class TestDataFiltering:
    """Test data filtering functions."""

    def test_filter_target_routes_matching(self):
        """Test filtering buses for target routes."""
        bus_data = {
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
                        "position": {"latitude": 51.5084, "longitude": -0.1278},
                        "timestamp": "2025-01-01T12:00:00",
                        "trip": {
                            "route_id": "OTHER",
                            "trip_headsign": "outbound",
                            "trip_id": "OTHER_BUS002",
                        },
                    }
                },
            ]
        }

        target_routes = [{"route_name": "TUBE", "directions": ["inbound", "outbound"]}]

        filtered = filter_target_routes(bus_data, target_routes)

        assert len(filtered) == 1
        assert filtered[0]["bus_id"] == "BUS001"
        assert filtered[0]["route"] == "TUBE"
        assert filtered[0]["direction"] == "inbound"
        assert filtered[0]["latitude"] == 51.5074
        assert filtered[0]["longitude"] == -0.1278

    def test_filter_target_routes_no_matches(self):
        """Test filtering when no buses match target routes."""
        bus_data = {
            "entity": [
                {
                    "vehicle": {
                        "vehicle": {"id": "BUS001"},
                        "position": {"latitude": 51.5074, "longitude": -0.1278},
                        "timestamp": "2025-01-01T12:00:00",
                        "trip": {
                            "route_id": "OTHER",
                            "trip_headsign": "inbound",
                            "trip_id": "OTHER_BUS001",
                        },
                    }
                }
            ]
        }

        target_routes = [{"route_name": "TUBE", "directions": ["inbound", "outbound"]}]

        filtered = filter_target_routes(bus_data, target_routes)

        assert len(filtered) == 0

    def test_filter_target_routes_empty_data(self):
        """Test filtering with empty bus data."""
        bus_data = {"entity": []}
        target_routes = [{"route_name": "TUBE", "directions": ["inbound"]}]

        filtered = filter_target_routes(bus_data, target_routes)

        assert len(filtered) == 0

    def test_filter_target_routes_missing_fields(self):
        """Test filtering with buses missing required fields."""
        bus_data = {
            "entity": [
                {
                    "vehicle": {
                        "vehicle": {"id": "BUS001"},
                        "position": {"latitude": 51.5074, "longitude": -0.1278},
                        "trip": {
                            "route_id": "TUBE"
                            # Missing trip_headsign and trip_id
                        },
                    }
                }
            ]
        }

        target_routes = [{"route_name": "TUBE", "directions": ["inbound"]}]

        filtered = filter_target_routes(bus_data, target_routes)

        # Should still include bus with empty/missing fields
        assert len(filtered) == 1
        assert filtered[0]["direction"] == ""
        assert filtered[0]["trip_id"] == ""

    def test_print_bus_locations_valid_buses(self, capsys):
        """Test printing bus locations with valid coordinates."""
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TUBE",
                "direction": "inbound",
                "latitude": 51.5074,
                "longitude": -0.1278,
            },
            {
                "bus_id": "BUS002",
                "route": "TUBE",
                "direction": "outbound",
                "latitude": 51.5084,
                "longitude": -0.1288,
            },
        ]

        # Mock find_nearest_stop to avoid XML parsing
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "get_bus_data.find_nearest_stop",
                lambda lat, lon, route, direction: ("Test Stop", 100),
            )
            print_bus_locations(buses)

        captured = capsys.readouterr()
        assert "Current Bus Locations (2 valid, 0 invalid)" in captured.out
        assert "BUS001: 51.507400, -0.127800" in captured.out
        assert "BUS002: 51.508400, -0.128800" in captured.out

    def test_print_bus_locations_invalid_coordinates(self, capsys):
        """Test printing bus locations with invalid coordinates."""
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TUBE",
                "direction": "inbound",
                "latitude": 51.5074,
                "longitude": -0.1278,
            },
            {
                "bus_id": "BUS002",
                "route": "TUBE",
                "direction": "outbound",
                "latitude": 0.0,
                "longitude": 0.0,
            },
        ]

        # Mock find_nearest_stop
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "get_bus_data.find_nearest_stop",
                lambda lat, lon, route, direction: ("Test Stop", 100),
            )
            print_bus_locations(buses)

        captured = capsys.readouterr()
        assert "Current Bus Locations (1 valid, 1 invalid)" in captured.out
        assert "BUS001: 51.507400, -0.127800" in captured.out
        assert "Skipped 1 buses with invalid GPS coordinates" in captured.out
        assert "Bus BUS002: (0,0) - Invalid GPS data" in captured.out
