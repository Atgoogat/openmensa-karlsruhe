from fastapi import FastAPI
import app.swapi as swapi

app = FastAPI()

@app.get("/")
async def root():
    return swapi.getCanteenData()
