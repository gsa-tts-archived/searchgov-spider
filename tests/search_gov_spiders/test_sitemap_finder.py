import pytest
import requests # Import requests to mock exceptions like requests.exceptions.Timeout

# Import the class to be tested (assuming the script is saved as sitemap_finder.py)
# If your tests are in a 'tests' directory, you might need to adjust the import path
# depending on your project structure (e.g., 'from ..src.sitemap_finder import SitemapFinder'
# or ensure your project root is in PYTHONPATH)
from search_gov_crawler.search_gov_spiders.sitemaps.sitemap_finder import SitemapFinder

# --- Constants for Testing ---
TEST_BASE_URL_NO_SLASH = "example.com"
TEST_BASE_URL_WITH_SLASH = "https://example.com/"
TEST_BASE_URL_HTTP = "http://example.com/"


# --- Pytest Fixture for SitemapFinder Instance ---

@pytest.fixture
def finder():
    """Provides a SitemapFinder instance for tests."""
    return SitemapFinder()

# --- Test Helper Methods ---

def test_join_base_relative(finder):
    """Test joining a relative path."""
    assert finder._join_base(TEST_BASE_URL_WITH_SLASH, "relative/path.xml") == "https://example.com/relative/path.xml"

def test_join_base_absolute(finder):
    """Test joining an absolute path (should return it unchanged)."""
    assert finder._join_base(TEST_BASE_URL_WITH_SLASH, "https://othersite.com/sitemap.xml") == "https://othersite.com/sitemap.xml"
    assert finder._join_base(TEST_BASE_URL_WITH_SLASH, "http://othersite.com/sitemap.xml") == "http://othersite.com/sitemap.xml"

def test_find_base_url_normalization(finder, mocker):
    """Test that the find method normalizes the base URL correctly."""
    mock_head = mocker.patch('sitemap_finder.requests.head')
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/xml"}
    mock_head.return_value = mock_response

    # Test without scheme and without slash
    finder.find(TEST_BASE_URL_NO_SLASH)
    mock_head.assert_called_with(
        "https://example.com/sitemap.xml", # Note: normalized URL
        timeout=finder.timeout_seconds,
        headers=finder.headers,
        allow_redirects=True
    )

    # Reset mock and test with http scheme and trailing slash
    mock_head.reset_mock()
    finder.find(TEST_BASE_URL_HTTP)
    mock_head.assert_called_with(
        "http://example.com/sitemap.xml", # Note: normalized URL
        timeout=finder.timeout_seconds,
        headers=finder.headers,
        allow_redirects=True
    )


# --- Test Finding Methods ---

def test_check_common_locations_found(finder, mocker):
    """Test finding a sitemap in a common location."""
    mock_head = mocker.patch('sitemap_finder.requests.head')

    mock_response_200 = mocker.MagicMock()
    mock_response_200.status_code = 200
    # The 'or True' in the original code means content-type doesn't strictly matter
    mock_response_200.headers = {"Content-Type": "text/html"}

    # Simulate finding the sitemap at the second common location
    mock_head.side_effect = [
        requests.exceptions.Timeout("Timeout for first"), # Simulate error on first
        mock_response_200, # Simulate success on second
        # No need for more mocks as it should return after success
    ]

    expected_url = f"{TEST_BASE_URL_WITH_SLASH}{finder.common_sitemap_names[1]}"
    result = finder._check_common_locations(TEST_BASE_URL_WITH_SLASH)

    assert result == expected_url
    # Check that HEAD was called for the first two common locations
    assert mock_head.call_count == 2
    mock_head.assert_has_calls([
        mocker.call(f"{TEST_BASE_URL_WITH_SLASH}{finder.common_sitemap_names[0]}", timeout=finder.timeout_seconds, headers=finder.headers, allow_redirects=True),
        mocker.call(expected_url, timeout=finder.timeout_seconds, headers=finder.headers, allow_redirects=True),
    ])

