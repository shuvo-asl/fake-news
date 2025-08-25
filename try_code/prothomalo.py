# Awesome — let’s scrape the Education section from prothomalo.com.

# Here’s a robust Python scraper that:
# - Collects article URLs from the Education section (with simple pagination discovery)
# - Extracts title, author, publish time, description, image, keywords, section, and full text
# - Respects robots.txt (optional)
# - Saves to JSONL or CSV
# - Includes retries, random delays, and a realistic User-Agent

# Setup
# - Python 3.9+
# - pip install: requests, beautifulsoup4, lxml

# Code
# ```python
# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

import argparse
import csv
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib.robotparser import RobotFileParser
from urllib3.util.retry import Retry

BASE = "https://www.prothomalo.com"
SECTION_PATH = "/education"


def make_session():
    sess = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"])
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "bn-BD,bn;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return sess


def normalize_url(url, base=BASE):
    url = urljoin(base, url)
    # strip query and fragment
    u = urlparse(url)
    return urlunparse((u.scheme, u.netloc, u.path, "", "", ""))


def parse_iso8601(dt):
    if not dt:
        return None
    try:
        # Handle Z or offset formats
        dt = dt.replace("Z", "+00:00")
        return datetime.fromisoformat(dt).astimezone(timezone.utc).isoformat()
    except Exception:
        return dt  # keep raw if unknown format


