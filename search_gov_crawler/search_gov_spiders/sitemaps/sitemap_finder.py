import re
import requests
from typing import Optional
from urllib.parse import urljoin

class SitemapFinder:
    def __init__(self):

        self.common_sitemap_names = [
            "sitemap.xml",
            "wp-sitemap.xml",
            "page-sitemap.xml",
            "tag-sitemap.xml",
            "category-sitemap.xml",
            "sitemap1.xml",
            "post-sitemap.xml"
            "sitemap_index.xml",
            "sitemap-index.xml",
            "sitemapindex.xml"
        ]

        self.timeout_seconds = 5
        
        # User agent to avoid blocking
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
    
    def _join_base(self, base_url: str, sitemap_path: str):
        if not sitemap_path.startswith(("http://", "https://")):
            return urljoin(base_url, sitemap_path)
        return sitemap_path
        
    def find(self, base_url) -> Optional[str]:
        """
        Find sitemap URL using multiple methods.
        Returns the first successful sitemap URL or None if not found.
        """
        base_url = base_url if base_url.endswith("/") else f"{base_url}/"
        if not base_url.startswith(("http://", "https://")):
            base_url = f"https://{base_url}"

        # Method 1: Try common sitemap locations
        sitemap_url = self._check_common_locations(base_url)
        if sitemap_url:
            return sitemap_url
            
        # Method 2: Check robots.txt
        sitemap_url = self._check_robots_txt(base_url)
        if sitemap_url:
            return sitemap_url
            
        # Method 3: Check HTML source
        sitemap_url = self._check_html_source(base_url)
        if sitemap_url:
            return sitemap_url
            
        # Method 4: Check XML sitemaps in root directory
        sitemap_url = self._check_xml_files_in_root(base_url)
        if sitemap_url:
            return sitemap_url
            
        return None
    
    def _check_common_locations(self, base_url: str) -> Optional[str]:
        """Try common sitemap locations using HEAD requests."""
        print("Checking common sitemap locations...")
        
        for name in self.common_sitemap_names:
            potential_url = urljoin(base_url, name)
            try:
                response = requests.head(potential_url, timeout=self.timeout_seconds, headers=self.headers, allow_redirects=True)
                if response.status_code == 200:
                    content_type = response.headers.get("Content-Type", "")
                    # Even if the content type doesn't specify XML, if the status is 200 and it's a sitemap filename, assume it's valid
                    if "xml" in content_type or True:
                        print(f"Found sitemap at common location: {potential_url}")
                        return potential_url
            except Exception as e:
                pass
                
        return None
    
    def _check_robots_txt(self, base_url: str) -> Optional[str]:
        """Check robots.txt for Sitemap directive."""
        print("Checking robots.txt for sitemap...")
        
        try:
            robots_url = urljoin(base_url, "robots.txt")
            response = requests.get(robots_url, timeout=self.timeout_seconds, headers=self.headers)
            
            if response.status_code == 200:
                content = response.text
                # Look for Sitemap: directive
                sitemap_matches = re.findall(r"(?i)Sitemap:\s*(https?://\S+)", content)
                if sitemap_matches:
                    sitemap_url = sitemap_matches[0].strip()
                    print(f"Found sitemap in robots.txt: {sitemap_url}")
                    return sitemap_url
        except Exception as e:
            print(f"Error checking robots.txt: {e}")
                
        return None
    
    def _check_html_source(self, base_url: str) -> Optional[str]:
        """Check HTML source for sitemap references."""
        print("Checking HTML source for sitemap references...")
        
        try:
            response = requests.get(base_url, timeout=self.timeout_seconds, headers=self.headers)
            if response.status_code == 200:
                html_content = response.text
                
                # Look for sitemap in link tags
                link_pattern = r"<link[^>]*rel=[\"'](?:sitemap|alternate)[\"'][^>]*href=[\"']([^\"']+)[\"']"
                matches = re.findall(link_pattern, html_content, re.IGNORECASE)
                if matches:
                    sitemap_url = matches[0]
                    sitemap_url = self._join_base(base_url, sitemap_url)
                    print(f"Found sitemap in HTML link tag: {sitemap_url}")
                    return sitemap_url
                
                # Look for any .xml files that might be sitemaps
                xml_pattern = r"href=[\"']([^\"']*sitemap[^\"']*\.xml)[\"']"
                matches = re.findall(xml_pattern, html_content, re.IGNORECASE)
                if matches:
                    sitemap_path = matches[0]
                    sitemap_url = self._join_base(base_url, sitemap_path)
                    print(f"Found sitemap reference in HTML: {sitemap_url}")
                    return sitemap_url
                
        except Exception as e:
            print(f"Error checking HTML source: {e}")
            
        return None

    def _check_xml_files_in_root(self, base_url: str) -> Optional[str]:
        """
        Last resort: Sometimes web servers allow directory listing.
        Check if we can find XML files that might be sitemaps.
        """
        print("Checking for XML files in root directory...")
        
        try:
            response = requests.get(base_url, timeout=self.timeout_seconds, headers=self.headers)
            if response.status_code == 200:
                html_content = response.text
                
                # Look for XML files that might be sitemaps
                xml_pattern = r"href=[\"']([^\"']+\.xml)[\"']"
                matches = re.findall(xml_pattern, html_content, re.IGNORECASE)
                
                for match in matches:
                    if "sitemap" in match.lower():
                        sitemap_url = urljoin(base_url, match)
                        # Verify it exists with a HEAD request
                        head_response = requests.head(sitemap_url, timeout=self.timeout_seconds, headers=self.headers)
                        if head_response.status_code == 200:
                            print(f"Found potential sitemap XML in directory: {sitemap_url}")
                            return sitemap_url
                    
        except Exception as e:
            pass
            
        return None
