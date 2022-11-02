import urllib.request, json

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
