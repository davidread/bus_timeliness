"""
Test arrival detection logic and state tracking.
"""


from get_bus_data import _bus_previous_state, detect_stop_arrivals


class TestArrivalDetection:
    """Test arrival detection and state tracking."""

    def setup_method(self):
        """Clear state before each test."""
        _bus_previous_state.clear()

    def test_detect_arrivals_first_observation(self, mocker):
        """First observations should not count as arrivals."""
        # Mock extract_stops_from_xml to return test stops
        mock_stops = [{"name": "Test Stop", "lat": 51.5074, "lon": -0.1278, "atco_code": "TEST123"}]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Bus very close to stop (first observation)
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 51.5074,  # Same as stop
                "longitude": -0.1278,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should be no arrivals on first observation
        assert len(arrivals) == 0
        assert _bus_previous_state["BUS001_TRIP001"] == "Test Stop"

    def test_detect_arrivals_transition_to_stop(self, mocker):
        """Bus moving from not at stop to at stop should be an arrival."""
        mock_stops = [{"name": "Test Stop", "lat": 51.5074, "lon": -0.1278, "atco_code": "TEST123"}]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Set previous state: bus was not at any stop
        _bus_previous_state["BUS001_TRIP001"] = "not_at_stop"

        # Bus now at stop
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should detect arrival
        assert len(arrivals) == 1
        assert arrivals[0]["bus_id"] == "BUS001"
        assert arrivals[0]["stop_name"] == "Test Stop"
        assert arrivals[0]["distance_meters"] < 10

    def test_detect_arrivals_already_at_stop(self, mocker):
        """Bus already at stop should not trigger new arrival."""
        mock_stops = [{"name": "Test Stop", "lat": 51.5074, "lon": -0.1278, "atco_code": "TEST123"}]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Set previous state: bus was already at this stop
        _bus_previous_state["BUS001_TRIP001"] = "Test Stop"

        # Bus still at same stop
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 51.5074,
                "longitude": -0.1278,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should be no new arrivals
        assert len(arrivals) == 0

    def test_detect_arrivals_stop_to_stop(self, mocker):
        """Bus moving from one stop to another should be an arrival."""
        mock_stops = [
            {"name": "Stop A", "lat": 51.5074, "lon": -0.1278, "atco_code": "A123"},
            {"name": "Stop B", "lat": 51.5084, "lon": -0.1278, "atco_code": "B456"},
        ]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Set previous state: bus was at Stop A
        _bus_previous_state["BUS001_TRIP001"] = "Stop A"

        # Bus now at Stop B
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 51.5084,
                "longitude": -0.1278,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should detect arrival at Stop B
        assert len(arrivals) == 1
        assert arrivals[0]["stop_name"] == "Stop B"

    def test_detect_arrivals_invalid_coordinates(self, mocker):
        """Buses with invalid coordinates should be skipped."""
        mock_stops = [{"name": "Test Stop", "lat": 51.5074, "lon": -0.1278, "atco_code": "TEST123"}]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Bus with invalid coordinates
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 0.0,
                "longitude": 0.0,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should be no arrivals (bus skipped)
        assert len(arrivals) == 0
        assert "BUS001_TRIP001" not in _bus_previous_state

    def test_detect_arrivals_threshold_distance(self, mocker):
        """Bus outside threshold should not trigger arrival."""
        mock_stops = [{"name": "Test Stop", "lat": 51.5074, "lon": -0.1278, "atco_code": "TEST123"}]
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Set previous state: bus was not at stop
        _bus_previous_state["BUS001_TRIP001"] = "not_at_stop"

        # Bus far from stop (more than 1km away)
        buses = [
            {
                "bus_id": "BUS001",
                "route": "TEST",
                "direction": "inbound",
                "latitude": 51.5174,  # About 1.1km away
                "longitude": -0.1278,
                "trip_id": "TRIP001",
            }
        ]

        arrivals = detect_stop_arrivals(buses, arrival_threshold_meters=100)

        # Should be no arrivals (too far)
        assert len(arrivals) == 0
        assert _bus_previous_state["BUS001_TRIP001"] == "not_at_stop"
