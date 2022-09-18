
from time import time
from typing import Dict, List, Union, Optional
from pydantic import BaseModel
import requests

class PredictionRequestRecord(BaseModel):
    key:str
    text:str
    contextData:Optional[Dict[str,str]]

class Prediction(BaseModel):
    label:str
    score:float


class PredictedItem(BaseModel):
    predicted:Union[List[Prediction], None]
    handling:str
    key:Optional[str]=None
    explanations:Optional[List[Dict]]=None


class PredictctRespone(BaseModel):
    predictions:List[PredictedItem]


class NodeClient:
    def __init__(self, 
            access_token: str = None,
            url: str = None,
            tennant_id:str = None,
            node_name:str = None,
            timeout:int = 60
        ):

        if not url:
            if not node_name or not tennant_id :
                raise Exception("if url is not set, then tennant_id + node_name parameter must be set")
            else:
                url = f"https://api.labelator.io/nodes/{tennant_id}/{node_name}"
        

        if not requests.get(url).status_code==200:
            raise Exception(f"Unable to conntact node at {url}")
        self.url=url.rstrip("/")
        self.headers={"access_token": access_token}
        self.timeout=timeout
    
    def predict(
            self,
            query:Union[str, PredictionRequestRecord, List[str], List[PredictionRequestRecord]] , 
            model=None,
            explain=False,
            test=False
        ):
        if isinstance(query,str) or isinstance(query,PredictionRequestRecord):
            query=[query]
        
        query_url =  (f"{self.url }/predict" if not model else f"{self.url}/predict/{model}")
        response = requests.post(
                query_url,
                json={"texts":[req.dict() for req in query]}, 
                headers=self.headers,
                params={"explain":explain, "text":test},
                timeout= self.timeout,
            )

        if response.status_code==200:
            return PredictctRespone(**response.json())
        else:
            raise Exception(f"Unexpected response: {response.status_code}: {response.reason}")
