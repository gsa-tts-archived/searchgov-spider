import os
import json
from dotenv import load_dotenv
from pathlib import Path

import requests
import xml.etree.ElementTree as ET
import time
import logging
from datetime import datetime
import os
from typing import Dict, List, Set, Tuple
import hashlib
import heapq

from pythonjsonlogger.json import JsonFormatter

from search_gov_crawler.search_gov_spiders.extensions.json_logging import LOG_FMT
from search_gov_crawler.search_gov_spiders.crawl_sites import CrawlSite
from search_gov_crawler.search_gov_spiders.sitemaps.sitemap_finder import SitemapFinder


from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from search_gov_crawler.search_gov_spiders.spiders.domain_spider import DomainSpider
from search_gov_crawler.search_gov_spiders.spiders.domain_spider_js import (
    DomainSpiderJs,
)

load_dotenv()

logging.basicConfig(level=os.environ.get("SCRAPY_LOG_LEVEL", "INFO"))
logging.getLogger().handlers[0].setFormatter(JsonFormatter(fmt=LOG_FMT))
log = logging.getLogger("search_gov_crawler.sitemaps")


CRAWL_SITES_FILE = (
    Path(__file__).parent / "domains" / os.environ.get("SPIDER_CRAWL_SITES_FILE_NAME", "crawl-sites-production.json")
)

HOME_DIR = os.path.expanduser("~")

def get_json_dict(file_path: Path) -> list[CrawlSite]:
    records = json.loads(file_path.read_text(encoding="UTF-8"))
    crawl_sites = [CrawlSite(**record) for record in records]
    return crawl_sites

