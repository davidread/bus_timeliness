"""
Test distance calculations and coordinate handling.
"""



from get_bus_data import calculate_distance, find_nearest_stop


class TestDistanceCalculations:
    """Test distance calculation functions."""

    def test_calculate_distance_same_point(self):
        """Distance between same point should be 0."""
        lat, lon = 51.5074, -0.1278  # London coordinates
        distance = calculate_distance(lat, lon, lat, lon)
        assert distance == 0.0

    def test_calculate_distance_known_points(self):
        """Test distance between known points."""
        # London to Paris (approximately 344 km)
        london_lat, london_lon = 51.5074, -0.1278
        paris_lat, paris_lon = 48.8566, 2.3522

        distance = calculate_distance(london_lat, london_lon, paris_lat, paris_lon)

        # Should be approximately 344,000 meters (allow 10km tolerance)
        assert 334000 < distance < 354000

    def test_calculate_distance_small_distance(self):
        """Test distance calculation for small distances."""
        # Two points very close together (about 111m apart)
        lat1, lon1 = 51.5074, -0.1278
        lat2, lon2 = 51.5084, -0.1278  # 0.001 degree difference in latitude

        distance = calculate_distance(lat1, lon1, lat2, lon2)

        # Should be approximately 111 meters (allow 10m tolerance)
        assert 100 < distance < 122

    def test_find_nearest_stop_with_mock_data(self, mocker):
        """Test finding nearest stop with mocked stop data."""
        # Mock the extract_stops_from_xml function
        mock_stops = [
            {"name": "Stop A", "lat": 51.5074, "lon": -0.1278, "atco_code": "A123"},
            {"name": "Stop B", "lat": 51.5084, "lon": -0.1278, "atco_code": "B456"},
            {"name": "Stop C", "lat": 51.5094, "lon": -0.1278, "atco_code": "C789"},
        ]

        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        # Test point closest to Stop A
        nearest_stop, distance = find_nearest_stop(51.5074, -0.1278, "TEST", "inbound")

        assert nearest_stop == "Stop A"
        assert distance < 1  # Should be very close

    def test_find_nearest_stop_no_coordinates(self, mocker):
        """Test nearest stop when stops have no coordinates."""
        mock_stops = [
            {"name": "Stop A", "lat": None, "lon": None, "atco_code": "A123"},
            {"name": "Stop B", "lat": None, "lon": None, "atco_code": "B456"},
        ]

        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=mock_stops)

        nearest_stop, distance = find_nearest_stop(51.5074, -0.1278, "TEST", "inbound")

        assert nearest_stop == "Stop A"  # Should return first stop
        assert distance == 0  # Unknown distance

    def test_find_nearest_stop_no_stops(self, mocker):
        """Test nearest stop when no stops are available."""
        mocker.patch("get_bus_data.extract_stops_from_xml", return_value=[])

        nearest_stop, distance = find_nearest_stop(51.5074, -0.1278, "TEST", "inbound")

        assert nearest_stop == "No stops found"
        assert distance == float("inf")
