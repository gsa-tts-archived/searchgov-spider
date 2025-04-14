from apscheduler.job import Job


class SpiderJob(Job):
    """
    Custom job class for Spier Scrapy jobs to add to .
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_queued = False