def test_check_common_locations_not_found(finder, mocker):
    """Test when no common sitemap locations are found."""
    mock_head = mocker.patch('sitemap_finder.requests.head')
    mock_response_404 = mocker.MagicMock()
    mock_response_404.status_code = 404
    mock_head.side_effect = [mock_response_404] * len(finder.common_sitemap_names)

    result = finder._check_common_locations(TEST_BASE_URL_WITH_SLASH)
    assert result is None
    assert mock_head.call_count == len(finder.common_sitemap_names)

def test_check_robots_txt_found(finder, mocker):
    """Test finding a sitemap URL in robots.txt."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    robots_content = """
    User-agent: *
    Allow: /
    Sitemap: https://example.com/main_sitemap.xml
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = robots_content
    mock_get.return_value = mock_response

    result = finder._check_robots_txt(TEST_BASE_URL_WITH_SLASH)
    assert result == "https://example.com/main_sitemap.xml"
    mock_get.assert_called_once_with(
        f"{TEST_BASE_URL_WITH_SLASH}robots.txt",
        timeout=finder.timeout_seconds,
        headers=finder.headers
    )

def test_check_robots_txt_found_case_insensitive(finder, mocker):
    """Test finding a sitemap URL in robots.txt with different casing."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    robots_content = "User-agent: *\nsitemap: http://example.com/another_sitemap.xml"
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = robots_content
    mock_get.return_value = mock_response

    result = finder._check_robots_txt(TEST_BASE_URL_WITH_SLASH)
    assert result == "http://example.com/another_sitemap.xml"


def test_check_robots_txt_not_found(finder, mocker):
    """Test when robots.txt exists but doesn't contain a Sitemap directive."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    robots_content = "User-agent: *\nAllow: /"
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = robots_content
    mock_get.return_value = mock_response

    result = finder._check_robots_txt(TEST_BASE_URL_WITH_SLASH)
    assert result is None

def test_check_robots_txt_fetch_error(finder, mocker):
    """Test when fetching robots.txt results in an error."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_get.side_effect = requests.exceptions.ConnectionError("Failed to connect")

    result = finder._check_robots_txt(TEST_BASE_URL_WITH_SLASH)
    assert result is None

def test_check_robots_txt_fetch_404(finder, mocker):
    """Test when robots.txt returns a 404 status."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_response = mocker.MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response

    result = finder._check_robots_txt(TEST_BASE_URL_WITH_SLASH)
    assert result is None

def test_check_html_source_link_tag(finder, mocker):
    """Test finding sitemap via <link rel='sitemap'> tag."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    html_content = """
    <html><head>
    <link rel="sitemap" type="application/xml" href="/sitemap_from_link.xml" />
    </head><body></body></html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_get.return_value = mock_response

    result = finder._check_html_source(TEST_BASE_URL_WITH_SLASH)
    assert result == "https://example.com/sitemap_from_link.xml"
    mock_get.assert_called_once_with(
        TEST_BASE_URL_WITH_SLASH,
        timeout=finder.timeout_seconds,
        headers=finder.headers
    )

def test_check_html_source_alternate_link_tag(finder, mocker):
    """Test finding sitemap via <link rel='alternate' type='application/xml'> tag."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    html_content = """
    <html><head>
    <link rel="alternate" type="application/xml" title="Sitemap" href="https://example.com/sitemap_alternate.xml" />
    </head><body></body></html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_get.return_value = mock_response

    result = finder._check_html_source(TEST_BASE_URL_WITH_SLASH)
    assert result == "https://example.com/sitemap_alternate.xml"

