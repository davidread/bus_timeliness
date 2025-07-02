"""
Test XML parsing functionality.
"""

import xml.etree.ElementTree as ET
from unittest.mock import mock_open

from get_bus_data import extract_stops_from_xml, get_bus_positions


class TestXMLParsing:
    """Test XML parsing functions."""

    def test_get_bus_positions_siri_xml(self, mocker):
        """Test parsing SIRI XML response."""
        # Mock SIRI XML response
        siri_xml = """<?xml version="1.0"?>
        <Siri xmlns="http://www.siri.org.uk/siri">
            <ServiceDelivery>
                <VehicleMonitoringDelivery>
                    <VehicleActivity>
                        <MonitoredVehicleJourney>
                            <LineRef>TEST</LineRef>
                            <DirectionRef>inbound</DirectionRef>
                            <VehicleLocation>
                                <Longitude>-0.1278</Longitude>
                                <Latitude>51.5074</Latitude>
                            </VehicleLocation>
                            <VehicleRef>BUS001</VehicleRef>
                        </MonitoredVehicleJourney>
                        <RecordedAtTime>2025-01-01T12:00:00</RecordedAtTime>
                    </VehicleActivity>
                </VehicleMonitoringDelivery>
            </ServiceDelivery>
        </Siri>"""

        # Mock the HTTP request
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = siri_xml
        mock_response.headers = {"content-type": "text/xml"}
        mock_response.raise_for_status.return_value = None

        mocker.patch("requests.get", return_value=mock_response)
        mocker.patch("builtins.open", mock_open())

        result = get_bus_positions("test_api_key", "TEST")

        assert "entity" in result
        assert len(result["entity"]) == 1

        bus = result["entity"][0]
        assert bus["vehicle"]["vehicle"]["id"] == "BUS001"
        assert bus["vehicle"]["position"]["latitude"] == 51.5074
        assert bus["vehicle"]["position"]["longitude"] == -0.1278
        assert bus["vehicle"]["trip"]["route_id"] == "TEST"
        assert bus["vehicle"]["trip"]["trip_headsign"] == "inbound"

    def test_get_bus_positions_empty_response(self, mocker):
        """Test handling of empty API response."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = ""
        mock_response.headers = {"content-type": "text/xml"}
        mock_response.raise_for_status.return_value = None

        mocker.patch("requests.get", return_value=mock_response)
        mocker.patch("builtins.open", mock_open())

        result = get_bus_positions("test_api_key", "TEST")

        assert result == {"entity": []}

    def test_get_bus_positions_invalid_xml(self, mocker):
        """Test handling of invalid XML."""
        mock_response = mocker.Mock()
        mock_response.status_code = 200
        mock_response.text = "Invalid XML content"
        mock_response.headers = {"content-type": "text/xml"}
        mock_response.raise_for_status.return_value = None

        mocker.patch("requests.get", return_value=mock_response)
        mocker.patch("builtins.open", mock_open())

        result = get_bus_positions("test_api_key", "TEST")

        assert result == {"entity": []}

    def test_extract_stops_from_xml_with_coordinates(self, mocker):
        """Test extracting stops from TransXChange XML with coordinates."""
        # Mock TransXChange XML with coordinates
        transxchange_xml = """<?xml version="1.0"?>
        <TransXChange xmlns="http://www.transxchange.org.uk/">
            <StopPoints>
                <AnnotatedStopPointRef>
                    <StopPointRef>STOP001</StopPointRef>
                    <CommonName>Test Stop</CommonName>
                </AnnotatedStopPointRef>
            </StopPoints>
            <RouteSections>
                <RouteSection>
                    <RouteLink>
                        <From>
                            <StopPointRef>STOP001</StopPointRef>
                        </From>
                        <Track>
                            <Mapping>
                                <Location>
                                    <Longitude>-0.1278</Longitude>
                                    <Latitude>51.5074</Latitude>
                                </Location>
                            </Mapping>
                        </Track>
                    </RouteLink>
                </RouteSection>
            </RouteSections>
            <Services>
                <Service>
                    <JourneyPatternSections>
                        <JourneyPatternSection>
                            <JourneyPatternTimingLink>
                                <From>
                                    <StopPointRef>STOP001</StopPointRef>
                                    <DynamicDestinationDisplay>to Oxford</DynamicDestinationDisplay>
                                </From>
                            </JourneyPatternTimingLink>
                        </JourneyPatternSection>
                    </JourneyPatternSections>
                </Service>
            </Services>
        </TransXChange>"""

        # Mock file operations
        mock_tree = ET.ElementTree(ET.fromstring(transxchange_xml))
        mocker.patch("xml.etree.ElementTree.parse", return_value=mock_tree)

        # Clear cache
        from get_bus_data import _stops_cache

        _stops_cache.clear()

        stops = extract_stops_from_xml("TEST", "inbound")

        assert len(stops) == 1
        assert stops[0]["name"] == "Test Stop"
        assert stops[0]["atco_code"] == "STOP001"
        assert stops[0]["lat"] == 51.5074
        assert stops[0]["lon"] == -0.1278

    def test_extract_stops_caching(self, mocker):
        """Test that stop extraction results are cached."""
        # Mock the parse function to track calls
        mock_parse = mocker.patch("xml.etree.ElementTree.parse")

        # Mock empty XML
        empty_xml = ET.ElementTree(
            ET.fromstring('<TransXChange xmlns="http://www.transxchange.org.uk/"></TransXChange>')
        )
        mock_parse.return_value = empty_xml

        # Clear cache
        from get_bus_data import _stops_cache

        _stops_cache.clear()

        # First call should parse XML
        extract_stops_from_xml("TEST", "inbound")
        assert mock_parse.call_count == 1

        # Second call should use cache
        extract_stops_from_xml("TEST", "inbound")
        assert mock_parse.call_count == 1  # Should not increase
