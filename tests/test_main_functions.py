"""
Test cases for the refactored main function components.
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

from get_bus_data import (
    collect_bus_data,
    process_bus_data,
    update_route_specific_sheets,
    run_tracking_loop
)


class TestCollectBusData:
    """Test the collect_bus_data function."""
    
    @patch('get_bus_data.get_bus_positions')
    def test_collect_bus_data_success(self, mock_get_positions):
        """Test successful bus data collection."""
        # Mock successful API responses
        mock_get_positions.side_effect = [
            {"entity": [{"bus": "123"}]},
            {"entity": [{"bus": "456"}, {"bus": "789"}]}
        ]
        
        target_routes = [
            {"route_name": "ROUTE1"},
            {"route_name": "ROUTE2"}
        ]
        
        result = collect_bus_data("test_api_key", target_routes)
        
        # Should combine all buses from all routes
        assert len(result) == 3
        assert result == [{"bus": "123"}, {"bus": "456"}, {"bus": "789"}]
        
        # Should call API for each route
        mock_get_positions.assert_has_calls([
            call("test_api_key", "ROUTE1"),
            call("test_api_key", "ROUTE2")
        ])
    
    @patch('get_bus_data.get_bus_positions')
    def test_collect_bus_data_with_api_errors(self, mock_get_positions):
        """Test bus data collection with some API errors."""
        # Mock one successful and one failed API call
        mock_get_positions.side_effect = [
            {"entity": [{"bus": "123"}]},
            Exception("API Error")
        ]
        
        target_routes = [
            {"route_name": "ROUTE1"},
            {"route_name": "ROUTE2"}
        ]
        
        result = collect_bus_data("test_api_key", target_routes)
        
        # Should return data from successful calls only
        assert len(result) == 1
        assert result == [{"bus": "123"}]
    
    @patch('get_bus_data.get_bus_positions')
    def test_collect_bus_data_empty_responses(self, mock_get_positions):
        """Test handling of empty API responses."""
        mock_get_positions.side_effect = [
            {"entity": []},
            {}  # Missing entity key
        ]
        
        target_routes = [
            {"route_name": "ROUTE1"},
            {"route_name": "ROUTE2"}
        ]
        
        result = collect_bus_data("test_api_key", target_routes)
        
        # Should handle empty responses gracefully
        assert result == []


class TestProcessBusData:
    """Test the process_bus_data function."""
    
    @patch('get_bus_data.update_route_specific_sheets')
    @patch('get_bus_data.update_raw_data_sheet')
    @patch('get_bus_data.detect_stop_arrivals')
    @patch('get_bus_data.print_bus_locations')
    def test_process_bus_data_with_arrivals(self, mock_print, mock_detect, mock_update_raw, mock_update_routes):
        """Test processing bus data with arrivals detected."""
        filtered_buses = [{"bus_id": "123", "lat": 51.5, "lon": -0.1}]
        mock_arrivals = [{"bus_id": "123", "stop_name": "Test Stop", "distance_meters": 50}]
        mock_detect.return_value = mock_arrivals
        
        worksheets = {"raw_data": MagicMock()}
        
        result = process_bus_data(filtered_buses, worksheets)
        
        # Should call all processing functions
        mock_print.assert_called_once_with(filtered_buses)
        mock_detect.assert_called_once_with(filtered_buses, arrival_threshold_meters=100)
        mock_update_raw.assert_called_once_with(worksheets["raw_data"], filtered_buses)
        mock_update_routes.assert_called_once_with(mock_arrivals, worksheets)
        
        assert result == mock_arrivals
    
    @patch('get_bus_data.update_route_specific_sheets')
    @patch('get_bus_data.update_raw_data_sheet')
    @patch('get_bus_data.detect_stop_arrivals')
    @patch('get_bus_data.print_bus_locations')
    def test_process_bus_data_no_arrivals(self, mock_print, mock_detect, mock_update_raw, mock_update_routes):
        """Test processing bus data with no arrivals."""
        filtered_buses = [{"bus_id": "123", "lat": 51.5, "lon": -0.1}]
        mock_detect.return_value = []
        
        worksheets = {"raw_data": MagicMock()}
        
        result = process_bus_data(filtered_buses, worksheets)
        
        # Should not call route-specific updates when no arrivals
        mock_print.assert_called_once()
        mock_detect.assert_called_once()
        mock_update_raw.assert_called_once()
        mock_update_routes.assert_not_called()
        
        assert result == []
    
    def test_process_bus_data_empty_input(self):
        """Test processing with no bus data."""
        result = process_bus_data([], {})
        assert result == []
    
    @patch('get_bus_data.update_raw_data_sheet')
    @patch('get_bus_data.detect_stop_arrivals')
    @patch('get_bus_data.print_bus_locations')
    def test_process_bus_data_sheet_error(self, mock_print, mock_detect, mock_update_raw):
        """Test handling of Google Sheets errors."""
        filtered_buses = [{"bus_id": "123"}]
        mock_detect.return_value = []
        mock_update_raw.side_effect = Exception("Sheets error")
        
        worksheets = {"raw_data": MagicMock()}
        
        # Should not raise exception, should handle gracefully
        result = process_bus_data(filtered_buses, worksheets)
        assert result == []


class TestUpdateRouteSpecificSheets:
    """Test the update_route_specific_sheets function."""
    
    @patch('get_bus_data.extract_stops_from_xml')
    @patch('get_bus_data.update_route_specific_sheet')
    def test_update_route_specific_sheets_success(self, mock_update_sheet, mock_extract_stops):
        """Test successful route-specific sheet updates."""
        mock_extract_stops.return_value = [{"name": "Stop 1"}]
        
        arrivals = [
            {"route": "TUBE", "direction": "inbound", "bus_id": "123"},
            {"route": "TUBE", "direction": "outbound", "bus_id": "456"}
        ]
        
        worksheets = {
            "TUBE_inbound": MagicMock(),
            "TUBE_outbound": MagicMock()
        }
        
        update_route_specific_sheets(arrivals, worksheets)
        
        # Should call update for each route-direction combination
        assert mock_update_sheet.call_count == 2
        mock_extract_stops.assert_has_calls([
            call("TUBE", "inbound"),
            call("TUBE", "outbound")
        ])
    
    @patch('get_bus_data.extract_stops_from_xml')
    @patch('get_bus_data.update_route_specific_sheet')
    def test_update_route_specific_sheets_missing_worksheet(self, mock_update_sheet, mock_extract_stops):
        """Test handling when worksheet doesn't exist."""
        arrivals = [{"route": "TUBE", "direction": "inbound", "bus_id": "123"}]
        worksheets = {}  # Missing worksheet
        
        # Should not raise exception
        update_route_specific_sheets(arrivals, worksheets)
        
        # Should not call update functions
        mock_update_sheet.assert_not_called()
        mock_extract_stops.assert_not_called()


