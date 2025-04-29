from pathlib import Path
from typing import ClassVar

from spidermon import MonitorSuite
from spidermon.contrib.actions.email.ses import SendSESEmail
from spidermon.contrib.actions.reports.files import CreateFileReport
from spidermon.contrib.scrapy.monitors.monitors import (
    FinishReasonMonitor,
    ItemCountMonitor,
    PeriodicExecutionTimeMonitor,
    UnwantedHTTPCodesMonitor,
)


class CreateCustomFileReport(CreateFileReport):
    """Overrides the default CreateFileReport to use a custom template."""

    template_paths: ClassVar[list] = [Path(__file__).parent / "actions"]


class SpiderCloseMonitorSuite(MonitorSuite):
    """
    These monitors will only run once when the spider is closed.

    These will compare the "items_scraped_count" to SPIDERMON_MIN_ITEMS. If the items_scraped_count is less
    than SPIDERMON_MIN_ITEMS it will count as a failure. UnwantedHTTPCodesMonitor checks the count of the unwanted
    http codes (SPIDERMON_UNWANTED_HTTP_CODES). If any of those codes have a count higher than
    SPIDERMON_UNWANTED_HTTP_CODES_MAX_COUNT it will count as a failure.

    A failed action will create a report which will be saved in the search_gov_crawler directory
    and sent to SPIDERMON_EMAIL_TO using Amazon SES.

    The run time at the end of the spider will fail if the spider has been running longer than
    SPIDERMON_MAX_EXECUTION_TIME.

    If the finish reason is not "finished" it will count as a failure. This is the default but can be mmodified
    using SPIDERMON_EXPECTED_FINISH_REASONS.

    Relevant settings are all defined in search_gov_crawler/search_gov_spiders/settings.py
    """

    monitors: ClassVar[list] = [
        ItemCountMonitor,
        UnwantedHTTPCodesMonitor,
        PeriodicExecutionTimeMonitor,
        FinishReasonMonitor,
    ]
    monitors_failed_actions: ClassVar[list] = [CreateCustomFileReport, SendSESEmail]
