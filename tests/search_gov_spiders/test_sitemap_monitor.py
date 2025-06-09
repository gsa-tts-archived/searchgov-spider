import unittest
import tempfile
import shutil
import hashlib
import requests
from pathlib import Path
from unittest.mock import patch, MagicMock
from search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor import (
    SitemapMonitor,
    create_directory
)
import xml.etree.ElementTree as ET
import time


class MockCrawlSite:
    def __init__(self, starting_urls, sitemap_url=None, depth_limit=8, check_sitemap_hours=48, **kwargs):
        self.starting_urls = starting_urls
        self.sitemap_url = sitemap_url
        self.depth_limit = depth_limit
        self.check_sitemap_hours = check_sitemap_hours
        self.handle_javascript = kwargs.get('handle_javascript', False)
        self.allow_query_string = kwargs.get('allow_query_string', False)
        self.allowed_domains = kwargs.get('allowed_domains', [])
        self.deny_paths = kwargs.get('deny_paths', [])
        self.output_target = kwargs.get('output_target', None)


class BaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        p = patch(
            "search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.TARGET_DIR",
            Path(self.temp_dir)
        )
        p.start()
        self.addCleanup(p.stop Gentile)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)


class TestCreateDirectory(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.base_dir))

    def test_create_new(self):
        target = self.base_dir / "foo"
        create_directory(target)
        self.assertTrue(target.is_dir())

    def test_idempotent(self):
        target = self.base_dir / "bar"
        target.mkdir()
        create_directory(target)
        self.assertTrue(target.is_dir())


