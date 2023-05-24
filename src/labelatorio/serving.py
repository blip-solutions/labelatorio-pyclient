
from typing import Dict, List, Union, Optional
from pydantic import BaseModel, root_validator
import requests
import logging
import aiohttp
import json

class PredictionRequestRecord(BaseModel):
    text:str
    key:Optional[str]
    contextData:Optional[Dict[str,str]]
    reviewProjectId:Optional[str] #where to send data for review... if not set, will be determined by model project

class Prediction(BaseModel):
    label:str
    score:float

class Answer(BaseModel):
    answer:str
    score:Optional[float]

class PredictedItem(BaseModel):
    predicted:Union[List[Prediction],List[Answer], None]
    handling:str
    key:Optional[str]=None
    explanations:Optional[List[Dict]]=None


class PredictResponse(BaseModel):
    predictions:Union[List[PredictedItem], List[Answer]]

class AnswerSource(BaseModel):
    id:Optional[str]=None
    text:str

class AnsweredQuestion(BaseModel):
    id:Optional[str]=None
    text:str
    answer:str

class AskQuestionRecord(BaseModel):
    key:Optional[str] = None
    question:str 
    potential_sources:Optional[List[Union[AnsweredQuestion,AnswerSource]]] =None
    history:Optional[List[AnsweredQuestion]] =None
    contextData:Optional[Dict[str,str]] =None
    reviewProjectId:Optional[str] =None #where to send data for review... if not set, will be determined by model project



class Answer(BaseModel):
    predicted:Union[List[Answer], None]
    answer_sources:Optional[List[Union[AnswerSource,AnsweredQuestion]]]=None
    handling:str
    key:Optional[str]=None
    explanations:Optional[List[Dict]]=None

    @root_validator(pre=True)
    def pre_validation(cls, values):
        if values.get("answer_sources"):
            answer_sources=[]
            for src in values.get("answer_sources"):
                if isinstance(src,str):
                    answer_sources.append(src)
                elif isinstance(src,dict):
                    if "answer" in src:
                        answer_sources.append(AnsweredQuestion(**src))
                    else:
                        answer_sources.append(AnswerSource(**src))
                else:
                    answer_sources.append(src)
            values["answer_sources"] = answer_sources
        return values



class NodeClient:
    def __init__(self, 
            access_token: str = None,
            url: str = None,
            tennant_id:str = None,
            node_name:str = None,
            timeout:int = 240
        ):

        if not url:
            if not node_name or not tennant_id :
                raise Exception("if url is not set, then tenant_id + node_name parameter must be set")
            else:
                url = f"https://api.labelator.io/nodes/{tennant_id}/{node_name}"
        

        if not requests.get(url, timeout=timeout).status_code==200:
            raise Exception(f"Unable to contact node at {url}")
        self.url=url.rstrip("/")
        self.headers={"access_token": access_token}
        self.timeout=timeout
    
    def predict(
            self,
            query:Union[str, PredictionRequestRecord, List[str], List[PredictionRequestRecord]] , 
            model=None,
            explain=False,
            test=False
        )->PredictResponse:
        if isinstance(query,str) or isinstance(query,PredictionRequestRecord):
            query=[query]
        
        query_url = f"{self.url }/predict" 
        response = requests.post(
                query_url,
                json={"texts":[req.dict() if isinstance(req,PredictionRequestRecord) else req  for req in query]}, 
                headers=self.headers,
                params={k:v for k,v in {"explain":explain, "text":test, "model_name":model}.items() if v},
                timeout= self.timeout,
            )

        if response.status_code==200:
            return PredictResponse(**response.json())
        else:
            raise Exception(f"Unexpected response: {response.status_code}: {response.reason}")
    
    


    async def apredict(
            self,
            query: Union[str, PredictionRequestRecord, List[str], List[PredictionRequestRecord]],
            model=None,
            explain=False,
            test=False
    ) -> PredictResponse:
        if isinstance(query, str) or isinstance(query, PredictionRequestRecord):
            query = [query]

        query_url = f"{self.url}/predict"
        params = {k: v for k, v in {"explain": explain, "text": test, "model_name": model}.items() if v}
        json_payload = {"texts": [req.dict() if isinstance(req, PredictionRequestRecord) else req for req in query]}

        async with aiohttp.ClientSession() as session:
            async with session.post(query_url, json=json_payload, headers=self.headers, params=params,
                                    timeout=self.timeout) as response:
                if response.status == 200:
                    response_text = await response.text()
                    data = json.loads(response_text)
                    return PredictResponse(**data)
                else:
                    raise Exception(f"Unexpected response: {response.status}: {response.reason}")

    def get_answers(
            self,
            query:Union[str, AskQuestionRecord, List[str], List[AskQuestionRecord]] , 
            top_k:int=None,
            model=None,
            explain=False,
            test=False,
            additional_instructions:Optional[str]=None
        )->Union[List[Answer],Answer]:

        return_first=False
        if not isinstance(query,list):
            query=[query]
            return_first=True
        if isinstance(query[0],PredictionRequestRecord):
            logging.warn("Using PredictionRequestRecord as a query for get_answer is obsolete. Please use AskQuestionRecord")
        
        payload = {"texts":[req.dict() if isinstance(req,BaseModel) else req  for req in query]}
        if additional_instructions:
            payload["additional_instructions"]=additional_instructions
        
        query_url =  f"{self.url }/get-answer"
        response = requests.post(
                query_url,
                json=payload, 
                headers=self.headers,
                params={k:v for k,v in {"explain":explain, "test":test,"top_k":top_k,  "model_name":model}.items() if v},
                timeout= self.timeout,
            )

        if response.status_code==200:
            predictions = response.json().get("predictions")
            result = [Answer(**ans_result)for ans_result in predictions]
            if return_first:
                return result[0]
            else:
                return result
        else:
            raise Exception(f"Unexpected response: {response.status_code}: {response.reason}", response.json() if response.headers.get("content-type")=="application/json" else None)

    def get_embeddings(
            self,
            texts:Union[str,List[str]], 
            model=None
        )->Union[List[float],List[List[float]]]:
        query_url = f"{self.url }/embeddings" 
        response = requests.post(
                query_url,
                json={"texts":texts}, 
                headers=self.headers,
                params={ "model_name":model} if model else None,
                timeout= self.timeout,
            )

        if response.status_code==200:
            return response.json().get("embeddings")
        else:
            raise Exception(f"Unexpected response: {response.status_code}: {response.reason}")

    def force_refresh(
            self
        )->None:
        
        response = requests.post(
                f"{self.url}/refresh",
                headers=self.headers,
                timeout= self.timeout,
            )

        if response.status_code==200:
            return
        else:
            raise Exception(f"Unexpected response: {response.status_code}: {response.reason}")