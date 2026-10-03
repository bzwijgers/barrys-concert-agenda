from urllib.request import Request, urlopen
from urllib.parse import urlsplit, urlunsplit, quote
from urllib.error import HTTPError, URLError
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import html as html_module
import json
import time


# ============================================================
# ALGEMEEN
# ============================================================

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
    "Cache-Control": "no-cache",
}

MONTHS_SHORT = {
    "jan": 1,
    "feb": 2,
    "mrt": 3,
    "maa": 3,
    "apr": 4,
    "mei": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "nov": 11,
    "dec": 12,
}

MONTHS_LONG = {
    "januari": 1,
    "februari": 2,
    "maart": 3,
    "april": 4,
    "mei": 5,
    "juni": 6,
    "juli": 7,
    "augustus": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "december": 12,
}


def encode_url(url):
    parts = urlsplit(url)

    encoded_path = quote(
        parts.path,
        safe="/%:@"
    )

    encoded_query = quote(
        parts.query,
        safe="=&%:@/?"
    )

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            encoded_path,
            encoded_query,
            parts.fragment,
        )
    )


def download_page(url):
    safe_url = encode_url(url)

    request = Request(
        safe_url,
        headers=HEADERS
    )

    with urlopen(
        request,
        timeout=30
    ) as response:
        return response.read().decode(
            "utf-8",
            errors="replace"
        )


def download_page_retry(
    url,
    attempts=3
):
    last_error = None

    for attempt in range(attempts):
        try:
            return download_page(url)

        except Exception as error:
            last_error = error

            if attempt < attempts - 1:
                time.sleep(1)

    raise last_error


def clean_text(value):
    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html_module.unescape(
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalize_url(url):
    return (
        url
        .strip()
        .rstrip("/")
        .lower()
    )


def clean_json_text(text):
    return (
        text
        .replace("\\/", "/")
        .replace('\\"', '"')
        .replace("\\u0026", "&")
        .replace("\\u0027", "'")
        .replace("\\u2018", "‘")
        .replace("\\u2019", "’")
        .replace("\\u2013", "–")
        .replace("\\u2014", "—")
        .replace("&amp;", "&")
        .strip()
    )


def find_json_value(
    text,
    key
):
    regex = re.compile(
        r'"'
        + re.escape(key)
        + r'"\s*:\s*"((?:\\.|[^"\\])*)"',
        flags=re.IGNORECASE,
    )

    match = regex.search(text)

    if not match:
        return None

    return match.group(1)
