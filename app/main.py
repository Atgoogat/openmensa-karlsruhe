from fastapi import FastAPI
from fastapi.routing import APIRouter
import app.swapi as swapi

from os import environ


router = APIRouter()


@router.get("/")
async def root():
    return swapi.getCanteenData()

app = FastAPI()
app.include_router(router, prefix=environ.get('OMKA_ROOT_PATH') or "")