class TestRunTrackingLoop:
    """Test the run_tracking_loop function."""
    
    def test_run_tracking_loop_function_exists(self):
        """Test that the run_tracking_loop function is properly defined."""
        # Simple test to verify the function exists and is callable
        from get_bus_data import run_tracking_loop
        assert callable(run_tracking_loop)
    
    @patch('get_bus_data.time.sleep')
    @patch('get_bus_data.process_bus_data')
    @patch('get_bus_data.filter_target_routes')
    @patch('get_bus_data.collect_bus_data')
    def test_run_tracking_loop_with_errors(self, mock_collect, mock_filter, mock_process, mock_sleep):
        """Test that tracking loop continues despite errors."""
        # Mock some calls to succeed, others to fail
        mock_collect.side_effect = [
            [{"bus": "123"}],  # First call succeeds
            Exception("API Error")  # Second call fails
        ]
        mock_filter.return_value = [{"bus": "123"}]
        mock_process.return_value = []
        
        api_key = "test_key"
        worksheets = {"raw_data": MagicMock()}
        target_routes = [{"route_name": "TEST"}]
        
        # Use short duration and test error handling
        poll_count = run_tracking_loop(api_key, worksheets, target_routes, duration_hours=0.001)
        
        # Should complete without crashing
        assert poll_count >= 0