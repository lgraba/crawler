import pytest

from crawler.utils import get_domain, get_extension, is_valid_url, normalize_url, process_blacklist_input

# --- Tests for normalize_url ---


@pytest.mark.parametrize(
    'base, link, expected',
    [
        ('http://example.com', '/page', 'http://example.com/page'),
        ('http://example.com/path/', 'sub', 'http://example.com/path/sub'),
        ('http://example.com/path/', '../sub', 'http://example.com/sub'),
        ('http://example.com', 'http://other.com/page', 'http://other.com/page'),
        ('http://example.com', '//other.com/page', 'http://other.com/page'),
        ('https://example.com', '//other.com/page', 'https://other.com/page'),
        ('http://example.com', 'page.html#fragment', 'http://example.com/page.html'),  # Fragment removal
        ('http://example.com', '?query=1', 'http://example.com?query=1'),  # Query preserved
        ('http://example.com', 'mailto:a@b.com', None),  # Invalid scheme
        ('http://example.com', 'javascript:alert(1)', None),  # Invalid scheme
        ('http://example.com', '', 'http://example.com'),  # Empty link uses base
        ('http://example.com', '  /path \n', 'http://example.com/path'),  # Whitespace stripping
    ],
)
def test_normalize_url(base, link, expected):
    assert normalize_url(base, link) == expected


# --- Tests for get_domain ---


@pytest.mark.parametrize(
    'url, expected',
    [
        ('http://example.com', 'example.com'),
        ('https://www.example.com/path', 'www.example.com'),
        ('http://example.com:8080/page?q=1', 'example.com:8080'),
        ('ftp://ftp.example.com', 'ftp.example.com'),
        ('http://192.168.1.1/page', '192.168.1.1'),
        ('invalid-url', None),
        ('', None),
    ],
)
def test_get_domain(url, expected):
    assert get_domain(url) == expected


# --- Tests for get_extension ---


@pytest.mark.parametrize(
    'url, expected',
    [
        ('http://example.com/page.html', '.html'),
        ('http://example.com/archive.tar.gz', '.gz'),  # Gets last extension
        ('http://example.com/document.PDF', '.pdf'),  # Lowercase
        ('http://example.com/noextension', None),
        ('http://example.com/', None),
        ('http://example.com/path/.config', None),  # Hidden file is not treated as extension
        ('http://example.com/page.html?query=1#frag', '.html'),  # Ignores query/fragment
        ('http://example.com/.', None),  # Just a dot
    ],
)
def test_get_extension(url, expected):
    assert get_extension(url) == expected


# --- Tests for is_valid_url ---


@pytest.mark.parametrize(
    'url, domains, blacklist, expected',
    [
        # Basic valid
        ('http://example.com/page', None, None, True),
        ('https://example.com', None, None, True),
        # Scheme invalid
        ('ftp://example.com', None, None, False),
        ('mailto:a@b.com', None, None, False),
        # Domain restriction
        ('http://good.com/page', {'good.com', 'ok.com'}, None, True),
        ('http://bad.com/page', {'good.com', 'ok.com'}, None, False),
        ('http://good.com/page', None, None, True),
        # Blacklist restriction
        ('http://example.com/image.jpg', None, {'.jpg', '.png'}, False),
        ('http://example.com/page.html', None, {'.jpg', '.png'}, True),
        ('http://example.com/script.js', None, {'.js'}, False),
        ('http://example.com/noext', None, {'.jpg'}, True),
        # Combined
        ('http://good.com/image.jpg', {'good.com'}, {'.jpg'}, False),  # Blacklisted
        ('http://bad.com/page.html', {'good.com'}, {'.jpg'}, False),  # Wrong domain
        ('http://good.com/page.html', {'good.com'}, {'.jpg'}, True),  # OK
    ],
)
def test_is_valid_url(url, domains, blacklist, expected):
    allowed_domain_set = set(domains) if domains else None
    blacklist_set = set(blacklist) if blacklist else None
    assert is_valid_url(url, allowed_domain_set, blacklist_set) == expected


# --- Tests for process_blacklist_input ---


def test_process_blacklist_input_none():
    """Test with None input."""
    assert process_blacklist_input(None) is None


def test_process_blacklist_input_empty_string():
    """Test with an empty string input."""
    assert process_blacklist_input('') is None


def test_process_blacklist_input_string_simple():
    """Test with a simple comma-separated string."""
    result = process_blacklist_input('.jpg,.png, .gif')
    assert sorted(result) == ['.gif', '.jpg', '.png']


def test_process_blacklist_input_string_no_dots():
    """Test string input needing dot prefix."""
    result = process_blacklist_input('css, js,html')
    assert sorted(result) == ['.css', '.html', '.js']


def test_process_blacklist_input_string_mixed():
    """Test string with mixed dots, spacing, duplicates."""
    result = process_blacklist_input(' .jpeg, css,, .jpeg , svg')
    assert sorted(result) == ['.css', '.jpeg', '.svg']


def test_process_blacklist_input_file_simple(tmp_path):
    """Test reading from a valid file."""
    p = tmp_path / 'blacklist.txt'
    p.write_text('.mp4, .mov, .pdf,\n.png')  # Content with newline
    result = process_blacklist_input(str(p))
    assert sorted(result) == ['.mov', '.mp4', '.pdf', '.png']


def test_process_blacklist_input_file_empty(tmp_path):
    """Test reading from an empty file."""
    p = tmp_path / 'empty_blacklist.txt'
    p.write_text('')
    result = process_blacklist_input(str(p))
    assert result == []


def test_process_blacklist_input_file_not_found():
    """Test input string looks like a path but file doesn't exist."""
    with pytest.raises(IOError, match='looks like a path but file not found'):
        process_blacklist_input('./nonexistent/file.txt')


def test_process_blacklist_input_file_read_error(tmp_path, monkeypatch):
    """Test handling of file read errors."""
    p = tmp_path / 'unreadable.txt'
    p.touch()

    def mock_open(*args, **kwargs):
        if args[0] == str(p):
            raise IOError('Permission denied (mocked)')
        return open(*args, **kwargs)

    monkeypatch.setattr('builtins.open', mock_open)

    with pytest.raises(IOError, match='Could not read blacklist file'):
        process_blacklist_input(str(p))
