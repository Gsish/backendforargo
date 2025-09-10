
from models.structure import  Netcdf
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=True,
    allow_methods=["*"],         
    allow_headers=["*"],         
)


@app.post("/hello")
async def get_hello(net :Netcdf):
    return {"message": net.filename}


