# Bus timeliness

![Tests](https://github.com/USER/REPO/workflows/Tests/badge.svg)
[![Coverage](https://codecov.io/gh/USER/REPO/branch/main/graph/badge.svg)](https://codecov.io/gh/USER/REPO)

Calculates the arrival time distribution for bus routes.

## Setup

1. Get a BODS API key from https://data.bus-data.dft.gov.uk/account/settings/ and save it in `.bods_key`

2. Python setup

```
python3 -m venv venv
. venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -r requirements-test.txt  # For running tests
```

3. GSheet setup

For uploading results to the Google Sheets, setup and download the Google Service Account token, that has permission to write to the sheet:

* Go to [Google Cloud Console](https://console.cloud.google.com/)
* Select project "Job Scraper" (or create it)
* In APIs, enable the Google Sheets API
* In Google Sheets API, create a Service Account, noting its email address
* Download the service account key JSON file as `~/.gcloud/scraper-service-account-key.json`
* In the Sheet, share it with the service account's email address


## Run

```
. venv/bin/activate
python get_bus_data.py
```

## Tests

Run the comprehensive test suite:

```sh
# Run all tests
make test

# Run tests with coverage
make test-cov

# Quick test run
make test-fast

# Or use pytest directly
. venv/bin/activate
pytest tests/ -v
```

The test suite includes:
- **Unit tests** for distance calculations and coordinate handling
- **Arrival detection tests** with state tracking validation
- **XML parsing tests** for SIRI and TransXChange formats
- **Data filtering tests** for bus route filtering and validation
- **Mocked external dependencies** to avoid API calls during testing

## Tech choices

* Input data about buses is from BODS, since it's easy to get hold of
* Data on arrival times is stored in Google Sheet, for easy visibility, and free
* Python is preferred language by the author
* gspread is the python library for GSheet, with biggest community base, and ease of adding rows
* pandas dataframe is great for storing the tabular data in python
* GitHub Actions for running this on a schedule, because it's free and stores the log output
