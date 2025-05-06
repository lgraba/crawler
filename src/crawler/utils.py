import os
from typing import Optional, Set
from urllib.parse import urljoin, urlparse


def normalize_url(base_url: str, link: str) -> Optional[str]:
    """Convert a potentially relative link to an absolute URL"""
    try:
        absolute_url = urljoin(base_url, link.strip())
        parsed = urlparse(absolute_url)

        if not parsed.scheme or not parsed.netloc:
            return None
        clean_url = parsed._replace(fragment='').geturl()
        return clean_url
    except ValueError:
        return None


def get_domain(url: str) -> Optional[str]:
    """Extract the netloc (domain) from a URL"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except ValueError:
        return None


def get_extension(url: str) -> Optional[str]:
    """Extract the file extension from the URL path"""
    try:
        parsed = urlparse(url)
        path = parsed.path
        if path:
            _, ext = os.path.splitext(path)
            return ext.lower() if ext else None
        return None
    except ValueError:
        return None


def is_valid_url(
    url: str, allowed_domains: Optional[Set[str]] = None, blacklist_extensions: Optional[Set[str]] = None
) -> bool:
    """Check if a URL is valid based on scheme, domain, and extension"""
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False

        if allowed_domains:
            domain = parsed.netloc

            if not domain or domain not in allowed_domains:
                return False

        if blacklist_extensions:
            ext = get_extension(url)

            if ext and ext in blacklist_extensions:
                return False

        return True
    except ValueError:
        return False
