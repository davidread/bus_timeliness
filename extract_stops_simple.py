#!/usr/bin/env python3
"""
Simple extraction of stops from TransXChange XML files for each direction.
"""

import xml.etree.ElementTree as ET

from config import ROUTES_TO_ANALYZE


def get_stops_from_journey_pattern_sections(xml_file):
    """Extract all stops from JourneyPatternSections organized by direction."""

    # Load the XML file
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

    # Get stops for each direction from journey pattern sections
    direction_stops = {"inbound": [], "outbound": []}

    for jp_section in root.findall(".//txc:JourneyPatternSection", ns):
        section_id = jp_section.get("id")
        print(f"Processing section: {section_id}")

        # Get all stops in sequence from this section
        section_stops = []
        for timing_link in jp_section.findall(".//txc:JourneyPatternTimingLink", ns):
            # Check From stop
            from_elem = timing_link.find(".//txc:From", ns)
            if from_elem is not None:
                dest_display = from_elem.find("txc:DynamicDestinationDisplay", ns)
                stop_ref_elem = from_elem.find("txc:StopPointRef", ns)

                if dest_display is not None and stop_ref_elem is not None:
                    dest_text = dest_display.text
                    stop_id = stop_ref_elem.text

                    if stop_id in stops_dict:
                        stop_info = {"name": stops_dict[stop_id], "atco_code": stop_id}

                        # Determine direction based on destination
                        if "london" in dest_text.lower() or "victoria" in dest_text.lower():
                            if stop_info not in direction_stops["outbound"]:
                                direction_stops["outbound"].append(stop_info)
                        elif "oxford" in dest_text.lower():
                            if stop_info not in direction_stops["inbound"]:
                                direction_stops["inbound"].append(stop_info)

            # Check To stop
            to_elem = timing_link.find(".//txc:To", ns)
            if to_elem is not None:
                dest_display = to_elem.find("txc:DynamicDestinationDisplay", ns)
                stop_ref_elem = to_elem.find("txc:StopPointRef", ns)

                if dest_display is not None and stop_ref_elem is not None:
                    dest_text = dest_display.text
                    stop_id = stop_ref_elem.text

                    if stop_id in stops_dict:
                        stop_info = {"name": stops_dict[stop_id], "atco_code": stop_id}

                        # Determine direction based on destination
                        if "london" in dest_text.lower() or "victoria" in dest_text.lower():
                            if stop_info not in direction_stops["outbound"]:
                                direction_stops["outbound"].append(stop_info)
                        elif "oxford" in dest_text.lower():
                            if stop_info not in direction_stops["inbound"]:
                                direction_stops["inbound"].append(stop_info)

    return direction_stops


def main():
    """Extract and display stops for all configured routes and directions."""

    for route_config in ROUTES_TO_ANALYZE:
        route_name = route_config["route_name"]
        xml_file = f"timetable-{route_name}.xml"

        print(f"\n=== Processing route: {route_name} ===")

        try:
            direction_stops = get_stops_from_journey_pattern_sections(xml_file)

            for direction in route_config["directions"]:
                print(f"\n--- Direction: {direction} ---")

                stops = direction_stops.get(direction, [])
                if stops:
                    print(f"Found {len(stops)} stops:")
                    for i, stop in enumerate(stops, 1):
                        print(f"  {i:2d}. {stop['name']} ({stop['atco_code']})")
                else:
                    print("No stops found for this direction")

        except Exception as e:
            print(f"Error processing {route_name}: {e}")


if __name__ == "__main__":
    main()
