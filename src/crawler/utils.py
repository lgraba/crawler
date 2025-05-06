import logging
import os
from typing import List, Optional, Set
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


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


def process_blacklist_input(input_value: Optional[str]) -> Optional[List[str]]:
    """
    Processes the blacklist input; a comma-separated string of extensions or a path to a file containing them.

    Args:
        input_value: The string provided via the --blacklist argument, or None.

    Returns:
        A list of cleaned blacklist extensions (lowercase, starting with '.'), or None if no input_value was provided.
        Returns an empty list if the input was provided but contained no valid extensions.

    Raises:
        IOError: If input_value looks like a file but cannot be read.
        Exception: For other unexpected processing errors.
    """
    if not input_value:
        return None

    blacklist_items_raw = []
    processed_extensions_set: Set[str] = set()

    if os.path.exists(input_value) and os.path.isfile(input_value):
        logger.info(f'Reading blacklist extensions from file: {input_value}')
        try:
            with open(input_value, 'r', encoding='utf-8') as f:
                content = ''.join(f.readlines())
                blacklist_items_raw = [item.strip() for item in content.split(',') if item.strip()]
        except IOError as e:
            logger.error(f"IOError reading blacklist file '{input_value}': {e}")
            raise IOError(f"Could not read blacklist file '{input_value}'") from e
        except Exception as e:
            logger.error(f"Unexpected error reading file '{input_value}': {e}", exc_info=True)
            raise Exception(f"Failed to process blacklist file '{input_value}'") from e

    else:
        if os.path.sep in input_value and not os.path.exists(input_value):
            logger.warning(
                f"Blacklist argument '{input_value}' looks like a path but file not found. Treating it as comma-separated string!"
            )
        else:
            logger.info('Processing blacklist extensions from command line string')
        try:
            blacklist_items_raw = [item.strip() for item in input_value.split(',') if item.strip()]
        except Exception as e:
            logger.error(f"Unexpected error splitting blacklist string '{input_value}': {e}", exc_info=True)
            raise ValueError(f"Failed to parse blacklist string '{input_value}'.") from e

    if blacklist_items_raw:
        for ext in blacklist_items_raw:
            clean_ext = ext.lower()
            if not clean_ext.startswith('.'):
                clean_ext = '.' + clean_ext
            processed_extensions_set.add(clean_ext)
        logger.debug(f'Processed blacklist extensions (set): {processed_extensions_set}')

        return sorted(list(processed_extensions_set))
    else:
        logger.info('Blacklist input provided, but it resulted in an empty list!')
        return []
