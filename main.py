from models.structure import userquery
from typing import Union
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datapipline import vectorization, pos
from llminferance.chatwithagent import query_database
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import asyncio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        
    allow_credentials=True,
    allow_methods=["*"],         
    allow_headers=["*"],         
)


@app.post("/upload")
async def process_files(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
      
        file_path = f"uploads/{file.filename}"
        print(file_path)
        with open(file_path, "wb") as f:
            f.write(await file.read())

       
        vectorization.proccessnetcdf(file_path)
        print("vectorization done")
        df = pos.extract_ocean_data(file_path)
        print("df done")
        pos.insert_to_postgres(df)
        results.append({
            "filename": file.filename,
            "content_type": file.content_type
        })

    return {"files_received": results}


 
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    success: bool
    sql_query: str | None = None
    count: int = 0
    result: Dict[str, Any]
    error: str | None = None

@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    """
    Query oceanographic data using natural language
    
    Parameters:
    - query: Natural language query about oceanographic data
    
    Returns formatted visualization data based on query type:
    - T-S Diagram: temperature vs salinity
    - Salinity Profile: salinity vs depth  
    - Map View: trajectory/location data
    - Time Series: chlorophyll or other time-based data
    - Raw Data: tabular data for other queries
    """
    return query_database(request.query)