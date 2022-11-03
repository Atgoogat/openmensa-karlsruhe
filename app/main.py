from fastapi import FastAPI, Response
from fastapi.routing import APIRouter
import app.swapi as swapi
from app.feedv2.feed import generateFeedV2

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
        
    c = swapi.toCanteen(canteen, canteenData)
    return Response(content=generateFeedV2(c, "0.1-a"), media_type="application/xml")

app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
