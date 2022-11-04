import urllib.request, json

from datetime import datetime
from app.feedv2.feed import Meal, Canteen, CanteenDay, Category


CONST_META_URL = "https://www.sw-ka.de/en/json_interface/general/"
CONST_CANTEEN_URL = "https://www.sw-ka.de/en/json_interface/canteen/"


def getCanteenData():
    with urllib.request.urlopen(CONST_CANTEEN_URL) as url:
        data = json.load(url)
        return data

def getMetaData():
    with urllib.request.urlopen(CONST_META_URL) as url:
        data = json.load(url)
        return data

def toMeals(mealData):
    meals: list[Meal] = []

    note = ""
    for m in mealData:
        if m["price_1"] == 0: # zusatz 
            note = m["meal"]
        else:
            meal: str = m["meal"] + " " + m["dish"]
            meals.append(
                Meal(meal.strip(), "", {
                    "pupil": m["price_4"],
                    "student": m["price_1"],
                    "employee": m["price_3"],
                    "other": m["price_2"],
                })
            )

    for m in meals:
        m.note = note

    return meals

def toCategory(categoryData, linesData):
    categories: list[Category] = []

    for cKey in categoryData: 
        c = categoryData[cKey]
        if c[0].get("nodata") is not None:
            continue        # closed

        categories.append(Category(linesData.get(cKey, cKey), toMeals(c)))

    return categories

def toCanteenDay(dayData, linesData):
    days: list[CanteenDay] = []

    for dKey in dayData:
        categories = toCategory(dayData[dKey], linesData)
        days.append(CanteenDay(datetime.fromtimestamp(float(dKey)).strftime("%Y-%m-%d"), categories, len(categories) == 0))

    return days

def toCanteen(canteen: str, apiData, linesData: dict[str, str]):
    return Canteen(
        toCanteenDay(apiData[canteen], linesData)
    )