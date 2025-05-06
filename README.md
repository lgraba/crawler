# Crawler

A Python web crawler


## Getting Started

1. `poetry install`
2. `poetry run python main.py -h`
3. `poetry run python main.py {start_url} --max-depth 10`

Here are some sites that you may want to try crawling:
* `https://quotes.toscrape.com/`
* `https://webscraper.io/test-sites/e-commerce/allinone`

E.g.

```
poetry run python main.py https://quotes.toscrape.com/ --max-depth 2 --domains quotes.toscrape.com --output-json stats.json
```

This command will:
* Crawl starting at `https://quotes.toscrape.com/`
* To a `max-depth` of 2 (where start_url is 0)
* Adhering to `quotes.toscrape.com` domain pages
* With the default verbosity of `INFO`
* Placing output statistics in `stats.json`

### Blacklist Extensions

Note that there is a default blacklist containing common file extensions one would not normally want to crawl. If one supplies a blacklist at execution time, only specified extensions will be blacklisted. You may supply a blacklist via a comma-separated list of file extensions either via command-line or file.

E.g. Supplying a file of blacklist extensions

```
poetry run python main.py https://quotes.toscrape.com/ --max-depth 2 --blacklist example.blacklist.txt --output-json stats.json
```

### Output Statistics

To see the full aggregated output statistics, specify `--output-json {filename}`. This contains the **Outputs** and **Statistics** defined below in the project requirements. Here is an example, abbreviated:

```
{
  "allowed_domains": null,
  "blacklist_extensions": [
    ".jpg",
    ".logan",
    ".png"
  ],
  "max_depth": 2,
  "results": [
    {
      "content_size": 11064,
      "depth": 0,
      "error": null,
      "status_code": 200,
      "timestamp": "2025-05-06T04:57:00.258309Z",
      "title": "Quotes to Scrape",
      "url": "https://quotes.toscrape.com/"
    },
    ... (n - 1 result objects)
  ],
  "start_url": "https://quotes.toscrape.com/",
  "stats": {
    "domain_counts": {
      "quotes.toscrape.com": 149,
      "www.goodreads.com": 234,
      "www.zyte.com": 47,
      "help.goodreads.com": 2,
      "www.facebook.com": 2,
      "twitter.com": 2,
      "www.instagram.com": 2,
      "www.linkedin.com": 2,
      "itunes.apple.com": 1,
      "play.google.com": 1,
      "app.zyte.com": 5,
      "support.zyte.com": 1,
      "docs.zyte.com": 2,
      "discord.com": 2,
      "info.zyte.com": 1,
      "www.youtube.com": 1
    },
    "duration_seconds": 22.02,
    "end_time": "2025-05-06T04:57:22.017346Z",
    "start_time": "2025-05-06T04:56:59.999426Z",
    "status_code_counts": {
      "200": 449,
      "429": 1,
      "400": 2
    },
    "total_errors_processing": 0,
    "total_errors_request": 2,
    "total_urls_processed": 454
  }
}
```


## Project Requirements

### Inputs

| Input     | Description                                                                |
| --------- | -------------------------------------------------------------------------- |
| max-depth | The maximum depth of links to crawl                                        |
| domains   | A list of domains to restrict crawling to; if none, crawl all links        |
| blacklist | A file or list of extensions to ignore during crawling (e.g. .jpg, .css)   |

### Outputs

For each crawled URL, we capture the following information:

| Output       | Description                                                     |
| ------------ | --------------------------------------------------------------- |
| status_code  | HTTP status code                                                |
| content_size | Content size in bytes                                           |
| title        | Title of the page, derived from `<title>` HTML tag if available |

### Statistics

For a collection of crawled URLs, we calculate the following statistics:

| Statistic               | Description                                                          |
| ----------------------- | -------------------------------------------------------------------- |
| total_urls_processed    | Total number of URLs crawled                                         |
| total_errors_request    | Total number of network request errors encounted during crawling     |
| total_errors_processing | Total number of internal processing errors encounted during crawling |
| status_code_counts      | Number of crawled URLs per HTTP status                               |
| domain_counts           | Number of crawled URLs per domain                                    |

#### Logan Note: 

I bifurcated the "Total number of errors" requirement into two separate statistics in order to provide valuable diagnostic information. For example, if we have a large `total_errors_request`, then it points toward network instability, IP bans/blocking by the target server(s), DNS issues, incorrect proxy configuration, or timeout settings being too restrictive. If we have a large `total_errors_processing`, then it points toward potential bugs in parsing logic, handling certain content types/encodings, or programmatic errors within our code. Furthermore, we choose to treat HTTP errors like 404, 500 as valid responses from the server and _do not_ increment either of these counters. We do, however, track these in the `status_code` and `status_code_counts` values. This design choice is made to segregate concerns in the most useful way possible.

## Planning

