import urllib.request, json

from datetime import datetime
from app.feedv2.feed import Meal, Canteen, CanteenDay, Category
from bs4 import BeautifulSoup
import requests
import re


CONST_META_URL = "https://www.sw-ka.de/en/json_interface/general/"
CONST_CANTEEN_URL = "https://www.sw-ka.de/de/hochschulgastronomie/speiseplan/mensa_adenauerring/"

def getCanteenHtml():
    req = requests.get(CONST_CANTEEN_URL)
    return BeautifulSoup(req.text, "html.parser")


def getCanteen(soup: BeautifulSoup):
    return Canteen(toCanteenDays(soup))
    

def toCanteenDays(canteenDaySoup):
    days: list[CanteenDay] = []
    dates: list[str] = getMensaDateList(canteenDaySoup) # Contains only the dates as YYYY-MM-DD string

    dateIndex = 0

    for day in canteenDaySoup.find_all("div", {"class": "canteen-day"}):
        categories: list[Category] = []
        for lineData in day.find_all("tr", {"class": "mensatype_rows"}):
            categories.append(toCategory(lineData))
        days.append(CanteenDay(dates[dateIndex], categories))
    dateIndex += 1
    
    return days


def toCategory(lineSoup):
    lineName = lineSoup.find("td", {"class": "mensatype"}).text
    lineData = lineSoup.find("table", {"class": "meal-detail-table"})
    lineMeals: list[Meal] = []
    for meal in lineData.select('tr[class*="mt-"]'):
        lineMeals.append(getMealFromMenuSoup(meal))

    return Category(lineName, lineMeals)


def getMensaDateList(soup):
    dates: list[str] = []

    # Find all links in the canteen day navigation bar, because only they contain the date
    for dayNav in soup.find("ul", {"class": "canteen-day-nav"}).find_all("a"):
        # regex matches the setCanteenDate function in the onClick event which contains the date as argument
        date = re.match("setCanteenDate\('(.*)'\)", dayNav["onclick"]).group(1)
        dates.append(date)

    return dates


def getMealFromMenuSoup(soup):
    name = soup.find("td", {"class": "first menu-title"}).text
    price_students = soup.find("span", {"bgp price_1"}).text
    price_pupils = soup.find("span", {"bgp price_4"}).text
    price_employee = soup.find("span", {"bgp price_3"}).text
    price_others = soup.find("span", {"bgp price_2"}).text

    meal = Meal(name=name, note="", price={
                    "pupil": price_pupils,
                    "student": price_students,
                    "employee": price_employee,
                    "other": price_others,
                })
    return meal


def getMetaData():
    with urllib.request.urlopen(CONST_META_URL) as url:
        data = json.load(url)
        return data
