
from models.structure import  Netcdf,userquery
from typing import Union
from fastapi import FastAPI
from pydantic import BaseModel
from datapipline import vectorization,pos
from llminferance.chatwithagent import runcode

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=True,
    allow_methods=["*"],         
    allow_headers=["*"],         
)


@app.post("/api/netpro")
async def get_hello(request :Netcdf):
    for i in request.filename:
        vectorization.proccessnetcdf(i)
        df = pos.extract_ocean_data(i)
        pos.insert_to_postgres(df)


    return {"files_received": request.filename, "type": request.typeoffile}


@app.post("/api/chat")
async def chatwllmm(request : userquery):
    res = runcode(request.query)
    return {"files_received": request.filename, "type": request.typeoffile}




