
from dataclasses import dataclass

from xml.etree import ElementTree as ET


@dataclass
class Meal:
    name: str
    note: str
    price: dict[str, float] # role -> price

    def toXml(self, root):
        mRoot = ET.SubElement(root, "meal")
        ET.SubElement(mRoot, "name", self.name)
        ET.SubElement(mRoot, "note", self.note)
        for role in self.price:
            ET.SubElement(mRoot, "price", self.price[role], attrib={"role": role})
        return mRoot


@dataclass
class Category:
    name: str
    meals: list[Meal]

    def toXml(self, root):
        cRoot = ET.SubElement(root, "category", attrib={"name": self.name})
        for m in self.meals:
            m.toXml(cRoot)
        return cRoot

@dataclass
class CanteenDay:
    date: str # YYYY-MM-DD
    categories: list[Category]

    def toXml(self, root):
        cRoot = ET.SubElement(root, "day", attrib={"date": self.date})
        for c in self.categories:
            c.toXml(c)
        return cRoot

@dataclass
class Canteen:
    days: list[CanteenDay]

    def toXml(self, root):
        cRoot = ET.SubElement(root, "canteen")
        for d in self.days:
            d.toXml(cRoot)
        return cRoot

def generateFeedV2(canteen: Canteen, parserVersion: str):
    root = ET.Element("openmensa", attrib={
        "version": "2.0",
        "xmlns": "http://openmensa.org/open-mensa-v2",
        "xmlns:xsi":"http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation":"http://openmensa.org/open-mensa-v2 http://openmensa.org/open-mensa-v2.xsd",
    })

    ET.SubElement(root, "version", parserVersion)
    canteen.toXml(root)

    return ET.tostring(root, encoding="unicode")
