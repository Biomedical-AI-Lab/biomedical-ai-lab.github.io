import os
from serpapi import GoogleSearch
from util import *


def main(entry):
    """
    receives single list entry from google-scholar data file
    returns list of sources to cite

    Google Scholar has no official API, so this uses SerpAPI
    (https://serpapi.com), which needs a GOOGLE_SCHOLAR_API_KEY secret.
    Without the key this plugin is skipped, so the rest of the site still builds.

    Entry fields (in _data/google-scholar.yaml):
      gsid:    Google Scholar user id (from the profile URL, user=...)
      from:    optional; skip papers published before this year
      exclude: optional; list of titles (or the start of titles) to leave out
    """

    # get api key (serp api key to access google scholar)
    api_key = os.environ.get("GOOGLE_SCHOLAR_API_KEY", "")
    if not api_key:
        log('No "GOOGLE_SCHOLAR_API_KEY" secret, skipping Google Scholar', indent=3, level="WARNING")
        return []

    # get id from entry
    _id = get_safe(entry, "gsid", "")
    if not _id:
        raise Exception('No "gsid" key')

    from_year = int(get_safe(entry, "from", 0) or 0)
    exclude = [normalize_title(t) for t in get_safe(entry, "exclude", []) or []]

    # query api: newest first ("sort by year" on the profile page), 100 per page
    @log_cache
    @cache.memoize(name=__file__, expire=1 * (60 * 60 * 24))
    def query(_id):
        articles = []
        for start in range(0, 500, 100):
            params = {
                "engine": "google_scholar_author",
                "api_key": api_key,
                "author_id": _id,
                "sort": "pubdate",
                "num": 100,  # max allowed
                "start": start,
            }
            page = get_safe(GoogleSearch(params).get_dict(), "articles", [])
            articles += page
            # stop once a page is short, or once it reaches papers older than "from"
            years = [int(a.get("year") or 0) for a in page]
            if len(page) < 100 or (from_year and years and min(years) < from_year):
                break
        return articles

    response = query(_id)

    # list of sources to return
    sources = []

    # go through response and format sources
    for work in response:
        year = get_safe(work, "year", "")
        title = get_safe(work, "title", "")

        # Scholar lists some items without a year; they can't be placed, so skip
        if not year:
            continue
        if from_year and int(year) < from_year:
            continue
        if any(normalize_title(title).startswith(e) for e in exclude if e):
            continue

        sources.append(
            {
                # no "id": Scholar ids aren't citeable by Manubot, so keep the
                # details Scholar gives instead
                "scholar_id": get_safe(work, "citation_id", ""),
                "title": title,
                "authors": list(map(str.strip, get_safe(work, "authors", "").split(","))),
                "publisher": get_safe(work, "publication", ""),
                "date": year + "-01-01",
                "link": get_safe(work, "link", ""),
            }
        )

    return sources
