import pytest

from crawler import Crawler
from crawler.constants import DEFAULT_BLACKLIST_EXTENSIONS

VALID_START_URL = 'http://example.com'


def test_crawler_init_defaults():
    """Test Crawler initializes with default values"""
    crawler = Crawler(start_url=VALID_START_URL)
    assert crawler.start_url == VALID_START_URL
    assert crawler.max_depth == 2
    assert crawler.allowed_domains is None
    assert crawler.blacklist_extensions == DEFAULT_BLACKLIST_EXTENSIONS
    assert crawler.concurrency == 10
    assert crawler.timeout == 10.0
    assert crawler.verify_ssl is True
    assert crawler.headers['User-Agent'].startswith('ASimplePythonCrawler')


def test_crawler_init_custom_args():
    """Test Crawler initialization with custom arguments"""
    domains = ['example.com', 'test.org']
    clean_blacklist = set(['.docx', 'pdf'])
    user_agent = 'TestAgent/1.0'

    crawler = Crawler(
        start_url=VALID_START_URL,
        max_depth=3,
        allowed_domains=domains,
        blacklist_extensions=clean_blacklist,
        concurrency=5,
        timeout=5.5,
        user_agent=user_agent,
        verify_ssl=False,
    )
    assert crawler.max_depth == 3
    assert crawler.allowed_domains == set(domains)
    assert crawler.blacklist_extensions == clean_blacklist
    assert crawler.concurrency == 5
    assert crawler.timeout == 5.5
    assert crawler.headers['User-Agent'] == user_agent
    assert crawler.verify_ssl is False


def test_crawler_init_empty_blacklist_arg():
    """Test that providing an empty list to blacklist overrides defaults"""
    crawler = Crawler(start_url=VALID_START_URL, blacklist_extensions=[])
    assert crawler.blacklist_extensions == set()


def test_crawler_init_none_blacklist_arg():
    """Test that providing None uses defaults (simulates --blacklist not used)"""
    crawler = Crawler(start_url=VALID_START_URL, blacklist_extensions=None)
    assert crawler.blacklist_extensions == DEFAULT_BLACKLIST_EXTENSIONS


def test_crawler_init_invalid_start_url():
    """Test Crawler raises ValueError for invalid start URL"""
    with pytest.raises(ValueError, match='Invalid start URL provided'):
        Crawler(start_url='invalid-url')


def test_crawler_init_negative_depth():
    """Test Crawler raises ValueError for negative max_depth"""
    with pytest.raises(ValueError, match='max_depth cannot be negative'):
        Crawler(start_url=VALID_START_URL, max_depth=-1)
