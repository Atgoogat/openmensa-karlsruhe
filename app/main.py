from bs4 import BeautifulSoup
from fastapi import FastAPI, Response
from fastapi.routing import APIRouter
import app.swapi as swapi
from app.feedv2.feed import Canteen, generateFeedV2
from app.feedv2.meta import getOpenMensaMetaData

from os import environ


router = APIRouter()


@router.get("/")
async def root():
    canteenSoup = swapi.getCanteenHtml()
    if canteenSoup is None:
        return Response(status_code=404)

    return swapi.getCanteen(canteenSoup)
    return generateFeedV2(swapi.getCanteen(canteenSoup), "0.1-a")
    

@router.get("/feed/{canteen}")
async def feed(canteen: str):
    canteen: Canteen
    canteenSoup = swapi.getCanteenHtml()
    if canteenSoup is None:
        return Response(status_code=404)

    canteen = swapi.getCanteen(canteenSoup)

    return Response(content=generateFeedV2(canteen, "0.1-a"), media_type="application/xml")

@router.get("/meta/{canteen}")
async def meta(canteen: str):
    metaData = getOpenMensaMetaData(canteen)
    if metaData is None:
        return Response(status_code=404)
    return Response(content=metaData, media_type="application/xml")


app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
