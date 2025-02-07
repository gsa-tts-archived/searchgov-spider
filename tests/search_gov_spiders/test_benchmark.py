import os
import time
from datetime import UTC, datetime
from pathlib import Path


import pytest
from apscheduler.schedulers.blocking import BlockingScheduler
from freezegun import freeze_time

from search_gov_crawler import scrapy_scheduler
from search_gov_crawler.benchmark import (
    benchmark_from_args,
    benchmark_from_file,
    create_apscheduler_job,
    init_scheduler,
)


@pytest.mark.parametrize(("scrapy_max_workers", "expected_val"), [("100", 100), (None, 14)])
def test_init_scheduler(caplog, monkeypatch, scrapy_max_workers, expected_val):
    if scrapy_max_workers:
        monkeypatch.setenv("SCRAPY_MAX_WORKERS", scrapy_max_workers)
    else:
        monkeypatch.delenv("SCRAPY_MAX_WORKERS", raising=False)

    monkeypatch.setattr(os, "cpu_count", lambda: 10)

    with caplog.at_level("INFO"):
        init_scheduler()

    assert f"Max workers for schedule set to {expected_val}" in caplog.messages


@freeze_time("2024-01-01 00:00:00", tz_offset=0)
@pytest.mark.parametrize(("handle_javascript", "spider_arg"), [(True, "domain_spider_js"), (False, "domain_spider")])
def test_create_apscheduler_job(handle_javascript, spider_arg):
    test_args = {
        "name": "test",
        "allow_query_string": True,
        "allowed_domains": "example.com",
        "starting_urls": "https://www.example.com",
        "handle_javascript": handle_javascript,
        "output_target": "csv",
        "runtime_offset_seconds": 5,
    }

    assert create_apscheduler_job(**test_args) == {
        "func": scrapy_scheduler.run_scrapy_crawl,
        "id": f"benchmark - {test_args['name']}",
        "name": f"benchmark - {test_args['name']}",
        "next_run_time": datetime(2024, 1, 1, 0, 0, 5, tzinfo=UTC),
        "args": [
            spider_arg,
            test_args["allow_query_string"],
            test_args["allowed_domains"],
            test_args["starting_urls"],
            test_args["output_target"],
        ],
    }


class MockScheduler:
    @staticmethod
    def add_job(*_args, **_kwargs):
        return True

    @staticmethod
    def start():
        return True

    @staticmethod
    def shutdown():
        return True


def test_benchmark_from_args(caplog, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda x: True)
    monkeypatch.setattr("search_gov_crawler.benchmark.init_scheduler", lambda: MockScheduler())  # pylint: disable=unnecessary-lambda
    test_args = {
        "allow_query_string": True,
        "allowed_domains": "unit-test.example.com",
        "starting_urls": "https://unit-test.example.com",
        "handle_javascript": False,
        "output_target": "csv",
        "runtime_offset_seconds": 0,
    }
    with caplog.at_level("INFO"):
        benchmark_from_args(**test_args)

    expected_log_msg = (
        "Starting benchmark from args! "
        "allow_query_string=True allowed_domains=unit-test.example.com starting_urls=https://unit-test.example.com "
        "handle_javascript=False output_target=csv runtime_offset_seconds=0"
    )
    assert expected_log_msg in caplog.messages


def test_benchmark_from_file(caplog, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda x: True)
    monkeypatch.setattr("search_gov_crawler.benchmark.init_scheduler", lambda: MockScheduler())  # pylint: disable=unnecessary-lambda

    input_file = Path(__file__).parent / "crawl-sites-test.json"
    with caplog.at_level("INFO"):
        benchmark_from_file(input_file=input_file, runtime_offset_seconds=0)

    assert "Starting benchmark from file! input_file=crawl-sites-test.json runtime_offset_seconds=0" in caplog.messages


def test_benchmark_from_file_missing_file():
    input_file = Path("/does/not/exist.json")
    with pytest.raises(FileNotFoundError, match=f"Input file {input_file} does not exist!"):
        benchmark_from_file(input_file=input_file, runtime_offset_seconds=0)
