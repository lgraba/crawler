import argparse
import asyncio
import logging
import sys
from typing import List, Optional

from crawler import Crawler
from crawler.utils import process_blacklist_input


async def run_crawl():
    parser = argparse.ArgumentParser(description='Simple Async Web Crawler')
    parser.add_argument('start_url', help='The starting URL to crawl')
    parser.add_argument('--max-depth', type=int, default=1, help='Maximum crawl depth (0 means only start URL)')
    parser.add_argument('--domains', nargs='*', help='List of allowed domains (optional)')
    parser.add_argument(
        '--blacklist',
        help="Comma-separated list of file extensions (e.g. '.jpg,.png') or path to a file (e.g. 'path/to/blacklist.txt') containing a comma-separated list of extensions to ignore",
    )
    parser.add_argument('--concurrency', type=int, default=10, help='Number of concurrent workers')
    parser.add_argument('--timeout', type=float, default=10.0, help='Request timeout in seconds')
    parser.add_argument('--user-agent', help='Custom User-Agent string')
    parser.add_argument('--output-json', help='File path to save the results as JSON')
    parser.add_argument(
        '--no-verify-ssl', action='store_true', help='Disable SSL certificate verification (use with caution)'
    )
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase logging verbosity (-v for INFO, -vv for DEBUG)'
    )

    args = parser.parse_args()

    # blacklist file vs. list handling
    blacklist_extensions: Optional[List[str]] = None

    try:
        blacklist_extensions = process_blacklist_input(args.blacklist)
    except (IOError, ValueError, Exception) as e:
        logging.error(f'Failed to process blacklist: {e}')

        if not isinstance(e, (IOError, ValueError)):
            logging.exception('Unexpected error during blacklist processing.')

        sys.exit(1)

    # logging config
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARNING

    logging.basicConfig(
        level=log_level, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s', stream=sys.stdout
    )

    if log_level >= logging.INFO:
        library_log_level = logging.WARNING
    else:
        library_log_level = logging.DEBUG

    # set httpx/httpcore logging level explicitly to avoid noise
    logging.getLogger('httpx').setLevel(library_log_level)
    logging.getLogger('httpcore').setLevel(library_log_level)

    try:
        crawler = Crawler(
            start_url=args.start_url,
            max_depth=args.max_depth,
            allowed_domains=args.domains,
            blacklist_extensions=blacklist_extensions,
            concurrency=args.concurrency,
            timeout=args.timeout,
            user_agent=args.user_agent,
            verify_ssl=not args.no_verify_ssl,
        )
    except ValueError as e:
        logging.error(f'Initialization Error: {e}')
        sys.exit(1)

    report = await crawler.crawl()

    print('\n' + '=' * 30 + ' Crawl Summary ' + '=' * 30)
    print(f'Start URL:         {report.start_url}')
    print(f'Max Depth:         {report.max_depth}')
    if report.allowed_domains:
        print(f'Allowed Domains:   {", ".join(report.allowed_domains)}')
    print(f'Duration:          {report.stats.duration_seconds:.2f} seconds')
    print(f'URLs Processed:    {report.stats.total_urls_processed}')
    print(f'Request Errors:    {report.stats.total_errors_request}')
    print(f'Processing Errors: {report.stats.total_errors_processing}')

    print('\nStatus Code Counts:')
    if report.stats.status_code_counts:
        for code, count in sorted(report.stats.status_code_counts.items()):
            print(f'  {code}: {count}')
    else:
        print('  None')

    print('\nDomain Counts (Top 10):')
    if report.stats.domain_counts:
        sorted_domains = sorted(report.stats.domain_counts.items(), key=lambda item: item[1], reverse=True)
        for domain, count in sorted_domains[:10]:
            print(f'  {domain}: {count}')
        if len(sorted_domains) > 10:
            print('  ...')
    else:
        print('  None')
    print('=' * 75)

    if args.output_json:
        print(f'\nSaving results to {args.output_json}...')
        try:
            with open(args.output_json, 'w', encoding='utf-8') as f:
                f.write(report.model_dump_json(indent=2))
            print('Successfully saved results.')
        except IOError as e:
            print(f'Error saving results to JSON file: {e}', file=sys.stderr)
        except Exception as e:
            print(f'An unexpected error occurred during JSON serialization: {e}', file=sys.stderr)


if __name__ == '__main__':
    asyncio.run(run_crawl())
