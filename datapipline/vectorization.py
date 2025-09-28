import xarray as xr
import json
from transformers import AutoTokenizer, AutoModel
import torch

from databseconnections import cdb


class BAAIBGEEmbeddings:
    def __init__(self, model_name="BAAI/bge-small-en"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of texts into vectors"""
        embeddings = []
        for text in texts:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                model_output = self.model(**inputs)
                # Mean pooling
                embedding = model_output.last_hidden_state.mean(dim=1).squeeze().tolist()
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query"""
        return self.embed_documents([text])[0]

    def embed_query(self, text):
        return self.embed_documents([text])[0]
    



metadata = {} 


def proccessnetcdf(pat: str):
    """Extracting NetCDF metadata and store in a single row"""
    global metadata
    obj = BAAIBGEEmbeddings()
    ds = xr.open_dataset(pat, engine="netcdf4")  

    variables_dict = {}
    for var_name in ds.variables:
        var = ds[var_name]
        variables_dict[var_name] = {
            "dimensions": var.dims,
            "shape": var.shape,
            "datatype": str(var.dtype),
            "coordinates": {coord: ds[coord].values.tolist() for coord in var.coords}
        }

    
    metadata = variables_dict.copy()
    metadata.update(ds.attrs) 

    
    serialized_metadata = json.dumps(metadata)

   
    embedding = obj.embed_documents({"full_metadata": serialized_metadata})

    
    collection = cdb.client.get_or_create_collection("netcdf_metadata")
    collection.add(
        ids=["full_metadata"],
        embeddings=[embedding["full_metadata"].tolist()],
        documents=[serialized_metadata]
    )

    print("Stored NetCDF metadata in a single row/document.")
    ds.close()
    return collection
