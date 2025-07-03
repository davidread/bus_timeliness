# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python project that tracks bus timeliness by collecting real-time bus position data from the UK's Bus Open Data Service (BODS) API and analyzing arrival patterns at stops. The system:

1. Polls BODS API every minute for bus positions
2. Tracks buses approaching and arriving at stops
3. Records arrival times in Google Sheets for analysis
4. Runs for 3-hour sessions using GitHub Actions

## Key Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
. venv/bin/activate

# Install dependencies
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-test.txt  # For testing
```

### Testing
```bash
# Run all tests
make test

# Run with coverage
make test-cov

# Quick test run
make test-fast

# Or use pytest directly
pytest tests/ -v
```

### Code Quality
```bash
# Run linting
make lint

# Format code
make format

# Run all quality checks
make quality

# Clean temporary files
make clean
```

### Running the Application
```bash
# Main application (requires API keys)
python get_bus_data.py
```

## Architecture Overview

### Core Components

- **`get_bus_data.py`** - Main application script that orchestrates the entire data collection process
- **`config.py`** - Configuration for routes to analyze and Google Sheets settings
- **`extract_stops.py`** & **`extract_stops_simple.py`** - Utilities for parsing TransXChange XML timetables

### Data Flow Architecture

1. **Data Collection** (`get_bus_data.py:30-95`)
   - Polls BODS API for real-time bus positions using SIRI XML format
   - Handles XML parsing and error recovery
   - Filters for configured routes only

2. **Stop Detection** (`get_bus_data.py:232-341`)
   - Parses TransXChange XML timetables to extract stop coordinates
   - Caches stop data for performance
   - Maps stops to specific route directions

3. **Arrival Detection** (`get_bus_data.py:469-553`)
   - Tracks bus state changes using global `_bus_previous_state`
   - Detects arrivals when bus transitions from "not at stop" to "at stop"
   - Uses 100-meter threshold for stop proximity

4. **Data Storage** (`get_bus_data.py:556-686`)
   - Updates Google Sheets with both raw position data and arrival times
   - Creates route-specific tabs with stop names as columns
   - **Journey Separation**: Automatically detects separate bus journeys (3+ hour gaps)
   - Creates new rows for different journeys, updates existing rows for same journey
   - Handles multiple journeys per bus per day without overwriting data

### State Management

The system maintains several global state variables:
- `_stops_cache` - Caches parsed stop data per route/direction
- `_bus_previous_state` - Tracks each bus's previous location state for arrival detection

### External Dependencies

- **BODS API** - Real-time bus position data via SIRI XML
- **Google Sheets** - Data storage and visualization
- **TransXChange XML** - Static timetable data for stop coordinates

## Testing Strategy

Tests are organized by functionality:
- **Unit tests** (`test_distance_calculations.py`) - Mathematical calculations
- **Arrival detection** (`test_arrival_detection.py`) - State transition logic
- **XML parsing** (`test_xml_parsing.py`) - SIRI and TransXChange formats
- **Data filtering** (`test_data_filtering.py`) - Route filtering logic

All external API calls are mocked to prevent live API usage during testing.

## Configuration

### Required API Keys
- **BODS API Key** - Store in `.bods_key` file or `BODS_KEY` environment variable
- **Google Service Account** - JSON file at `~/.gcloud/scraper-service-account-key.json` or `GOOGLE_SERVICE_ACCOUNT_KEY` environment variable

### Route Configuration
Routes are defined in `config.py` with:
- `route_name` - BODS route identifier
- `directions` - Array of "inbound"/"outbound" 
- `timetable_download_url` - TransXChange XML source

## Development Notes

- Uses 100-line limit for Black formatting
- Pytest with coverage reporting configured
- Ruff for additional linting beyond Black/isort
- Python 3.9+ target version
- All XML parsing uses ElementTree with proper namespace handling