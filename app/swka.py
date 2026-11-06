"""Parser for the Studierendenwerk Karlsruhe meal plan (www.sw-ka.de).

The page for one canteen shows a whole calendar week when called with `?kw=<iso week>`.
Each day is a `div.canteen-day`, matched to its date through the day navigation
(`a#canteen_day_nav_<n>` with `rel="YYYY-MM-DD"`). Inside a day every line ("Linie 1",
"Schnitzelbar", ...) is a `tr.mensatype_rows` with the line name in `td.mensatype` and the
meals in `td.mensadata`.

The markup leaves `<tr>` elements unclosed, so it has to be parsed with lxml, which repairs
the tree the same way a browser does.
"""

import concurrent.futures
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta

from bs4 import BeautifulSoup, Tag

from app.feedv2.feed import Canteen, CanteenDay, Category, Meal

BASE_URL = "https://www.sw-ka.de/de/hochschulgastronomie/speiseplan/"
USER_AGENT = "openmensa-karlsruhe (+https://github.com/Atgoogat/openmensa-karlsruhe)"
REQUEST_TIMEOUT = 15  # seconds
RETRIES = 3
RETRY_DELAY = 2  # seconds

# price_<n> span classes on the page -> OpenMensa roles
PRICE_ROLES = {
    "price_1": "student",
    "price_2": "other",
    "price_3": "employee",
    "price_4": "pupil",
}

# Legend from the official sw-ka list (Stand 01.09.2025)
ALLERGENS = {
    "Ca": "Cashewnüsse",
    "Di": "Dinkel",
    "Ei": "Eier",
    "Er": "Erdnüsse",
    "Fi": "Fisch",
    "Ge": "Gerste",
    "Hf": "Hafer",
    "Ha": "Haselnüsse",
    "Ka": "Kamut",
    "Kr": "Krebstiere",
    "Lu": "Lupine",
    "Ma": "Mandeln",
    "ML": "Milch/Laktose",
    "Pa": "Paranüsse",
    "Pe": "Pekannüsse",
    "Pi": "Pistazien",
    "Qu": "Macadamianüsse",
    "Ro": "Roggen",
    "Sa": "Sesam",
    "Se": "Sellerie",
    "Sf": "Schwefeldioxid/Sulfit",
    "Sn": "Senf",
    "So": "Soja",
    "Wa": "Walnüsse",
    "We": "Weizen",
    "Wt": "Weichtiere",
}
ADDITIVES = {
    "1": "mit Farbstoff",
    "2": "mit Konservierungsstoff",
    "3": "mit Antioxidationsmittel",
    "4": "mit Geschmacksverstärker",
    "5": "mit Phosphat",
    "6": "Oberfläche gewachst",
    "7": "geschwefelt",
    "8": "Oliven geschwärzt",
    "9": "mit Süßungsmitteln",
    "10": "kann bei übermäßigem Verzehr abführend wirken",
    "11": "enthält eine Phenylalaninquelle",
    "12": "kann Restalkohol enthalten",
    "14": "aus Fleischstücken zusammengefügt",
    "15": "mit kakaohaltiger Fettglasur",
    "27": "aus Fischstücken zusammengefügt",
    "LAB": "mit tierischem Lab",
    "GEL": "mit Gelatine",
}

logger = logging.getLogger(__name__)


class UpstreamUnavailable(Exception):
    """sw-ka.de could not be reached or returned a server error."""


def _fetch(url: str) -> str:
    lastErr: Exception | None = None
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as err:
            if err.code < 500:
                raise UpstreamUnavailable(f"{url}: HTTP {err.code}") from err
            lastErr = err
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            lastErr = err
        if attempt < RETRIES - 1:
            time.sleep(RETRY_DELAY)
    raise UpstreamUnavailable(f"{url}: {lastErr}") from lastErr


def _text(el: Tag | None) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)).strip() if el else ""


def toPrice(price: str) -> float | None:
    m = re.search(r"\d+(?:,\d+)?", price)
    return float(m.group(0).replace(",", ".")) if m else None


def _codeNotes(codes: str) -> list[str]:
    notes = []
    for code in (c.strip() for c in codes.split(",")):
        if not code:
            continue
        if code in ALLERGENS:
            notes.append(ALLERGENS[code])
        elif code in ADDITIVES:
            notes.append(ADDITIVES[code])
        else:
            notes.append(code)
    return notes