class TestSitemapMonitor(BaseTestCase):
    def make_records(self, depths):
        return [
            MockCrawlSite(starting_urls=f"http://example{i}.com",
                          sitemap_url="http://example.com/sitemap.xml",
                          depth_limit=d)
            for i, d in enumerate(depths)
        ]

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_filter_records(self, MockSitemapFinder):
        MockSitemapFinder.return_value.find.return_value = "sitemap.xml"
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        records = self.make_records([7, 8, 9])
        monitor = SitemapMonitor(records)
        monitor.setup()

        self.assertEqual(len(monitor.records), 2)
        self.assertEqual(
            [r.starting_urls for r in monitor.records],
            ["http://example1.com", "http://example2.com"]
        )

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_setup_sitemap_scenarios(self, MockSitemapFinder):
        finder = MockSitemapFinder.return_value
        finder.confirm_sitemap_url.side_effect = [True, False, False]
        finder.find.side_effect = ["http://found.com/sitemap.xml", None]

        records = [
            MockCrawlSite("http://valid.com", sitemap_url="http://valid.com/sitemap.xml"),
            MockCrawlSite("http://invalid.com", sitemap_url="http://invalid.com/sitemap.xml"),
            MockCrawlSite("http://none.com", sitemap_url=None),
        ]

        monitor = SitemapMonitor(records)
        monitor.setup()

        self.assertEqual(len(monitor.records), 2)
        self.assertEqual(monitor.records[0].sitemap_url, "http://valid.com/sitemap.xml")
        self.assertEqual(monitor.records[1].sitemap_url, "http://found.com/sitemap.xml")

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_load_stored_sitemaps_exists(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        url = "http://example.com/sitemap.xml"
        url_hash = hashlib.md5(url.encode()).hexdigest()
        file_path = Path(self.temp_dir) / f"{url_hash}.txt"
        with open(file_path, "w") as f:
            f.write("http://example.com/a\nhttp://example.com/b\n")

        records = [MockCrawlSite("http://example.com", sitemap_url=url)]
        monitor = SitemapMonitor(records)
        monitor.setup()

        self.assertIn(url, monitor.stored_sitemaps)
        self.assertSetEqual(monitor.stored_sitemaps[url], {"http://example.com/a", "http://example.com/b"})
        self.assertFalse(monitor.is_first_run[url])

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_load_stored_sitemaps_not_exists(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        url = "http://example.com/sitemap.xml"
        records = [MockCrawlSite("http://example.com", sitemap_url=url)]
        monitor = SitemapMonitor(records)
        monitor.setup()

        self.assertIn(url, monitor.stored_sitemaps)
        self.assertSetEqual(monitor.stored_sitemaps[url], set())
        self.assertTrue(monitor.is_first_run[url])

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_save_sitemap(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        monitor = SitemapMonitor([
            MockCrawlSite("http://example.com", sitemap_url="http://example.com/sitemap.xml")
        ])

        urls = {"http://example.com/a", "http://example.com/b"}
        monitor._save_sitemap("http://example.com/sitemap.xml", urls)

        h = hashlib.md5(b"http://example.com/sitemap.xml").hexdigest()
        path = Path(self.temp_dir) / f"{h}.txt"
        with open(path) as f:
            saved = {l.strip() for l in f}
        self.assertSetEqual(saved, urls)

    @patch("requests.Session")
    def test_fetch_sitemap_success(self, MockSession):
        xml = b"""<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                    <url><loc>http://ex.com/1</loc></url>
                    <url><loc>http://ex.com/2</loc></url>
                 </urlset>"""
        sess = MagicMock()
        resp = MagicMock(status_code=200, content=xml)
        sess.get.return_value = resp
        MockSession.return_value.__enter__.return_value = sess

        monitor = SitemapMonitor([])
        result = monitor._fetch_sitemap("http://ex.com/sitemap.xml")

        MockSession.assert_called_once()
        sess.headers.update.assert_called_once_with({"Cache-Control": "no-cache"})
        self.assertTrue(sess.cache_disabled)
        sess.get.assert_called_once_with("http://ex.com/sitemap.xml", timeout=30)
        self.assertSetEqual(result, {"http://ex.com/1", "http://ex.com/2"})

    @patch("requests.Session")
    def test_fetch_sitemap_nested(self, MockSession):
        sess = MockSession.return_value.__enter__.return_value
        sess.get.side_effect = [
            MagicMock(status_code=200, content=b"""<sitemapindex>
                <sitemap><loc>http://ex.com/sitemap1.xml</loc></sitemap>
            </sitemapindex>"""),
            MagicMock(status_code=200, content=b"""<urlset>
                <url><loc>http://ex.com/1</loc></url>
            </urlset>""")
        ]

        monitor = SitemapMonitor([])
        result = monitor._fetch_sitemap("http://ex.com/sitemap.xml")

        self.assertSetEqual(result, {"http://ex.com/1"})

    @patch("requests.Session")
    def test_fetch_sitemap_max_depth(self, MockSession):
        sess = MockSession.return_value.__enter__.return_value
        xml = b"""<sitemapindex><sitemap><loc>http://ex.com/next.xml</loc></sitemap></sitemapindex>"""
        sess.get.return_value = MagicMock(status_code=200, content=xml)

        monitor = SitemapMonitor([])
        result = monitor._fetch_sitemap("http://ex.com/sitemap.xml", depth=11, max_depth=10)

        self.assertSetEqual(result, set())

    @patch("requests.Session")
    def test_fetch_sitemap_non_sitemap_url(self, MockSession):
        sess = MockSession.return_value.__enter__.return_value
        xml = b"""<sitemapindex><sitemap><loc>http://ex.com/page.html</loc></sitemap></sitemapindex>"""
        sess.get.return_value = MagicMock(status_code=200, content=xml)

        monitor = SitemapMonitor([])
        result = monitor._fetch_sitemap("http://ex.com/sitemap.xml")

        self.assertSetEqual(result, set())

    @patch("requests.Session")
    def test_fetch_sitemap_unrecognized_tag(self, MockSession):
        sess = MockSession.return_value.__enter__.return_value
        xml = b"""<unknown></unknown>"""
        sess.get.return_value = MagicMock(status_code=200, content=xml)

        monitor = SitemapMonitor([])
        result = monitor._fetch_sitemap("http://ex.com/sitemap.xml")

        self.assertSetEqual(result, set())

    @patch("requests.Session")
    def test_fetch_sitemap_error(self, MockSession):
        sess = MockSession.return_value
        sess.get.side_effect = requests.exceptions.RequestException
        monitor = SitemapMonitor([])
        self.assertSetEqual(
            monitor._fetch_sitemap("http://fake"),
            set(),
            "Should return empty set on request errors"
        )

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_check_for_changes_true_first_run(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        monitor = SitemapMonitor([
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml")
        ])
        monitor.is_first_run["http://ex.com/sitemap.xml"] = True

        with patch.object(monitor, "_fetch_sitemap", return_value={"u1", "u2"}):
            new_urls, total = monitor._check_for_changes("http://ex.com/sitemap.xml")

        self.assertSetEqual(new_urls, set())
        self.assertEqual(total, 2)
        self.assertFalse(monitor.is_first_run["http://ex.com/sitemap.xml"])
        self.assertSetEqual(monitor.stored_sitemaps["http://ex.com/sitemap.xml"], {"u1", "u2"})

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_check_for_changes_no_new(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        monitor = SitemapMonitor([
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml")
        ])
        key = "http://ex.com/sitemap.xml"
        monitor.stored_sitemaps[key] = {"u1"}
        monitor.is_first_run[key] = False

        with patch.object(monitor, "_fetch_sitemap", return_value={"u1"}):
            new_urls, total = monitor._check_for_changes(key)

        self.assertSetEqual(new_urls, set())
        self.assertEqual(total, 1)

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_check_for_changes_with_new(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        monitor = SitemapMonitor([
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml")
        ])
        key = "http://ex.com/sitemap.xml"
        monitor.stored_sitemaps[key] = {"u1"}
        monitor.is_first_run[key] = False

        with patch.object(monitor, "_fetch_sitemap", return_value={"u1", "u2"}):
            new_urls, total = monitor._check_for_changes(key)

        self.assertSetEqual(new_urls, {"u2"})
        self.assertEqual(total, 2)

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_check_for_changes_fetch_error(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        monitor = SitemapMonitor([
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml")
        ])
        key = "http://ex.com/sitemap.xml"
        monitor.is_first_run[key] = False

        with patch.object(monitor, "_fetch_sitemap", side_effect=Exception("Fetch error")):
            new_urls, total = monitor._check_for_changes(key)

        self.assertSetEqual(new_urls, set())
        self.assertEqual(total, 0)

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    def test_get_check_interval(self, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True

        rec = MockCrawlSite(
            "http://ex.com",
            sitemap_url="http://ex.com/sitemap.xml",
            check_sitemap_hours=12
        )
        monitor = SitemapMonitor([rec])
        self.assertEqual(
            monitor._get_check_interval(rec.sitemap_url),
            12
        )

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    @patch("time.time")
    @patch("time.sleep")
    @patch("multiprocessing.Process")
    def test_run_initial_setup_and_queue(self, MockProcess, mock_sleep, mock_time, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        mock_time.side_effect = [0, 10, 20]
        mock_sleep.return_value = None

        records = [
            MockCrawlSite("http://ex1.com", sitemap_url="http://ex1.com/sitemap.xml", check_sitemap_hours=1),
            MockCrawlSite("http://ex2.com", sitemap_url="http://ex2.com/sitemap.xml", check_sitemap_hours=2),
        ]
        monitor = SitemapMonitor(records)
        monitor.setup()

        self.assertEqual(len(monitor.next_check_times), 2)
        self.assertEqual(monitor.next_check_times["http://ex1.com/sitemap.xml"], 0)
        self.assertEqual(monitor.next_check_times["http://ex2.com/sitemap.xml"], 0)

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    @patch("time.time")
    @patch("time.sleep")
    @patch("multiprocessing.Process")
    def test_run_with_new_urls(self, MockProcess, mock_sleep, mock_time, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        mock_time.side_effect = [0, 0, 3600]
        mock_sleep.return_value = None
        process_instance = MockProcess.return_value

        records = [
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml", check_sitemap_hours=1)
        ]
        monitor = SitemapMonitor(records)
        monitor.setup()

        with patch.object(monitor, "_check_for_changes", return_value=({"http://ex.com/new"}, 1)):
            # Simulate one iteration
            check_queue = [(0, "http://ex.com/sitemap.xml")]
            monitor.next_check_times["http://ex.com/sitemap.xml"] = 0
            monitor.records_map = {record.sitemap_url: record for record in monitor.records}
            with patch("heapq.heappop", return_value=check_queue.pop(0)), \
                 patch("heapq.heappush") as mock_heappush:
                monitor.run()

        MockProcess.assert_called_once()
        process_instance.start.assert_called_once()
        process_instance.join.assert_called_once()
        mock_heappush.assert_called_once()

    @patch("search_gov_crawler.search_gov_spiders.sitemaps.sitemap_monitor.SitemapFinder")
    @patch("time.time")
    @patch("time.sleep")
    @patch("multiprocessing.Process")
    def test_run_no_new_urls(self, MockProcess, mock_sleep, mock_time, MockSitemapFinder):
        MockSitemapFinder.return_value.confirm_sitemap_url.return_value = True
        mock_time.side_effect = [0, 0, 3600]
        mock_sleep.return_value = None

        records = [
            MockCrawlSite("http://ex.com", sitemap_url="http://ex.com/sitemap.xml", check_sitemap_hours=1)
        ]
        monitor = SitemapMonitor(records)
        monitor.setup()

        with patch.object(monitor, "_check_for_changes", return_value=(set(), 1)):
            check_queue = [(0, "http://ex.com/sitemap.xml")]
            monitor.next_check_times["http://ex.com/sitemap.xml"] = 0
            monitor.records_map = {record.sitemap_url: record for record in monitor.records}
            with patch("heapq.heappop", return_value=check_queue.pop(0)), \
                 patch("heapq.heappush") as mock_heappush:
                monitor.run()

        MockProcess.assert_not_called()
        mock_heappush.assert_called_once()


if __name__ == "__main__":
    unittest.main()