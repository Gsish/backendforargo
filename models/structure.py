from pydantic import BaseModel
from typing import List


class Netcdf(BaseModel):
    filename: List[str]
    typeoffile: str


class userquery(BaseModel):
     filename: List[str]
     query: str
     history:List[dict]


     