def load_robots(base=BASE):
    rp = RobotFileParser()
    rp.set_url(urljoin(base, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass
    return rp


def allowed_by_robots(rp, url, ua="*"):
    try:
        return rp.can_fetch(ua, url)
    except Exception:
        return True  # be permissive if robots cannot be parsed


def get_soup(session, url, timeout=20):
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    # BeautifulSoup auto-detects encoding; the site is UTF-8
    return BeautifulSoup(r.text, "lxml")


def extract_links_from_listing(soup, base=BASE):
    # Select anchors pointing to Education subsection articles
    links = set()
    for a in soup.select('a[href]'):
        href = a.get("href", "")
        if not href:
            continue
        # Must belong to education section
        if "/education" not in href:
            continue
        # Avoid category root and tag pages by preferring deeper paths
        url = normalize_url(href, base)
        # Heuristic: article URLs often have more than 2 path segments
        path_parts = urlparse(url).path.strip("/").split("/")
        if len(path_parts) >= 2:  # keep broad; adjust if too many non-articles appear
            links.add(url)
    return sorted(links)


def find_next_page_url(soup, current_url):
    # Try rel=next first
    link = soup.select_one('link[rel="next"], a[rel="next"]')
    if link and link.get("href"):
        return normalize_url(link["href"])

    # Look for common "Next" anchors (Bangla/English)
    candidates = soup.select('a[href]')
    for a in candidates:
        txt = (a.get_text(strip=True) or "").lower()
        if txt in ("next", "older", "পরবর্তী", "আরও", "আরো", "আরও দেখুন"):
            return normalize_url(a["href"])

    # Fallback to incrementing ?page=
    parsed = urlparse(current_url)
    qs = dict(parse_qsl(parsed.query))
    if "page" in qs:
        try:
            nxt = int(qs["page"]) + 1
            qs["page"] = str(nxt)
            return urlunparse(parsed._replace(query=urlencode(qs)))
        except Exception:
            pass
    else:
        # Try adding page=2
        qs["page"] = "2"
        return urlunparse(parsed._replace(query=urlencode(qs)))

    return None


def extract_json_ld(soup):
    items = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            if isinstance(data, list):
                items.extend(data)
            elif isinstance(data, dict):
                items.append(data)
        except Exception:
            continue
    return items


def _type_matches(t, names):
    if isinstance(t, str):
        return t in names
    if isinstance(t, list):
        return any(x in names for x in t)
    return False


def extract_text_from_html(soup):
    # Try likely content containers first
    selectors = [
        "article",
        'div[itemprop="articleBody"]',
        'div[class*="article-body"]',
        'div[class*="content"]',
        'div[class*="story"]',
        'section[class*="content"]',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            pts = [p.get_text(" ", strip=True) for p in el.find_all("p")]
            pts = [t for t in pts if t]
            if pts:
                return "\n\n".join(pts)

    # Fallback: use all <p>, but cap to reduce noise
    pts = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    pts = [t for t in pts if t]
    if pts:
        return "\n\n".join(pts[:60])
    return None


def extract_from_meta(soup, key, attr="property"):
    sel = soup.find("meta", {attr: key})
    if sel and sel.get("content"):
        return sel["content"].strip()
    return None


def parse_article(session, url):
    soup = get_soup(session, url)

    data = {
        "url": url,
        "source": "prothomalo.com",
        "section": "education",
        "lang": "bn",
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }

    # Prefer JSON-LD
    ld = extract_json_ld(soup)
    article_obj = None
    for obj in ld:
        if _type_matches(obj.get("@type"), ["NewsArticle", "Article"]):
            article_obj = obj
            break

    if article_obj:
        data["title"] = article_obj.get("headline") or article_obj.get("name")
        data["description"] = article_obj.get("description")
        data["published_at"] = parse_iso8601(article_obj.get("datePublished"))
        data["updated_at"] = parse_iso8601(article_obj.get("dateModified"))
        auth = article_obj.get("author")
        if isinstance(auth, dict):
            data["author"] = auth.get("name")
        elif isinstance(auth, list):
            data["author"] = ", ".join([a.get("name") if isinstance(a, dict) else str(a) for a in auth])
        elif isinstance(auth, str):
            data["author"] = auth

        img = article_obj.get("image")
        if isinstance(img, dict):
            data["image"] = img.get("url")
        elif isinstance(img, list):
            data["image"] = img[0] if img else None
        elif isinstance(img, str):
            data["image"] = img

        kw = article_obj.get("keywords")
        if isinstance(kw, list):
            data["keywords"] = kw
        elif isinstance(kw, str):
            data["keywords"] = [k.strip() for k in kw.split(",") if k.strip()]

        data["article_section"] = article_obj.get("articleSection")
        data["text"] = article_obj.get("articleBody")

    # Meta tag fallbacks
    if not data.get("title"):
        data["title"] = extract_from_meta(soup, "og:title") or (soup.title.get_text(strip=True) if soup.title else None)
    if not data.get("description"):
        data["description"] = extract_from_meta(soup, "og:description") or extract_from_meta(soup, "description", attr="name")
    if not data.get("published_at"):
        data["published_at"] = parse_iso8601(extract_from_meta(soup, "article:published_time"))
    if not data.get("image"):
        data["image"] = extract_from_meta(soup, "og:image")
    if not data.get("author"):
        data["author"] = extract_from_meta(soup, "author", attr="name") or extract_from_meta(soup, "article:author")

    if not data.get("text"):
        data["text"] = extract_text_from_html(soup)

    return data


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(path, rows):
    if not rows:
        return
    # Gather all keys to keep columns stable
    keys = sorted(set().union(*(r.keys() for r in rows)))
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def scrape_education(pages=1, max_articles=None, out="education.jsonl", out_format="jsonl",
                     min_delay=1.5, max_delay=3.5, respect_robots=True):
    session = make_session()
    rp = load_robots() if respect_robots else None

    start_url = urljoin(BASE, SECTION_PATH)
    ua_token = session.headers.get("User-Agent", "Mozilla/5.0")
    if rp and not allowed_by_robots(rp, start_url,ua=ua_token):
        print("Blocked by robots.txt for the section page. Exiting.", file=sys.stderr)
        return

    all_links = []
    seen = set()
    current = start_url

    for i in range(pages):
        print(f"[Listing] Fetching: {current}")
        try:
            soup = get_soup(session, current)
        except Exception as e:
            print(f"Failed to fetch listing page: {e}", file=sys.stderr)
            break

        links = extract_links_from_listing(soup, base=BASE)
        # Filter by robots and dedupe
        for url in links:
            if url in seen:
                continue
            if rp and not allowed_by_robots(rp, url):
                continue
            seen.add(url)
            all_links.append(url)
            if max_articles and len(all_links) >= max_articles:
                break

        print(f"  Found {len(links)} links (unique total: {len(all_links)})")

        if max_articles and len(all_links) >= max_articles:
            break

        next_url = find_next_page_url(soup, current)
        if not next_url:
            print("No next page detected.")
            break
        current = next_url

        time.sleep(random.uniform(min_delay, max_delay))

    # Fetch articles
    print(f"\n[Articles] Fetching up to {len(all_links)} article pages...")
    rows = []
    for idx, url in enumerate(all_links, 1):
        try:
            row = parse_article(session, url)
            rows.append(row)
            print(f"  [{idx}/{len(all_links)}] {row.get('title') or url}")
        except Exception as e:
            print(f"  Error parsing {url}: {e}", file=sys.stderr)

        time.sleep(random.uniform(min_delay, max_delay))

    # Output
    if out_format == "jsonl":
        write_jsonl(out, rows)
    elif out_format == "csv":
        write_csv(out, rows)
    else:
        print("Unknown output format; defaulting to JSONL", file=sys.stderr)
        write_jsonl(out, rows)

    print(f"\nSaved {len(rows)} records to {out}")


def main():
    p = argparse.ArgumentParser(description="Scrape Prothom Alo Education section")
    p.add_argument("--pages", type=int, default=1, help="Max listing pages to crawl")
    p.add_argument("--max-articles", type=int, default=None, help="Max number of articles")
    p.add_argument("--out", type=str, default="education.jsonl", help="Output file path")
    p.add_argument("--format", type=str, choices=["jsonl", "csv"], default="jsonl", help="Output format")
    p.add_argument("--min-delay", type=float, default=1.5, help="Min delay between requests (seconds)")
    p.add_argument("--max-delay", type=float, default=3.5, help="Max delay between requests (seconds)")
    p.add_argument("--no-robots", action="store_true", help="Ignore robots.txt")
    args = p.parse_args()

    scrape_education(
        pages=args.pages,
        max_articles=args.max_articles,
        out=args.out,
        out_format=args.format,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        respect_robots=not args.no_robots,
    )


if __name__ == "__main__":
    main()
# ```

# How to run
# - Install deps:
#   - pip install requests beautifulsoup4 lxml
# - Run:
#   - python prothomalo_education_scraper.py --pages 2 --max-articles 40 --out education.jsonl
#   - Or CSV: python prothomalo_education_scraper.py --pages 3 --format csv --out education.csv

# Notes and tips
# - Always review robots.txt and the site’s Terms before scraping.
# - If you get 403/Access Denied (e.g., Cloudflare), consider using Playwright for a headful browser-based scrape and keep delays gentle.
# - The script uses JSON-LD and OpenGraph meta tags for reliability, with HTML fallback for the article body.
# - Content is in Bangla; the file is UTF-8 encoded.

# Want me to tailor this for specific fields (e.g., only title + URL + date), or store into SQLite/Google Sheets?