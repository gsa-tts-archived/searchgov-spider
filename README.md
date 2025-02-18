# searchgov-spider
The home for the spider that supports [Search.gov](https://www.search.gov).

#### Table of contents
* [About](#about)
  * [Technologies](#technologies)
  * [Core Scrapy File Strcture](#core-scrapy-file-structure)
  * [Scrapy Web Crawler](#scrapy-web-crawler)
* [Quick Start](#quick-start)
* [Helpful Links](#helpful-links)
* [Advanced Setup and Use](docs/advanced_setup_and_use.md)
* [Deployments](docs/deployments.md)
* [Operations](docs/operations.md)
* [Running Scrapydweb UI](docs/running_scrapydwebui.md)

## About
With the move away from using Bing to provide search results for some domains, we need a solution that can index sites that were previously indexed by Bing and/or that do not have standard sitemaps.  Additionally, the Scrutiny desktop application is being run manually to provide coverage for a few dozen domains that cannot be otherwise indexed.  The spider application is our solution to both the Bing problem and the removal of manual steps.  The documentation here represents the most current state of the application and our design.

### Technologies
We currently run python 3.12.  The spider is based on the open source [scrapy](https://scrapy.org/) framework.  On top of that we use several other open source libraries and scrapy plugins.  See our [requirements file](search_gov_crawler/requirements.txt) for more details.

### Core Scrapy File Structure
*Note: Other files and directories are within the repository but the folders and files below relate to those needed for the scrapy framework.

```bash
├── search_gov_crawler              # scrapy root
|   ├── elasticsearch               # code related to indexing content in elasticsearch
│   ├── search_gov_spider           # scrapy project dir
│   │   ├── extensions              # custom scrapy extensions
│   │   ├── helpers                 # common functions
│   │   ├── spiders                 # all search_gov_spider spiders
│   │   │   ├── domain_spider.py    # for html pages
│   │   │   ├── domain_spider_js.py # for js pages
│   │   ├── utility_files           # json files with default domains to scrape
│   │   ├── items.py                # defines individual output of scrapes
│   │   ├── middlewares.py          # custom middleware code
│   │   ├── monitors.py             # custom spidermon monitors
│   │   ├── pipelines.py            # custom item pipelines
│   │   ├── settings.py             # settings that control all scrapy jobs
│   ├── scrapy.cfg
```

## Quick Start

1. Insall and activate virtual environment:
```bash
python -m venv venv
. venv/bin/activate
```

2. Install required python modules:
```bash
# make sure the virtual environment is activate
pip install -r ./search_gov_crawler/requirements.txt
playwright install --with-deps
playwright install chrome --force
```

3. Run A Spider For A Specific Domain:
In the same directory specified above, enter the command below, adding the domain and starting URL for the crawler:
```bash
# to run for a non-js domain:
scrapy crawl domain_spider -a allowed_domains=quotes.toscrape.com -a start_urls=https://quotes.toscrape.com -a output_target=csv

# or to run for a js domain
scrapy crawl domain_spider_js -a allowed_domains=quotes.toscrape.com -a start_urls=https://quotes.toscrape.com/js -a output_target=csv
```

The output of this scrape is one or more csv files containing URLs in the [output directory](search_gov_crawler/output).

For more advanced usage, see the [Advanced Setup and Use Page](docs/advanced_setup_and_use.md)

## Helpful Links
