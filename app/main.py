from fastapi import FastAPI, Response
from fastapi.routing import APIRouter
import app.swapi as swapi
from app.feedv2.feed import generateFeedV2
from app.feedv2.meta import getOpenMensaMetaData

from os import environ


router = APIRouter()


@router.get("/")
async def root():
    return swapi.getCanteenData()

@router.get("/feed/{canteen}")
async def feed(canteen: str):
    canteenData = swapi.getCanteenData()
    if canteenData.get(canteen) is None:
        return Response(status_code=404)

    try:
        metaData = swapi.getMetaData()
        lines = metaData["mensa"][canteen]["lines"]
    except KeyError:
        lines = []
        
    c = swapi.toCanteen(canteen, canteenData, lines)
    return Response(content=generateFeedV2(c, "0.1-a"), media_type="application/xml")

@router.get("/meta/{canteen}")
async def meta(canteen: str):
    metaData = getOpenMensaMetaData(canteen)
    if metaData is None:
        return Response(status_code=404)
    return Response(content=metaData, media_type="application/xml")


app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
