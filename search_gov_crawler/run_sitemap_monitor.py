from search_gov_crawler.search_gov_spiders.crawl_sites import CrawlSites
from search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor import SitemapMonitor
from search_gov_crawler.scrapy_scheduler import CRAWL_SITES_FILE

if __name__ == "__main__":
    records = CrawlSites.from_file(file=CRAWL_SITES_FILE) 
    monitor = SitemapMonitor(records)
    monitor.run()
