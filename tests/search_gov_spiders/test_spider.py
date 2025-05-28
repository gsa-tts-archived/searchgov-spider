import re

import pytest
from scrapy.http.request import Request
from scrapy.http.response import Response

from search_gov_crawler.search_gov_spiders.spiders.domain_spider import DomainSpider
from search_gov_crawler.search_gov_spiders.spiders.domain_spider_js import DomainSpiderJs

TEST_URL = "http://example.com"


@pytest.fixture(name="spider", params=[DomainSpider(output_target="csv"), DomainSpiderJs(output_target="csv")])
def fixture_spider(request):
    return request.param


def get_results(spider, content: str):
    request = Request(url=TEST_URL, encoding="utf-8")

    response = Response(url=TEST_URL, request=request, headers={"content-type": content})

    spider.output_target = "csv"
    spider.allowed_domains = ["example.com"]
    return next(spider.parse_item(response), None)


def test_valid_content(spider):
    results = get_results(spider, "text/html")
    assert results is not None and results.get("url") == TEST_URL


def test_valid_content_plus(spider):
    results = get_results(spider, "text/html;utf-8")
    assert results is not None and results.get("url") == TEST_URL


def test_invalid_content(spider):
    results = get_results(spider, "media/image")
    assert results is None


INVALID_ARGS_TEST_CASES = [
    (
        DomainSpider,
        {"allowed_domains": "test.example.com", "output_target": "csv"},
        "Invalid arguments: allowed_domains and start_urls must be used together or not at all.",
    ),
    (
        DomainSpiderJs,
        {"allowed_domains": "test.example.com", "output_target": "csv"},
        "Invalid arguments: allowed_domains and start_urls must be used together or not at all.",
    ),
    (
        DomainSpider,
        {"allowed_domains": "test.example.com", "start_urls": "http://test.example.com/", "output_target": "yaml"},
        "Invalid arguments: output_target must be one of the following: ['csv', 'endpoint', 'elasticsearch']",
    ),
    (
        DomainSpiderJs,
        {"allowed_domains": "test.example.com", "start_urls": "http://test.example.com/", "output_target": "yaml"},
        "Invalid arguments: output_target must be one of the following: ['csv', 'endpoint', 'elasticsearch']",
    ),
    (
        DomainSpider,
        {"output_target": "yaml"},
        "Invalid arguments: output_target must be one of the following: ['csv', 'endpoint', 'elasticsearch']",
    ),
    (
        DomainSpiderJs,
        {"output_target": "yaml"},
        "Invalid arguments: output_target must be one of the following: ['csv', 'endpoint', 'elasticsearch']",
    ),
]


@pytest.mark.parametrize(("spider_cls", "kwargs", "msg"), INVALID_ARGS_TEST_CASES)
def test_invalid_args(spider_cls, kwargs, msg):
    with pytest.raises(ValueError, match=re.escape(msg)):
        spider_cls(**kwargs)


@pytest.fixture(name="spider_args")
def fixture_spider_args() -> dict:
    return {
        "allowed_domains": "example.com",
        "start_urls": "http://example.com/",
        "output_target": "csv",
        "allow_query_string": True,
        "deny_paths": "/deny/path",
        "prevent_follow": False,
    }


@pytest.fixture(name="domain_spider")
def fixture_domain_spider(spider_args):
    return DomainSpider(**spider_args)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("allowed_domains", ["example.com"]),
        ("start_urls", ["http://example.com/"]),
        ("output_target", "csv"),
        ("allow_query_string", True),
        ("_deny_paths", "/deny/path"),
    ],
)
def test_domain_spider_init(domain_spider, attribute, value):
    assert getattr(domain_spider, attribute) == value


@pytest.fixture(name="domain_spider_js")
def fixture_domain_spider_js(spider_args):
    return DomainSpiderJs(**spider_args)


@pytest.mark.parametrize(
    ("attribute", "value"),
    [
        ("allowed_domains", ["example.com"]),
        ("start_urls", ["http://example.com/"]),
        ("output_target", "csv"),
        ("allow_query_string", True),
        ("_deny_paths", "/deny/path"),
    ],
)
def test_domain_spider_js_init(domain_spider_js, attribute, value):
    assert getattr(domain_spider_js, attribute) == value


@pytest.mark.parametrize(
    ("spider_cls", "allow_query_string"),
    [
        (DomainSpider, "False"),
        (DomainSpider, "something else"),
        (DomainSpiderJs, "false"),
        (DomainSpiderJs, "not a boolean"),
    ],
)
def test_spider_init_allow_query_string_str_input(spider_cls, spider_args, allow_query_string):
    spider_args["allow_query_string"] = allow_query_string
    spider = spider_cls(**spider_args)
    assert spider.allow_query_string is False
