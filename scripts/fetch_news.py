
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS = [
    ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
    ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
    ("CISA Advisories", "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
]
PER_FEED = 6
MAX_TOTAL = 18


def local(tag):
    return tag.split("}")[-1]


def parse_date(s):
    now = datetime.now(timezone.utc)
    if not s:
        return now
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
        except Exception:
            return now
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def read_feed(name, url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as r:
        root = ET.fromstring(r.read())
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        kids = {}
        for c in el:
            kids.setdefault(local(c.tag), c)
        title = (kids["title"].text or "").strip() if "title" in kids else ""
        link = ""
        if "link" in kids:
            link = kids["link"].attrib.get("href") or (kids["link"].text or "")
        link = link.strip()
        raw_date = None
        for key in ("pubDate", "published", "updated", "date"):
            if key in kids and kids[key].text:
                raw_date = kids[key].text
                break
        date = parse_date(raw_date)
        if title and link.startswith(("http://", "https://")):
            items.append({"title": title, "link": link, "source": name, "date": date.isoformat()})
    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:PER_FEED]


def main():
    all_items = []
    for name, url in FEEDS:
        try:
            all_items += read_feed(name, url)
            print("ok  ", name)
        except Exception as e:  # one broken feed should not stop the others
            print("skip", name, e)
    all_items.sort(key=lambda x: x["date"], reverse=True)
    out = {"updated": datetime.now(timezone.utc).isoformat(), "items": all_items[:MAX_TOTAL]}
    if not out["items"]:
        raise SystemExit("No news fetched, keeping the previous file.")
    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("wrote", len(out["items"]), "items")


if __name__ == "__main__":
    main()
