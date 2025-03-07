import json
from pathlib import Path

import pytest

from search_gov_crawler.search_gov_spiders.crawl_sites import CrawlSites


@pytest.fixture(name="crawl_sites_test_file")
def fixture_crawl_sites_test_file() -> Path:
    return Path(__file__).parent / "crawl-sites-test.json"


@pytest.fixture(name="crawl_sites_test_file_json")
def fixture_crawl_sites_test_file_json(crawl_sites_test_file) -> dict:
    return json.loads(crawl_sites_test_file.resolve().read_text())


@pytest.fixture(name="crawl_sites_test_file_dataclass")
def fixture_crawl_sites_test_file_dataclass(crawl_sites_test_file) -> CrawlSites:
    return CrawlSites.from_file(file=crawl_sites_test_file)