def _parseMealRow(title: Tag) -> tuple[str, list[str], dict[str, float]]:
    row = title.find_parent("tr")
    name = _text(title.find("b"))
    notes: list[str] = []

    # additional description (e.g. "Blattsalat <span>Gärtnerinsalat</span>")
    nameSpan = title.find("span", class_="bg")
    if nameSpan:
        notes += [t for t in (_text(s) for s in nameSpan.find_all("span", recursive=False)) if t]

    # icons: vegan, vegetarisch, Schwein, Rind, Geflügel, MSC, ...
    for img in row.select(":scope > td.mtd-icon img[title]"):
        if img["title"] not in notes:
            notes.append(img["title"])

    sup = title.find("sup")
    if sup:
        notes += [n for n in _codeNotes(_text(sup).strip("[]")) if n not in notes]

    prices: dict[str, float] = {}
    for span in row.select(":scope > td span.bgp"):
        role = next((PRICE_ROLES[c] for c in span.get("class", []) if c in PRICE_ROLES), None)
        value = toPrice(span.get_text())
        if role and value is not None and role not in prices:
            prices[role] = value
    return name, notes, prices


def _parseLine(row: Tag) -> Category | None:
    lineName = _text(row.find("td", class_="mensatype"))
    data = row.find("td", class_="mensadata")
    if not lineName or data is None:
        return None

    meals: list[Meal] = []
    lineNotes: list[str] = []  # entries without price, e.g. "zu jedem Gericht reichen wir ..."
    for title in data.select("td.menu-title"):
        name, notes, prices = _parseMealRow(title)
        if not name:
            continue
        if prices:
            meals.append(Meal(name, notes, prices))
        else:
            lineNotes.append(name)

    for meal in meals:
        meal.notes = lineNotes + meal.notes
    return Category(lineName, meals)


def parseWeek(html: str) -> dict[str, list[Category]]:
    """Returns the categories for every day shown on the page, keyed by YYYY-MM-DD."""
    soup = BeautifulSoup(html, "lxml")
    days: dict[str, list[Category]] = {}
    for nav in soup.select("a[id^=canteen_day_nav_]"):
        n = nav["id"].removeprefix("canteen_day_nav_")
        dateStr = nav.get("rel")
        dateStr = dateStr[0] if isinstance(dateStr, list) else dateStr
        dayDiv = soup.find("div", id=f"canteen_day_{n}")
        if not dateStr or dayDiv is None:
            continue

        categories: dict[str, Category] = {}
        for row in dayDiv.select("tr.mensatype_rows"):
            cat = _parseLine(row)
            if cat is None or not cat.meals:
                continue
            if cat.name in categories:
                categories[cat.name].meals += cat.meals
            else:
                categories[cat.name] = cat
        days[dateStr] = list(categories.values())
    return days


def fetchWeek(canteen: str, week: int) -> dict[str, list[Category]]:
    return parseWeek(_fetch(f"{BASE_URL}{canteen}/?kw={week}"))


def getCanteen(canteen: str, start: date, numDays: int) -> tuple[Canteen, list[UpstreamUnavailable]]:
    """Fetches all weeks covering [start, start + numDays) and returns the canteen plus fetch errors."""
    end = start + timedelta(days=numDays)
    weeks = sorted({(start + timedelta(days=i)).isocalendar().week for i in range(numDays)})

    def load(week: int):
        try:
            return fetchWeek(canteen, week)
        except UpstreamUnavailable as err:
            return err

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(weeks)) as executor:
        results = list(executor.map(load, weeks))

    errors = [r for r in results if isinstance(r, UpstreamUnavailable)]
    days: dict[str, list[Category]] = {}
    for r in results:
        if isinstance(r, dict):
            days.update(r)

    canteenDays = []
    for dateStr in sorted(days):
        d = date.fromisoformat(dateStr)
        # `kw` has no year, so make sure we only report days that are actually in range
        if start <= d < end:
            canteenDays.append(CanteenDay(dateStr, days[dateStr], closed=not days[dateStr]))
    return Canteen(canteenDays), errors
