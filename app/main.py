from fastapi import FastAPI, Response
from fastapi.routing import APIRouter

from app import swka
from app.swka import UpstreamUnavailable
from app.feedv2.feed import Canteen, generateFeedV2
from app.feedv2.meta import getOpenMensaMetaData

from os import environ
from datetime import date

import logging

logger = logging.getLogger("uvicorn.error")

router = APIRouter()

CANTEEN = "mensa_adenauerring"
FEED_DAYS = 14
PARSER_VERSION = "0.2"


def _feedResponse(canteen: Canteen) -> Response:
    return Response(content=generateFeedV2(canteen, PARSER_VERSION), media_type="application/xml")


def _upstreamError() -> Response:
    # 503 lets OpenMensa retry later (see retry in meta) and keeps the existing data
    # instead of overwriting it with an empty/closed feed.
    return Response(content="sw-ka.de is currently unavailable", status_code=503,
                    headers={"Retry-After": "1800"}, media_type="text/plain")


# Endpoints are plain `def` so FastAPI runs them in a threadpool and the blocking
# HTTP calls do not stall the event loop.
@router.get("/feed/adenauerring")
def feedAdenauerring():
    canteen, errors = swka.getCanteen(CANTEEN, date.today(), FEED_DAYS)
    if errors:
        logger.warning("%d week(s) could not be fetched: %s", len(errors), errors[0])
    if errors and not canteen.days:
        return _upstreamError()
    # Weeks that failed are left out of the feed (not marked closed), so OpenMensa keeps their old data.
    return _feedResponse(canteen)


@router.get("/feed/adenauerring/{day}")
def feedAdenauerringDay(day: str):
    try:
        parsed = date.fromisoformat(day)
    except ValueError:
        return Response(content="invalid date, expected YYYY-MM-DD", status_code=400, media_type="text/plain")
    canteen, errors = swka.getCanteen(CANTEEN, parsed, 1)
    if errors:
        logger.warning("could not fetch %s: %s", day, errors[0])
        return _upstreamError()
    return _feedResponse(canteen)


@router.get("/meta/adenauerring")
def meta():
    metaData = getOpenMensaMetaData("adenauerring")
    if metaData is None:
        return Response(status_code=404)
    return Response(content=metaData, media_type="application/xml")


app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
