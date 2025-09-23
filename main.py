from models.structure import  Netcdf,userquery
from typing import Union
from fastapi import FastAPI,File, UploadFile
from pydantic import BaseModel
from datapipline import vectorization,pos
from llminferance.chatwithagent import runcode
from typing import List
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
async def process_files(files: List[UploadFile] = File(...)):
    results = []

    for file in files:
      
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            f.write(await file.read())

       
        vectorization.proccessnetcdf(file_path)
        df = pos.extract_ocean_data(file_path)
        pos.insert_to_postgres(df)

        results.append({
            "filename": file.filename,
            "content_type": file.content_type
        })

    return {"files_received": results}


@app.post("/api/chat")
async def chatwllmm(request : userquery):
    res = runcode(request.query)
    return {"files_received": request.filename, "type": request.typeoffile}




