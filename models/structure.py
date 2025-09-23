from pydantic import BaseModel
from typing import List




class userquery(BaseModel):
     filename: List[str]
     query: str
     history:List[dict]
     model: str


     


