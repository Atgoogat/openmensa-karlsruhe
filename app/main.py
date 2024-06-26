from fastapi import FastAPI, Response
from fastapi.routing import APIRouter

import app.mensaakkapi as mensaakkapi 
from app.feedv2.feed import generateFeedV2
from app.feedv2.meta import getOpenMensaMetaData

from os import environ
from datetime import datetime, timedelta

import concurrent.futures

router = APIRouter()

@router.get("/feed/adenauerring")
async def feedAdenauerring():
    mensaDays = []
    date = datetime.today()
    # fetch next 14 days
    dates = [date + timedelta(days=i) for i in range(14)]

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=14)
    days = executor.map(mensaakkapi.getMensaAdenauerringMeals, dates)
    for day in days:
        mensaDays.append(day)

    canteenData = mensaakkapi.toCanteen(mensaDays)
    return Response(content=generateFeedV2(canteenData, "0.1-a"), media_type="application/xml")

@router.get("/feed/adenauerring/{date}")
async def feedAdenauerring(date: str):
    data = mensaakkapi.getMensaAdenauerringMeals(datetime.strptime(date, "%Y-%m-%d"))
    canteenData = mensaakkapi.toCanteen([data])
    return Response(content=generateFeedV2(canteenData, "0.1-a"), media_type="application/xml")

@router.get("/meta/adenauerring")
async def meta():
    metaData = getOpenMensaMetaData("adenauerring")
    if metaData is None:
        return Response(status_code=404)
    return Response(content=metaData, media_type="application/xml")


app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
