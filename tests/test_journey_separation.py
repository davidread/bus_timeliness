"""
Test journey separation logic for handling multiple bus journeys per day.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from get_bus_data import update_route_specific_sheet


class TestJourneySeparation:
    """Test cases for journey separation logic."""
    
    def test_same_journey_updates_existing_row(self):
        """Test that arrivals within 3 hours update the existing row."""
        worksheet = MagicMock()
        
        # Mock existing data - bus has journey starting at 08:00
        existing_data = [
            {
                "Date": "2025-07-03",
                "Bus_ID": "123",
                "Trip_ID": "TUBE_123_morning",
                "Stop A": "08:00:00",
                "Stop B": "08:15:00",
                "Stop C": ""
            }
        ]
        worksheet.get_all_records.return_value = existing_data
        
        stops = [
            {"name": "Stop A"},
            {"name": "Stop B"},
            {"name": "Stop C"}
        ]
        
        # New arrival within 3 hours (same journey)
        arrivals = [
            {
                "timestamp": "2025-07-03T10:30:00+01:00",
                "bus_id": "123",
                "trip_id": "TUBE_123_morning",
                "stop_name": "Stop C",
                "route": "TUBE",
                "direction": "outbound"
            }
        ]
        
        update_route_specific_sheet(worksheet, arrivals, stops)
        
        # Should update existing row, not create new one
        worksheet.update.assert_called()
        worksheet.append_rows.assert_not_called()
    
    def test_different_journey_creates_new_row(self):
        """Test that arrivals after 3+ hours create a new row."""
        worksheet = MagicMock()
        
        # Mock existing data - bus has journey starting at 08:00
        existing_data = [
            {
                "Date": "2025-07-03",
                "Bus_ID": "123",
                "Trip_ID": "TUBE_123_morning",
                "Stop A": "08:00:00",
                "Stop B": "08:15:00",
                "Stop C": ""
            }
        ]
        worksheet.get_all_records.return_value = existing_data
        
        stops = [
            {"name": "Stop A"},
            {"name": "Stop B"},
            {"name": "Stop C"}
        ]
        
        # New arrival after 3+ hours (different journey)
        arrivals = [
            {
                "timestamp": "2025-07-03T12:30:00+01:00",
                "bus_id": "123",
                "trip_id": "TUBE_123_afternoon",
                "stop_name": "Stop A",
                "route": "TUBE",
                "direction": "inbound"
            }
        ]
        
        update_route_specific_sheet(worksheet, arrivals, stops)
        
        # Should create new row, not update existing
        worksheet.append_rows.assert_called()
    
    def test_journey_time_comparison_logic(self):
        """Test the journey time comparison logic."""
        
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
        
        # Test cases within 3 hours (same journey)
        assert is_same_journey("08:00:00", "08:30:00") == True
        assert is_same_journey("08:00:00", "10:59:00") == True
        
        # Test cases over 3 hours (different journey)
        assert is_same_journey("08:00:00", "11:01:00") == False
        assert is_same_journey("08:00:00", "12:00:00") == False
        
        # Test day boundary cases
        assert is_same_journey("23:30:00", "01:00:00") == True  # 1h30m across midnight
        assert is_same_journey("23:00:00", "03:00:00") == False  # 4h across midnight
    
    def test_multiple_journeys_same_day(self):
        """Test handling multiple journeys for the same bus on the same day."""
        worksheet = MagicMock()
        
        # Mock existing data with two journeys for same bus
        existing_data = [
            {
                "Date": "2025-07-03",
                "Bus_ID": "123",
                "Trip_ID": "TUBE_123_morning",
                "Stop A": "08:00:00",
                "Stop B": "08:15:00",
                "Stop C": ""
            },
            {
                "Date": "2025-07-03",
                "Bus_ID": "123",
                "Trip_ID": "TUBE_123_afternoon",
                "Stop A": "14:00:00",
                "Stop B": "",
                "Stop C": ""
            }
        ]
        worksheet.get_all_records.return_value = existing_data
        
        stops = [
            {"name": "Stop A"},
            {"name": "Stop B"},
            {"name": "Stop C"}
        ]
        
        # New arrival that matches the afternoon journey
        arrivals = [
            {
                "timestamp": "2025-07-03T14:20:00+01:00",
                "bus_id": "123",
                "trip_id": "TUBE_123_afternoon",
                "stop_name": "Stop B",
                "route": "TUBE",
                "direction": "inbound"
            }
        ]
        
        update_route_specific_sheet(worksheet, arrivals, stops)
        
        # Should update the afternoon journey row
        worksheet.update.assert_called()
        worksheet.append_rows.assert_not_called()
    
    def test_no_existing_data(self):
        """Test behavior when no existing data exists."""
        worksheet = MagicMock()
        worksheet.get_all_records.return_value = []
        
        stops = [{"name": "Stop A"}]
        
        arrivals = [
            {
                "timestamp": "2025-07-03T08:00:00+01:00",
                "bus_id": "123",
                "trip_id": "TUBE_123",
                "stop_name": "Stop A",
                "route": "TUBE",
                "direction": "outbound"
            }
        ]
        
        update_route_specific_sheet(worksheet, arrivals, stops)
        
        # Should create new row since no existing data
        worksheet.append_rows.assert_called()
        worksheet.update.assert_not_called()