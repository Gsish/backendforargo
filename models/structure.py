from pydantic import BaseModel
from typing import List


class Netcdf(BaseModel):
    filename: List[str]
    typeoffile: str

