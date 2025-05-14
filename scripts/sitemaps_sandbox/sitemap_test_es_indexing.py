import os
from dotenv import load_dotenv

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from search_gov_crawler.search_gov_spiders.spiders.domain_spider import DomainSpider

load_dotenv()

os.environ.setdefault("SPIDER_SPIDERMON_ENABLED", "False")

if __name__ == "__main__":

    new_urls = [
        "https://ioos.noaa.gov/project/ocean-enterprise-study/",
        "https://ioos.noaa.gov/about/ioos-history/"
    ]
    spider_args = {
        "allow_query_string": False,
        "allowed_domains": "ioos.noaa.gov",
        "deny_paths": None,
        "start_urls": ",".join(new_urls),
        "output_target": "elasticsearch",
        "prevent_follow": True,
        "depth_limit": 1,
    }
    spider_cls = DomainSpider
    process = CrawlerProcess(get_project_settings(), install_root_handler=False)
    process.crawl(spider_cls, **spider_args)
    process.start()
