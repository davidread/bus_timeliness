#!/usr/bin/env python3
"""
Extract stops from TransXChange XML files for each route direction.
"""

import xml.etree.ElementTree as ET

from config import ROUTES_TO_ANALYZE


def extract_stops_from_xml(route_name, direction):
    """Extract stops from downloaded TransXChange XML file for specific route/direction."""

    # Load the XML file
    xml_file = f"timetable-{route_name}.xml"
    tree = ET.parse(xml_file)
    root = tree.getroot()

    # Define namespace
    ns = {"txc": "http://www.transxchange.org.uk/"}

    # Get all stop points first
    stops_dict = {}
    for stop_point in root.findall(".//txc:AnnotatedStopPointRef", ns):
        stop_ref = stop_point.find("txc:StopPointRef", ns).text
        common_name = stop_point.find("txc:CommonName", ns).text
        stops_dict[stop_ref] = common_name

    print(f"Found {len(stops_dict)} total stops in XML")

    # Find services that match our route
    route_stops = []
    for service in root.findall(".//txc:Service", ns):
        # Check if this service has our route
        for line in service.findall(".//txc:LineName", ns):
            if line.text == route_name:
                print(f"Found service for route {route_name}")

                # Find journey patterns for this direction
                for journey_pattern in service.findall(".//txc:JourneyPattern", ns):
                    # Get direction information
                    direction_elem = journey_pattern.find(".//txc:Direction", ns)

                    if direction_elem is not None:
                        direction_text = direction_elem.text
                        print(f"Found direction: {direction_text}")

                        # Match direction - check for inbound/outbound
                        direction_match = False
                        if direction == "inbound" and (
                            "inbound" in direction_text.lower()
                            or "oxford" in direction_text.lower()
                        ):
                            direction_match = True
                        elif direction == "outbound" and (
                            "outbound" in direction_text.lower()
                            or "london" in direction_text.lower()
                        ):
                            direction_match = True

                        if direction_match:
                            print(f"Matched direction {direction} with {direction_text}")

                            # Get stop sequence for this journey pattern
                            stop_sequence = []

                            # Look for JourneyPatternSectionRefs to get the actual route
                            for jp_section_ref in journey_pattern.findall(
                                ".//txc:JourneyPatternSectionRef", ns
                            ):
                                section_id = jp_section_ref.text

                                # Find the corresponding JourneyPatternSection
                                for jp_section in root.findall(
                                    f'.//txc:JourneyPatternSection[@id="{section_id}"]', ns
                                ):
                                    # Get timing links which contain the stops
                                    for timing_link in jp_section.findall(
                                        ".//txc:JourneyPatternTimingLink", ns
                                    ):
                                        # Get From stop
                                        from_stop = timing_link.find(
                                            ".//txc:From/txc:StopPointRef", ns
                                        )
                                        if from_stop is not None:
                                            stop_id = from_stop.text
                                            if stop_id in stops_dict:
                                                stop_name = stops_dict[stop_id]
                                                if {
                                                    "name": stop_name,
                                                    "atco_code": stop_id,
                                                } not in stop_sequence:
                                                    stop_sequence.append(
                                                        {"name": stop_name, "atco_code": stop_id}
                                                    )

                                        # Get To stop
                                        to_stop = timing_link.find(".//txc:To/txc:StopPointRef", ns)
                                        if to_stop is not None:
                                            stop_id = to_stop.text
                                            if stop_id in stops_dict:
                                                stop_name = stops_dict[stop_id]
                                                if {
                                                    "name": stop_name,
                                                    "atco_code": stop_id,
                                                } not in stop_sequence:
                                                    stop_sequence.append(
                                                        {"name": stop_name, "atco_code": stop_id}
                                                    )

                            if stop_sequence:
                                route_stops = stop_sequence
                                print(f"Found {len(route_stops)} stops for {direction}")
                                return route_stops  # Return immediately when we find stops

                if route_stops:
                    break

        if route_stops:
            break

    return route_stops


def main():
    """Extract and display stops for all configured routes and directions."""

    for route_config in ROUTES_TO_ANALYZE:
        route_name = route_config["route_name"]
        print(f"\n=== Processing route: {route_name} ===")

        for direction in route_config["directions"]:
            print(f"\n--- Direction: {direction} ---")

            try:
                stops = extract_stops_from_xml(route_name, direction)

                if stops:
                    print(f"Extracted {len(stops)} stops:")
                    for i, stop in enumerate(stops, 1):
                        print(f"  {i:2d}. {stop['name']} ({stop['atco_code']})")
                else:
                    print("No stops found for this direction")

            except Exception as e:
                print(f"Error extracting stops for {route_name} {direction}: {e}")


if __name__ == "__main__":
    main()
