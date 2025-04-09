from pathlib import Path
from spidermon import MonitorSuite
from spidermon.contrib.actions.email.ses import SendSESEmail
from spidermon.contrib.actions.reports.files import CreateFileReport
from spidermon.contrib.scrapy.monitors.monitors import (
    ItemCountMonitor,
    UnwantedHTTPCodesMonitor,
    PeriodicItemCountMonitor,
    PeriodicExecutionTimeMonitor,
)


class CreateCustomFileReport(CreateFileReport):
    template_paths = [Path(__file__).parent / "actions"]


class SpiderCloseMonitorSuite(MonitorSuite):
    monitors = [ItemCountMonitor, UnwantedHTTPCodesMonitor]

    monitors_failed_actions = [CreateCustomFileReport, SendSESEmail]


class PeriodicMonitorSuite(MonitorSuite):
    monitors = [PeriodicItemCountMonitor, PeriodicExecutionTimeMonitor]

    monitors_failed_actions = [CreateCustomFileReport, SendSESEmail]
