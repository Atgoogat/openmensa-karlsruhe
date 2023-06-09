from typing import Any
import urllib.request, json
from dataclasses import dataclass
import re

from datetime import datetime
from app.feedv2.feed import Meal, Canteen, CanteenDay, Category

MENSA_URL = "https://mensa.akk.org/json/"

@dataclass
class AkkMensaDay:
    day: str 
    mensa: str
    closed: bool 
    data: Any

def loadExampleData() -> AkkMensaDay:
    with open('./example-data/2023-06-05.json') as f:
        data = json.load(f)
        date = data["date"]
        canteens = data["canteens"]
        for c in canteens:
            if c[0] == "Mensa am Adenauerring":
                return AkkMensaDay(date, "Mensa am Adenauerring", c[1])
        raise Exception("mensa adenauerring not present in dataset")
    
def getMensaAdenauerringMeals(date: datetime) -> AkkMensaDay:
    date_str = date.strftime("%Y-%m-%d")
    try:
        url = urllib.request.urlopen(MENSA_URL + date_str + ".json") 
        data = json.load(url)
        date = data["date"]
        canteens = data["canteens"]
        for c in canteens:
            if c[0] == "Mensa am Adenauerring":
                return AkkMensaDay(date, "Mensa am Adenauerring", False, c[1])
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return AkkMensaDay(date_str, "Mensa am Adenauerring", True, None)
        raise err

def toPrice(price: str) -> float:
    price = price.replace(",", ".")
    price = price.replace("€", "")
    if price.startswith("(ab)"):
        return float(price[5:])
    return float(price)

def toMeals(meals: Any) -> list[Meal]:
    m: list[Meal] = []

    notes = filter(lambda meal: "price" not in meal or meal["price"] == "", meals)
    meals = filter(lambda meal: "price" in meal and meal["price"] != "", meals)

    note = '\n'.join([n["name"] for n in notes])

    for meal in meals:
        m.append(Meal(meal["name"], note, {
            "student": toPrice(meal["price"]),
        }))

    return m

def toCategories(lines: Any) -> list[Category]:
    categories: list[Category] = []
    for line in lines:
        # Akk Api has some typos by default, that includes no whitespace after "Linie x" and no whitespace between some lines and their opening times.
        # (?=[^\s])) is a lookahead ensuring that the regex matches only if no whitespace follows.
        lineName = re.sub(r'(Linie \d(?=[^\s]))', r'\1 ', line[0]) # Whitespaces after "Linie x" were missing
        lineName = re.sub(r'(werk(?=[^\s]))', r'\1 ', lineName) # Whitespaces after "werk" were missing
        lineName = re.sub(r'(?<=[^\s])(\d{2}-\d{2} Uhr)', r' \1', lineName) # Whitespaces before opening times were missing
        categories.append(Category(lineName, toMeals(line[1]["dishes"])))
    return categories

def toCanteenDay(akkMensaDay: AkkMensaDay) -> CanteenDay:
    if akkMensaDay.closed:
        return CanteenDay(akkMensaDay.day, [], True)
    return CanteenDay(akkMensaDay.day, toCategories(akkMensaDay.data), False)

def toCanteen(akkMensaDays: list[AkkMensaDay]) -> Canteen:
    days = [toCanteenDay(day) for day in akkMensaDays]
    return Canteen(days)
