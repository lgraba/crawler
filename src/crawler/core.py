import asyncio
import datetime
import logging
import time
from typing import List, Optional, Set

import httpx
from bs4 import BeautifulSoup

from .constants import DEFAULT_BLACKLIST_EXTENSIONS, DEFAULT_HEADERS
from .models import CrawlReport, CrawlResult, CrawlStats
from .utils import get_domain, is_valid_url, normalize_url

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(
        self,
        start_url: str,
        max_depth: int = 2,
        allowed_domains: Optional[List[str]] = None,
        blacklist_extensions: Optional[List[str]] = None,
        concurrency: int = 10,
        timeout: float = 10.0,
        user_agent: Optional[str] = None,
        verify_ssl: bool = True,
    ):
        _start_url_normalized = normalize_url(start_url, start_url)
        if not _start_url_normalized:
            raise ValueError(f'Invalid start URL provided: {start_url}')
        self.start_url = _start_url_normalized

        if max_depth < 0:
            raise ValueError('max_depth cannot be negative')
        self.max_depth = max_depth

        self.allowed_domains: Optional[Set[str]] = set(allowed_domains) if allowed_domains else None

        if blacklist_extensions is not None:
            self.blacklist_extensions = set(blacklist_extensions)
            logger.info(f'Using provided blacklist extensions: {self.blacklist_extensions}')
        else:
            self.blacklist_extensions = DEFAULT_BLACKLIST_EXTENSIONS.copy()
            logger.info(f'Using default blacklist extensions (count: {len(self.blacklist_extensions)})')

        self.concurrency = max(1, concurrency)
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.headers = DEFAULT_HEADERS.copy()
        if user_agent:
            self.headers['User-Agent'] = user_agent

        self._queue: asyncio.Queue = asyncio.Queue()
        self._visited_urls: Set[str] = set()
        self._results: List[CrawlResult] = []
        self._stats = CrawlStats()
        self._active_tasks: Set[asyncio.Task] = set()

        # Semaphore to limit concurrent requests
        self._semaphore = asyncio.Semaphore(self.concurrency)

        logger.info('Crawler initialized:')
        logger.info(f'  Start URL: {self.start_url}')
        logger.info(f'  Max Depth: {self.max_depth}')
        logger.info(f'  Allowed Domains: {self.allowed_domains or "Any"}')
        logger.info(f'  Blacklisted Extensions Count: {len(self.blacklist_extensions)}')
        logger.info(f'  Concurrency: {self.concurrency}, Timeout: {self.timeout}s, Verify SSL: {self.verify_ssl}')

    async def _worker(self, worker_id: int, client: httpx.AsyncClient):
        """Worker task to process URLs from the queue"""

        logger.debug(f'Worker {worker_id} starting.')
        while True:
            try:
                # wait for an item from the queue
                current_url, current_depth = await self._queue.get()
                logger.debug(f'Worker {worker_id} got URL: {current_url} (depth {current_depth})')

                # double-check if visited (might have been visited by another worker between adding to queue and processing)
                if current_url in self._visited_urls:
                    self._queue.task_done()
                    continue

                # add to visited before processing to prevent re-queueing
                self._visited_urls.add(current_url)

                # acquire semaphore before making request
                async with self._semaphore:
                    await self._process_url(client, current_url, current_depth)

                self._queue.task_done()

            except asyncio.CancelledError:
                logger.debug(f'Worker {worker_id} was cancelled.')
                break
            except Exception as e:
                logger.error(f'Critical error in worker {worker_id} loop: {e}', exc_info=True)
                self._stats.total_errors_processing += 1

                try:
                    self._queue.task_done()
                except ValueError:
                    pass

        logger.debug(f'Worker {worker_id} finished.')

    async def _process_url(self, client: httpx.AsyncClient, url: str, depth: int):
        """Fetch, parse, and process a single URL."""

        self._stats.total_urls_processed += 1
        domain = get_domain(url)
        if domain:
            self._stats.domain_counts[domain] = self._stats.domain_counts.get(domain, 0) + 1

        result = CrawlResult(url=url, depth=depth)

        try:
            logger.info(f'Fetching: {url} (Depth: {depth})')
            response = await client.get(url, follow_redirects=True)

            result.status_code = response.status_code
            result.content_size = len(response.content)
            self._stats.status_code_counts[response.status_code] = (
                self._stats.status_code_counts.get(response.status_code, 0) + 1
            )

            response.raise_for_status()

            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                title_tag = soup.find('title')
                if title_tag and title_tag.string:
                    result.title = title_tag.string.strip()

                if depth < self.max_depth:
                    links = soup.find_all('a', href=True)
                    for link_tag in links:
                        href = link_tag['href']
                        normalized_url = normalize_url(url, href)

                        if normalized_url and normalized_url not in self._visited_urls:
                            if is_valid_url(normalized_url, self.allowed_domains, self.blacklist_extensions):
                                # check visited again right before putting (minimal race condition window)
                                if normalized_url not in self._visited_urls:
                                    logger.debug(f'Queueing Link: {normalized_url} (Depth: {depth + 1})')
                                    await self._queue.put((normalized_url, depth + 1))
                            else:
                                logger.debug(f'Filtered Link: {normalized_url}')
            else:
                logger.debug(f'Non-HTML content skipped for link extraction: {url} ({content_type})')

        except httpx.HTTPStatusError as e:
            logger.warning(f'HTTP error fetching {url}: Status {e.response.status_code}')
            result.error = f'HTTP Status {e.response.status_code}'
        except httpx.RequestError as e:
            logger.error(f'Request error fetching {url}: {type(e).__name__}')
            result.error = f'Request Error: {type(e).__name__}'
            self._stats.total_errors_request += 1
        except Exception as e:
            logger.error(f'Processing error for {url}: {e}', exc_info=True)
            result.error = f'Processing Error: {type(e).__name__}'
            self._stats.total_errors_processing += 1
        finally:
            result.timestamp = datetime.datetime.now(datetime.timezone.utc)
            self._results.append(result)

    async def crawl(self) -> CrawlReport:
        """Starts the crawling process and returns the report."""

        if not is_valid_url(self.start_url, self.allowed_domains, self.blacklist_extensions):
            logger.error(f'Start URL {self.start_url} is invalid or does not match crawl criteria.')

            return CrawlReport(
                start_url=self.start_url,
                max_depth=self.max_depth,
                allowed_domains=list(self.allowed_domains) if self.allowed_domains else None,
                blacklist_extensions=list(self.blacklist_extensions),
                results=[],
                stats=self._stats,
            )

        self._stats.start_time = datetime.datetime.now(datetime.timezone.utc)
        start_perf = time.perf_counter()

        await self._queue.put((self.start_url, 0))

        # single shared httpx client session for all workers
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=self.timeout,
            verify=self.verify_ssl,
            follow_redirects=True,
            limits=httpx.Limits(max_connections=self.concurrency, max_keepalive_connections=self.concurrency),
        ) as client:
            worker_tasks = []

            for i in range(self.concurrency):
                task = asyncio.create_task(self._worker(i, client), name=f'worker-{i}')
                worker_tasks.append(task)

            await self._queue.join()
            logger.info('All items processed from queue.')

            logger.info('Cancelling worker tasks...')
            for task in worker_tasks:
                task.cancel()

            await asyncio.gather(*worker_tasks, return_exceptions=True)
            logger.info('All worker tasks finished cancellation.')

        end_perf = time.perf_counter()
        self._stats.end_time = datetime.datetime.now(datetime.timezone.utc)
        self._stats.duration_seconds = round(end_perf - start_perf, 2)

        logger.info(f'Crawling finished in {self._stats.duration_seconds:.2f} seconds.')
        logger.info(f'Total URLs processed: {self._stats.total_urls_processed}')
        logger.info(f'Total request errors: {self._stats.total_errors_request}')
        logger.info(f'Total processing errors: {self._stats.total_errors_processing}')

        report = CrawlReport(
            start_url=self.start_url,
            max_depth=self.max_depth,
            allowed_domains=list(self.allowed_domains) if self.allowed_domains else None,
            blacklist_extensions=sorted(list(self.blacklist_extensions)),
            results=self._results,
            stats=self._stats,
        )
        return report
