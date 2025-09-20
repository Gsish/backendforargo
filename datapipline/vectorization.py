import xarray as xr
import json
from transformers import AutoTokenizer, AutoModel
import torch

from databseconnections import cdb

class BAAIBGEEmbeddings:
    def __init__(self, model_name="BAAI/bge-small-en"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)

    def embed_documents(self, texts: dict):
        """
        texts: dict where key -> document ID, value -> document text
        returns: dict of embeddings with same keys
        """
        embeddings = {}

        for key, value in texts.items():
            inputs = self.tokenizer(value, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use mean pooling of last hidden state as embedding
                emb = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                embeddings[key] = emb

        return embeddings

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

    # Merge dataset attributes
    metadata = variables_dict.copy()
    metadata.update(ds.attrs) 

    # Serialize entire metadata as one JSON string
    serialized_metadata = json.dumps(metadata)

    # Create one embedding for the full metadata
    embedding = obj.embed_documents({"full_metadata": serialized_metadata})

    # Store in a single row/collection
    collection = cdb.client.get_or_create_collection("netcdf_metadata")
    collection.add(
        ids=["full_metadata"],
        embeddings=[embedding["full_metadata"].tolist()],
        documents=[serialized_metadata]
    )

    print("Stored NetCDF metadata in a single row/document.")
    ds.close()
    return collection