def test_check_html_source_href_xml(finder, mocker):
    """Test finding sitemap via href containing 'sitemap' and '.xml'."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    html_content = """
    <html><body>
    <a href="/path/my-sitemap-file.xml">Check Sitemap</a>
    </body></html>
    """
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_get.return_value = mock_response

    result = finder._check_html_source(TEST_BASE_URL_WITH_SLASH)
    assert result == "https://example.com/path/my-sitemap-file.xml"

def test_check_html_source_not_found(finder, mocker):
    """Test when HTML doesn't contain any sitemap references."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    html_content = "<html><body><h1>Hello</h1></body></html>"
    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.text = html_content
    mock_get.return_value = mock_response

    result = finder._check_html_source(TEST_BASE_URL_WITH_SLASH)
    assert result is None

def test_check_html_source_fetch_error(finder, mocker):
    """Test error fetching HTML source."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")
    result = finder._check_html_source(TEST_BASE_URL_WITH_SLASH)
    assert result is None

def test_check_xml_files_in_root_found(finder, mocker):
    """Test finding sitemap via XML file link in root directory listing."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_head = mocker.patch('sitemap_finder.requests.head')
    html_content = """
    <html><body>Directory Listing:
    <a href="image.jpg">Image</a>
    <a href="root_sitemap.xml">Root Sitemap XML</a>
    <a href="another.xml">Another XML</a>
    </body></html>
    """
    # Mock GET for the directory listing
    mock_get_response = mocker.MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.text = html_content
    mock_get.return_value = mock_get_response

    # Mock HEAD for verifying the found XML file
    mock_head_response = mocker.MagicMock()
    mock_head_response.status_code = 200
    mock_head.return_value = mock_head_response

    result = finder._check_xml_files_in_root(TEST_BASE_URL_WITH_SLASH)
    expected_url = f"{TEST_BASE_URL_WITH_SLASH}root_sitemap.xml"

    assert result == expected_url
    mock_get.assert_called_once_with(
         TEST_BASE_URL_WITH_SLASH,
         timeout=finder.timeout_seconds,
         headers=finder.headers
    )
    # Ensure HEAD was called to verify the *correct* sitemap URL
    mock_head.assert_called_once_with(
        expected_url,
        timeout=finder.timeout_seconds,
        headers=finder.headers
    )

def test_check_xml_files_in_root_found_but_head_fails(finder, mocker):
    """Test finding XML in root, but verification via HEAD fails."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_head = mocker.patch('sitemap_finder.requests.head')
    html_content = '<a href="sitemap_exists_but_404.xml">Sitemap</a>'
    # Mock GET
    mock_get_response = mocker.MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.text = html_content
    mock_get.return_value = mock_get_response

    # Mock HEAD to return 404
    mock_head_response = mocker.MagicMock()
    mock_head_response.status_code = 404
    mock_head.return_value = mock_head_response

    result = finder._check_xml_files_in_root(TEST_BASE_URL_WITH_SLASH)
    assert result is None
    mock_head.assert_called_once() # Ensure HEAD was attempted

def test_check_xml_files_in_root_no_sitemap_xml(finder, mocker):
    """Test root listing exists but no XML file contains 'sitemap'."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_head = mocker.patch('sitemap_finder.requests.head')
    html_content = '<a href="data.xml">Data</a> <a href="config.xml">Config</a>'
    mock_get_response = mocker.MagicMock()
    mock_get_response.status_code = 200
    mock_get_response.text = html_content
    mock_get.return_value = mock_get_response

    result = finder._check_xml_files_in_root(TEST_BASE_URL_WITH_SLASH)
    assert result is None
    mock_head.assert_not_called() # HEAD shouldn't be called

def test_check_xml_files_in_root_get_fails(finder, mocker):
    """Test root listing check when GET fails."""
    mock_get = mocker.patch('sitemap_finder.requests.get')
    mock_get.side_effect = requests.exceptions.RequestException("Error")
    result = finder._check_xml_files_in_root(TEST_BASE_URL_WITH_SLASH)
    assert result is None

# --- Test Main `find` Method Orchestration ---

