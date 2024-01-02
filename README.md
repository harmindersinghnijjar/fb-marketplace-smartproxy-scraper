# Facebook Marketplace Smartproxy Scraper

This repository houses a Python-based scraper specifically designed for extracting vehicle listings from Facebook Marketplace in Canadian cities. It leverages Smartproxy, a leading proxy service provider, to facilitate efficient and anonymous data collection.

## Features

- **Targeted Scraping**: Focused on Canadian cities for a region-specific dataset.
- **Proxy Integration**: Uses Smartproxy for reliable and undetected scraping operations.
- **Data Extraction**: Captures key details of vehicle listings, including price, model, location, and more.
- **SQLite Database**: Stores scraped data in an SQLite database for easy access and analysis.

## Prerequisites

Before running the scraper, ensure you have the following:

- Python 3.x installed.
- Access to Smartproxy services.
- Required Python libraries installed (`requests`, `beautifulsoup4`, `sqlite3`, etc.).

## Installation

1. Clone the repository:

```
https://github.com/harmindersinghnijjar/fb-marketplace-smartproxy-scraper.git
```


2. Navigate to the cloned directory and install the required libraries:

```
pip install -r requirements.txt
```


## Usage

To run the scraper:

```
python fb-marketplace-smartproxy-scraper.py
```

## Configuring the Scraper

- Set your Smartproxy details in the configuration file.
- Customize the search queries and target cities as per your requirements.

## Contributing

Contributions to enhance the functionality, improve efficiency, or fix bugs are always welcome. Please read `CONTRIBUTING.md` for guidelines on how to submit your contributions.


## Disclaimer

This tool is for educational and research purposes only. Users must adhere to Facebook's terms of service and Smartproxy's usage policy.

## Acknowledgements

- Smartproxy for their reliable proxy solutions.
- Python community for the wealth of libraries and resources.