### Key Considerations:

* Crawling Library: This is probably the most critical consideration. Performance/scalability and future expandability are my primary concerns.
  * **requests + bs4** (sync): Will result in IO-bound, sequential requests; concurrency would have to be handled separately
  * **aiohttp + bs4** (async): Utilizes asyncio
  * **httpx + bs4** (sync/async): Gives the option of starting with sync and moving to async if requirements necessitate
  * **Scrapy**: Crawling framework; may be overkill for this project. Opinionated with project structure/concepts. Typically run as a standalone process. Could be fun to learn about.
* Concurrency: How will the crawler handle multiple requests simultaneously?
  * **Sync**
  * **Async**
    * Async would integrate well with an async API framework like FastAPI and provide good concurrency without the overhead of threads. Should scale well.
  * **Threaded**
* API Framework: While this is not a requirement, it's an important extensibility consideration.
  * **FastAPI**
    * I'd prefer to use FastAPI dude to its native asyncio support, and Pydantic can be used for input validation
  * **Flask**
  * **Django**
* Crawl State Management:
  * **In-memory**
    * Most appropriate for a simple CLI script
  * **DB**
    * Each API call + crawl could be arguably short-lived, so a persistent store may not be necessary (but would be nice for scalability). It shouldn't be too much overhead for me to spin up, and would allow me to showcase some ERD design.
* Data Storage for Outputs/Statistics:
  * **In-memory**
    * Most appropriate for a simple CLI script
  * **Temporary files**
  * **DB** (SQLite, Redis, PostgreSQL)
    * Starting with ephemeral, in-memory would seem to be appropriate given the scope, but I'd really like to implement persistence via DB (minimal overhead when dockerized)
* Handling Input Constraints (max-depth, domains, blacklist)
  * **Check when adding to the queue**:
    * `max-depth`: Track the depth of the current URL and only add links found on it to the queue if `current_depth + 1 <= max_depth`
    * `domain`: Parse the domain of extracted links and only add the link to the queue if its domain is in the allowed list or list is empty (urllib.parse.urlparse)
    * `blacklist`: Check the file extensions against the blacklist before adding to the queue (os.path.splitext)
  * **Check before making the request**:
    * Would separate filtering from parsing, but we may have inappropriate URLs on the queue
* Error Handling
  * **Log and Continue**
    * Allows us to gather the required statistics; We can store them ephemerally or persistently
    * Note that we must account for parsing errors, separate from an HTTP error status
  * **Retry mechanism**
    * If I have time, I may implement a configurable retry mechanism (e.g. `retry-count` input param)
  * **Halt on Error**

### Key Choices:

I'm going to start with the simple CLI script, adhering to the states requirements. However, I want to keep options open for future extensibility, robustness, and possible integration into an API that would make this a standalone service.

#### Crawling Library: httpx + bs4
* Lighter-weight solution
* Gives us the option of sync/async (I'll be utilizing async for concurrency)
* Would seamlessly integrate with FastAPI (future extensibility)
* Allows us to fully control the crawling logic (queue, depth, filtering)
* Less verbose than aiohttp
* Supports HTTP/1.1 and HTTP/2
* Modern with nice API
* Appropriate for the scale of project and base requirements

#### Concurrency: Async
* I'd like requests to made concurrently without the overhead of threads.

#### Crawl State Management: In-memory
* For the given scope of this small project, we'll stick to in-memory state management for now. For a more robust, production-level implementation a persistent database store would be most appropriate. Redis, for example, is very fast for queue/set operations.

#### Data Storage for Outputs/Statistics: In-memory
* Again, I'd like to have persistent data storage via a database (Postgres) in the future.

#### Handling Input Constraints: Check when adding to the queue

#### Error Handling: Log and Continue

#### Infrastructure: Start with a simple CLI script
* In the future, assuming we want to implement a full API service encompassing this crawler, I would containerize it (especially if we're adding persistent database storage). This would allow us to maintain architecture independence, easiest start-up for additional developers to start using it, and easy deployment to remote environments.
* CI/CD is a further consideration: automated test runs upon PR via Github Actions would be a good idea to implement for a more robust developmental methodology.

#### Developer Experience
* Dependency management via Poetry
* Ruff linting rules in pyproject.toml for consistency and ensured readability
* (future) Containerization for easy start-up, transportability across architectures, and future extensibility (like when we want to make this an actual service). This only makes sense with additional infrastructure. Assuming segregated containers (API service, postgres, redis) I would use Docker Compose for local container orchestration.


## ToDo

1. Unit testing
2. Performance testing (start up, concurrency I/O, memory complexity, etc.)
3. Persistent storage via a database like Redis (good for queue/set) and/or Postrgres
4. Peristent configuration via .env (or SSM for actual service)
4. FastAPI implementation for an actual service + CICD
5. Retry configuration and mechanism