def test_find_prioritization_common_first(finder, mocker):
    """Test find() returns URL from common locations first."""
    common_url = "https://example.com/sitemap.xml"
    robots_url = "https://example.com/robots_sitemap.xml"

    # Mock the internal check methods
    mock_common = mocker.patch.object(finder, '_check_common_locations', return_value=common_url)
    mock_robots = mocker.patch.object(finder, '_check_robots_txt', return_value=robots_url)
    mock_html = mocker.patch.object(finder, '_check_html_source', return_value=None)
    mock_xml = mocker.patch.object(finder, '_check_xml_files_in_root', return_value=None)

    result = finder.find(TEST_BASE_URL_NO_SLASH)

    assert result == common_url
    mock_common.assert_called_once()
    mock_robots.assert_not_called()
    mock_html.assert_not_called()
    mock_xml.assert_not_called()

def test_find_prioritization_robots_second(finder, mocker):
    """Test find() returns URL from robots.txt if common fails."""
    robots_url = "https://example.com/robots_sitemap.xml"
    html_url = "https://example.com/html_sitemap.xml"

    mock_common = mocker.patch.object(finder, '_check_common_locations', return_value=None)
    mock_robots = mocker.patch.object(finder, '_check_robots_txt', return_value=robots_url)
    mock_html = mocker.patch.object(finder, '_check_html_source', return_value=html_url)
    mock_xml = mocker.patch.object(finder, '_check_xml_files_in_root', return_value=None)

    result = finder.find(TEST_BASE_URL_WITH_SLASH)

    assert result == robots_url
    mock_common.assert_called_once()
    mock_robots.assert_called_once()
    mock_html.assert_not_called()
    mock_xml.assert_not_called()

def test_find_prioritization_html_third(finder, mocker):
    """Test find() returns URL from HTML if common and robots fail."""
    html_url = "https://example.com/html_sitemap.xml"
    xml_url = "https://example.com/xml_sitemap.xml"

    mock_common = mocker.patch.object(finder, '_check_common_locations', return_value=None)
    mock_robots = mocker.patch.object(finder, '_check_robots_txt', return_value=None)
    mock_html = mocker.patch.object(finder, '_check_html_source', return_value=html_url)
    mock_xml = mocker.patch.object(finder, '_check_xml_files_in_root', return_value=xml_url)

    result = finder.find(TEST_BASE_URL_WITH_SLASH)

    assert result == html_url
    mock_common.assert_called_once()
    mock_robots.assert_called_once()
    mock_html.assert_called_once()
    mock_xml.assert_not_called()

def test_find_prioritization_xml_last(finder, mocker):
    """Test find() returns URL from root XML check if others fail."""
    xml_url = "https://example.com/xml_sitemap.xml"

    mock_common = mocker.patch.object(finder, '_check_common_locations', return_value=None)
    mock_robots = mocker.patch.object(finder, '_check_robots_txt', return_value=None)
    mock_html = mocker.patch.object(finder, '_check_html_source', return_value=None)
    mock_xml = mocker.patch.object(finder, '_check_xml_files_in_root', return_value=xml_url)

    result = finder.find(TEST_BASE_URL_WITH_SLASH)

    assert result == xml_url
    mock_common.assert_called_once()
    mock_robots.assert_called_once()
    mock_html.assert_called_once()
    mock_xml.assert_called_once()

def test_find_not_found_any_method(finder, mocker):
    """Test find() returns None when no method finds a sitemap."""
    mock_common = mocker.patch.object(finder, '_check_common_locations', return_value=None)
    mock_robots = mocker.patch.object(finder, '_check_robots_txt', return_value=None)
    mock_html = mocker.patch.object(finder, '_check_html_source', return_value=None)
    mock_xml = mocker.patch.object(finder, '_check_xml_files_in_root', return_value=None)

    result = finder.find(TEST_BASE_URL_WITH_SLASH)

    assert result is None
    mock_common.assert_called_once()
    mock_robots.assert_called_once()
    mock_html.assert_called_once()
    mock_xml.assert_called_once()
