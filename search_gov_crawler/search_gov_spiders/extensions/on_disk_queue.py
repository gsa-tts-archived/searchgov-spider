import logging
from pathlib import Path
from typing import Self

from scrapy.crawler import Crawler
from scrapy.exceptions import NotConfigured
from scrapy.signals import spider_closed
from scrapy.spiders import Spider


class OnDiskSchedulerQueue:
    """Custom scrapy extension that helps clean up the on-disk scheduler queue directory when a spider is finished"""

    setting_key: str = "JOBDIR"

    def remove_directory(self, directory: Path) -> None:
        """Recusrively remove a directory and contents"""

        for item in directory.iterdir():
            if item.is_dir():
                self.remove_directory(item)
            else:
                item.unlink()

        directory.rmdir()

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> Self:
        """
        Required extension method that checks for configuration and connects extension methons to signals
        """
        if not crawler.settings.get(cls.setting_key):
            msg = f"OnDiskSchedulerQueue extension is listed in settings.EXTENSIONS but {cls.setting_key} is not set."
            raise NotConfigured(msg)

        ext = cls()
        crawler.signals.connect(ext.spider_closed, signal=spider_closed)
        return ext

    def spider_closed(self, spider: Spider) -> None:
        """Clean up jobs directory when spider is finished"""

        spider_log = logging.getLogger(spider.name)
        job_dir = spider.settings.get(self.setting_key)
        self.remove_directory(Path(job_dir))
        spider_log.info("Removed %s %s at end of spider.", self.setting_key, job_dir)
