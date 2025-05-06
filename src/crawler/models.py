import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class CrawlResult(BaseModel):
    """Information gathered for a single crawled URL"""

    content_size: Optional[int] = None
    depth: int
    error: Optional[str] = None
    status_code: Optional[int] = None
    timestamp: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
    title: Optional[str] = None
    url: str


class CrawlStats(BaseModel):
    """Overall statistics for a single crawl"""

    domain_counts: Dict[str, int] = {}
    duration_seconds: Optional[float] = None
    end_time: Optional[datetime.datetime] = None
    start_time: Optional[datetime.datetime] = None
    status_code_counts: Dict[int, int] = {}
    total_errors_processing: int = 0  # internal processing errors
    total_errors_request: int = 0  # network request errors
    total_urls_processed: int = 0


class CrawlReport(BaseModel):
    """The final report containing results and statistics"""

    allowed_domains: Optional[List[str]] = None
    blacklist_extensions: Optional[List[str]] = None
    max_depth: int
    results: List[CrawlResult]
    start_url: str
    stats: CrawlStats