class SitemapMonitor:
    def __init__(self, records: List[CrawlSite]):
        """
        Initialize the SitemapMonitor.
        
        Args:
            sitemap_configs: List of tuples containing (sitemap_url, check_interval_in_hours)
        """
        # Convert hours to seconds for internal use
        records = [(record.check_sitemap_hours * 3600) for record in records]
        self.records_map = {record[record.sitemap_url]: record for record in records}
        self.records = records
        self.stored_sitemaps: Dict[str, Set[str]] = {}
        self.next_check_times: Dict[str, float] = {}
        
        # Create data directory if it doesn't exist
        sitemap_dir = HOME_DIR / "sitemap_data"
        os.makedirs(sitemap_dir, exist_ok=True)
        
        # Load any previously stored sitemaps
        self._load_stored_sitemaps()
        
        # Initialize the next check times
        current_time = time.time()
        for record in self.records:
            self.next_check_times[record.sitemap_url] = current_time
    
    def _load_stored_sitemaps(self):
        """Load previously stored sitemaps from disk if they exist."""
        for record in self.records:
            url_hash = hashlib.md5(record.sitemap_url.encode()).hexdigest()
            file_path = HOME_DIR / "sitemap_data" / f"{url_hash}.txt"
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        urls = set(line.strip() for line in f.readlines())
                        self.stored_sitemaps[record.sitemap_url] = urls
                        log.info(f"Loaded {len(urls)} URLs from stored sitemap for {record.sitemap_url}")
                except Exception as e:
                    log.error(f"Error loading stored sitemap for {record.sitemap_url}: {e}")
                    self.stored_sitemaps[record.sitemap_url] = set()
            else:
                self.stored_sitemaps[record.sitemap_url] = set()
                
    def _save_sitemap(self, sitemap_url: str, urls: Set[str]):
        """Save sitemap URLs to disk."""
        url_hash = hashlib.md5(sitemap_url.encode()).hexdigest()
        file_path = HOME_DIR / "sitemap_data" / f"{url_hash}.txt"
        
        try:
            with open(file_path, "w") as f:
                for url in sorted(urls):
                    f.write(f"{url}\n")
            log.info(f"Saved {len(urls)} URLs for {sitemap_url}")
        except Exception as e:
            log.error(f"Error saving sitemap for {sitemap_url}: {e}")
    
    def fetch_sitemap(self, url: str) -> Set[str]:
        """
        Fetch and parse a sitemap XML file.
        
        Args:
            url: The URL of the sitemap to fetch
            
        Returns:
            A set of URLs found in the sitemap
        """
        try:
            log.info(f"Fetching sitemap from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # Parse the XML
            root = ET.fromstring(response.content)
            
            # Extract URLs based on the namespace
            # Handle both standard sitemaps and sitemap indexes
            urls = set()
            
            # Determine the namespace
            ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
            
            # Check if this is a sitemap index
            if root.tag.endswith("sitemapindex"):
                # Process each sitemap in the index
                for sitemap in root.findall(f"{ns}sitemap"):
                    loc = sitemap.find(f"{ns}loc")
                    if loc is not None and loc.text:
                        # Recursively fetch each sitemap
                        child_urls = self.fetch_sitemap(loc.text)
                        urls.update(child_urls)
            else:
                # Process regular sitemap
                for url_element in root.findall(f"{ns}url"):
                    loc = url_element.find(f"{ns}loc")
                    if loc is not None and loc.text:
                        urls.add(loc.text)
            
            log.info(f"Found {len(urls)} URLs in sitemap {url}")
            return urls
            
        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching sitemap {url}: {e}")
            return set()
        except ET.ParseError as e:
            log.error(f"Error parsing sitemap XML from {url}: {e}")
            return set()
        except Exception as e:
            log.error(f"Unexpected error processing sitemap {url}: {e}")
            return set()
    
    def check_for_changes(self, sitemap_url: str) -> Tuple[Set[str], int]:
        """
        Check a sitemap for new URLs.
        
        Args:
            sitemap_url: The URL of the sitemap to check
            
        Returns:
            Tuple of (new URLs, total URLs count)
        """
        try:
            current_urls = self.fetch_sitemap(sitemap_url)
            
            # Get previously stored URLs or empty set if first run
            previous_urls = self.stored_sitemaps.get(sitemap_url, set())
            
            # Find new URLs
            new_urls = current_urls - previous_urls
            
            # Update stored URLs
            self.stored_sitemaps[sitemap_url] = current_urls
            self._save_sitemap(sitemap_url, current_urls)
            
            return new_urls, len(current_urls)
        except Exception as e:
            log.error(f"Error checking for changes in {sitemap_url}: {e}")
            return set(), 0
    
    def get_check_interval(self, url: str) -> int:
        """Get the check interval for a specific URL in seconds."""
        for record in self.records:
            if record.sitemap_url == url:
                return record.check_sitemap_hours
        # Default to 24 hours if not found (shouldn't happen with proper initialization)
        return 86400
    
    def run(self):
        """Run the sitemap monitor continuously."""
        log.info(f"Starting Sitemap Monitor for {len(self.records)} sitemaps")
        
        # Log the check intervals for each sitemap
        for record in self.records:
            hours = record.check_sitemap_hours / 3600
            log.info(f"Check interval for {record.sitemap_url}: {hours:.1f} hours")
        
        # Priority queue for efficient scheduling
        check_queue = []
        
        # Initialize the priority queue with all sitemaps
        for record in self.records:
            heapq.heappush(check_queue, (self.next_check_times[record.sitemap_url], record.sitemap_url))
        
        try:
            while True:
                if not check_queue:
                    log.error("Check queue is empty. This shouldn't happen.")
                    break
                
                # Get the next sitemap to check
                next_check_time, sitemap_url = heapq.heappop(check_queue)
                
                # Calculate sleep time
                current_time = time.time()
                sleep_time = max(0, next_check_time - current_time)
                
                if sleep_time > 0:
                    next_check_str = datetime.fromtimestamp(next_check_time).strftime("%Y-%m-%d %H:%M:%S")
                    log.info(f"Waiting until {next_check_str} to check {sitemap_url} (sleeping for {sleep_time:.1f} seconds)")
                    time.sleep(sleep_time)
                
                # Process the sitemap
                log.info(f"Processing sitemap: {sitemap_url}")
                new_urls, total_count = self.check_for_changes(sitemap_url)
                
                # Report findings
                if new_urls:
                    log.info(f"Found {len(new_urls)} new URLs in {sitemap_url}")
                    log.info("New URLs:")
                    
                    for url in sorted(new_urls):
                        log.info(f"  - {url}")
                    
                    record = self.records_map[sitemap_url]

                    spider = DomainSpider(
                        allow_query_string=record.allow_query_string,
                        allowed_domains=None,
                        deny_paths=record.deny_paths,
                        start_urls=",".join(new_urls),
                        output_target=record.output_target,
                        prevent_follow=True
                    )

                    process = CrawlerProcess(get_project_settings(), install_root_handler=False)
                    process.crawl(spider)
                    process.start()

                else:
                    log.info(f"No new URLs found in {sitemap_url}")
                
                log.info(f"Total URLs in sitemap: {total_count}")
                
                # Schedule the next check for this sitemap
                check_interval = self.get_check_interval(sitemap_url)
                self.next_check_times[sitemap_url] = time.time() + check_interval
                next_check_str = datetime.fromtimestamp(self.next_check_times[sitemap_url]).strftime("%Y-%m-%d %H:%M:%S")
                log.info(f"Next check for {sitemap_url} scheduled at {next_check_str}")
                
                # Add back to the queue with updated time
                heapq.heappush(check_queue, (self.next_check_times[sitemap_url], sitemap_url))
                
        except KeyboardInterrupt:
            log.info("Sitemap Monitor stopped by user")
        except Exception as e:
            log.error(f"Sitemap Monitor stopped due to error: {e}")
            raise

if __name__ == "__main__":
    records = get_json_dict(CRAWL_SITES_FILE)

    sitemap_finder = SitemapFinder()

    sitemap_configs = []
    
    for record in records:
        if not record.sitemap_url:
            starting_url = record.starting_urls.split(",")[0]
            record.sitemap_url = sitemap_finder.find(starting_url)

    
    monitor = SitemapMonitor(records)
    monitor.run()      
