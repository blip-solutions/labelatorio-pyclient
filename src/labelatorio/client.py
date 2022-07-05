from pydoc_data.topics import topics
import pandas
import requests
import labelatorio.data_model as data_model
import dataclasses
from typing import *
from labelatorio._helpers import batchify
import numpy as np
from tqdm import tqdm
import os
from zipfile import ZipFile

class Client:
    """
    A python native Labelator.io Client class that encapsulates access to your Labelator.io data.
   
    """

    def __init__(self, 
            api_token: str,
            url: str="https://api.labelator.io" 
        ):
        """
        Initialize a Client class instance.

        Parameters
        ----------
        api_token : str
            User id can be claimed allong access token on login screen
        url : str
            optional ... The URL to the Labelator.io instance
        """
        if url is None:
            url="labelator.io/api"
        elif not isinstance(url, str):
            raise TypeError("URL is expected to be string but is " + str(type(url)))
        elif url.endswith("/"):
            # remove trailing slash
            url = url[:-1]
        
        if url.lower().startswith("http") and not url.lower().startswith("http://localhost") :
            url = url.split("://")[1]
            self.url=f"https://{url}/"
        else:
            if not url.endswith("/"):
                url=url+"/"
            self.url=url
        self.headers={f"authorization":f"Basic {api_token}"}
        self.timeout=500 
        self._check_auth()
        self.projects=ProjectEndpointGroup(self)
        self.documents=DocumentsEndpointGroup(self)
        self.models=ModelsEndpointGroup(self)

    def _check_auth(self):
        login_status_response= requests.get(self.url+ "login/status", headers=self.headers, timeout=self.timeout)
        if login_status_response.status_code==200:
            payload=login_status_response.json()
            if "displayName" in payload and payload["displayName"]:
                user = payload["displayName"]
            elif  "email" in payload:
                user = payload["email"]
            else:
                raise Exception("Invalid login response")
        else:
            raise Exception(f"Login error: {login_status_response.status_code}")

        print(f"Logged in as: {user}")



T = TypeVar('T')

class EndpointGroup(Generic[T]):
    def __init__(self, client: Client) -> None:
        self.client=client

    def url_for_path(self, endpoint_path:str):
        return self.client.url+endpoint_path

    def get_entity_type(self):
        return next(base.__args__[0] for base in self.__class__.__orig_bases__ if len(base.__args__)==1)

    def _call_endpoint(self,method,endpoint_path,query_params=None,body=None, entityClass=T):
        request_url = self.url_for_path(endpoint_path)
        if entityClass==T:
            entityClass=self.get_entity_type()
        if method=="GET":
            response = requests.get(request_url, params=query_params,json=body, headers=self.client.headers, timeout=self.client.timeout)
        elif method=="POST":
            response =  requests.post(request_url, params=query_params,json=body, headers=self.client.headers, timeout=self.client.timeout)
        elif method=="PUT":
            response = requests.put(request_url, params=query_params,json=body, headers=self.client.headers, timeout=self.client.timeout)
        elif method=="DELETE":
            response = requests.delete(request_url, params=query_params,json=body,headers=self.client.headers, timeout=self.client.timeout)
        elif method=="PATCH":
            response = requests.patch(request_url, params=query_params,json=body,headers=self.client.headers, timeout=self.client.timeout)
        
        if response.status_code<300:
            if response.status_code==204:
                return None
            if entityClass==None:
                return
            if entityClass==dict:
                return response.json()
            elif dataclasses.is_dataclass(entityClass):
                data =response.json()
                if isinstance(data,List):
                    return [entityClass.from_dict(rec) for rec in data]
                else:
                    return entityClass.from_dict(data)
            else:
                return entityClass(response.content)
        else:
            raise Exception(f"Error response from server: {response.status_code}: {response.text}")


class ProjectEndpointGroup(EndpointGroup[data_model.Project]):
    def __init__(self, client: Client) -> None:
        super().__init__(client)    

    def get(self,project_id:str)  -> data_model.Project:
        """Get project by it's id

        Args:
            project_id (str): uuid of the project

        Returns:
            data_model.Project
        """
        return self._call_endpoint("GET", f"projects/{project_id}")

    def get_stats(self,project_id:str)  -> data_model.ProjectStatistics:
        """Get project statistics (label counts)

        Args:
            project_id (str): uuid of the project

        Returns:
            data_model.ProjectStatistics
        """
        res= self._call_endpoint("GET", f"projects/{project_id}/status",entityClass=dict)
        return data_model.ProjectStatistics.from_dict(res["stats"])

    
    def save(self, project: data_model.Project, regenerate:bool=False, merge_new_data:bool=False)  -> data_model.Project:
        """Get project statistics (label counts)

        Args:
            project_id (str): uuid of the project

        Returns:
            data_model.ProjectStatistics
        """
        payload = project.to_dict()
        if not payload["id"]:
            payload.pop("id")
        return self._call_endpoint("POST", f"projects", 
            body=payload,
            query_params={"download_and_process_data": regenerate,"merge_with_new_data": merge_new_data},
            entityClass= data_model.Project
            )

    def search(self,search_name:str)  -> List[data_model.ProjectInfo]:
        """Fuzzy seach by project name 
        note: if exact match exists, you can still get more results, but the exact match will be first

        Args:
            search_name (str): The search phrase

        Returns:
            List[data_model.Project]
        """
        return self._call_endpoint("GET", f"projects/search", query_params={"name":search_name}, entityClass=data_model.ProjectInfo)

    def get_by_name(self,name:str)  -> data_model.ProjectInfo:
        """Get project by name

        Args:
            name (str): The search phrase

        Returns:
            data_model.Project
        """
        return next((proj for proj in self.search(name) if proj.name==name),None)

        
class DocumentsEndpointGroup(EndpointGroup[data_model.TextDocument]):
    
    def __init__(self, client: Client) -> None:
        super().__init__(client)     

    def get(self,project_id:str, doc_id:str)  -> data_model.TextDocument:
        """Get single document by it's uuid

        Args:
            project_id (str): Uuid of project
            doc_id (str): document uuid (internaly generated)

        Returns:
            data_model.TextDocument
        """
        return self._call_endpoint("GET", f"projects/{project_id}/doc/{doc_id}")

    def count(self,
            project_id:str,
            topic_id:str=None, 
            keyword:str=None, 
            by_label:str = None,
            key:str = None,
            false_positives:str=None,
            false_negatives:str=None,
            predicted_label:str = None,
            prediction_certainty:Optional[float]=None
    )  -> int:
        """_summary_

        Args:
            project_id (str): Uuid of project
            topic_id (str, optional): topic_id filter
            keyword (str, optional): keyword filter
            by_label (str, optional):label filter
            key (str, optional): key filter (key is your own provided document identifier)
            false_positives (str, optional): filter to search label in false_positives predictions, additionaly "null" and "!null" special values are suported for finding document with or without false_positives
            false_negatives (str, optional): filter to search label in false_negatives predictions, additionaly "null" and "!null" special values are suported for finding document with or without false_negatives
            predicted_label (str, optional):  filter to search label predicted_labels 
            prediction_certainty (Optional[str], optional): minimal prediction_certainty

        Returns:
            int: the count
        """
        query_params={
            "topic_id":topic_id,
            "keyword":keyword,
            "by_label":by_label,
            "key":key,
            "false_positives":false_positives,
            "false_negatives":false_negatives,
            "predicted_label":predicted_label,
            "prediction_certainty":prediction_certainty,
        }   
        query_params={key:value for key,value in query_params if value}

        return self._call_endpoint("GET", f"projects/{project_id}/doc/count", query_params=query_params,entityClass=int)

    def search(self,
            project_id: str, 
            topic_id:str=None, 
            keyword:str=None, 
            similar_to_doc:any=None, 
            similar_to_phrase:str=None,
            min_score:Union[float,None] = None,
            by_label:str = None,
            key:str = None,
            false_positives:str=None,
            false_negatives:str=None,
            predicted_label:str = None,
            prediction_certainty:Optional[str]=None,
            skip:int = 0,
            take:int=50
    ) -> Union[List[data_model.TextDocument],List[data_model.ScoredDocumentResponse]]:
        """General function to get and search in TextoDocuments

        Args:
            project_id (str): Uuid of project
            project_id (str): Uuid of project
            topic_id (str, optional): topic_id filter
            keyword (str, optional): keyword filter
            similar_to_doc (any, optional): Id of document to search similar docs to
            similar_to_phrase (str, optional): custom phrase to search similar docs to
            min_score (Union[float,None], optional): Miminal similarity score to cap the results
            by_label (str, optional): label filter
            key (str, optional): key filter (key is your own provided document identifier)
            false_positives (str, optional): filter to search label in false_positives predictions, additionaly "null" and "!null" special values are suported for finding document with or without false_positives
            false_negatives (str, optional): filter to search label in false_negatives predictions, additionaly "null" and "!null" special values are suported for finding document with or without false_negatives
            predicted_label (str, optional):  filter to search label predicted_labels 
            prediction_certainty (Optional[str], optional): minimal prediction_certainty
            skip (int, optional): Pagination - number of docs to skip. Defaults to 0.
            take (int, optional): Pagination - number of docs to take. Defaults to 50.

        Returns:
            List[data_model.TextDocument]               - for regular search (if similar_to_doc NOR similar_to_phrase is requested)
            List[data_model.ScoredDocumentResponse]     - for similarity search (if similar_to_doc OR similar_to_phrase is requested)
        """

        responseData = self._call_endpoint("GET", f"/projects/{project_id}/doc/search", query_params={
            "topic_id":topic_id,
            "keyword":keyword,
            "similar_to_doc":similar_to_doc,
            "similar_to_phrase":similar_to_phrase,
            "min_score":min_score,
            "by_label":by_label,
            "key":key,
            "false_positives":false_positives,
            "false_negatives":false_negatives,
            "predicted_label":predicted_label,
            "prediction_certainty":prediction_certainty,
            "skip":skip,
            "take":take,
            }, entityClass=dict)

        if similar_to_doc or similar_to_phrase:
            return [data_model.ScoredDocumentResponse.from_dict(item) for item in responseData  ]
        else:
            return [data_model.TextDocument.from_dict(item) for item in responseData  ]

    def get_neighbours(self,project_id:str, doc_id:str, min_score:float=0.7, take:int=50) -> List[data_model.TextDocument]:
        """Get documents similar to document

        Args:
            project_id (str): Uuid of project
            doc_id (str): Reference document for finding neighbours to
            min_score (Union[float,None], optional): Miminal similarity score to cap the results
            take (int): max result count

        Returns:
            List[data_model.TextDocument]
        """
        return self.search(project_id=project_id, similar_to_doc=doc_id, min_score=min_score,take=take)

    def _preprocess_text_data(item:dict)->dict:
        contextData = item.pop(data_model.TextDocument.COL_CONTEXT_DATA)
        if contextData:
            for field in contextData:
                item[field] = contextData[field]
        return item

    def set_labels(self, project_id:str, doc_ids:List[str], labels:List[str])-> None:
        """Set labels to document (annotate)

        Args:
            project_id (str): Uuid of project
            doc_ids (List[str]): list of document ids to set the defined labels
            labels (List[str]): defined labels to set on documents (overrides existing labels)
        """
        self._call_endpoint("PATCH", f"projects/{project_id}/doc/labels", entityClass=None, body={
            "doc_ids":doc_ids,
            "labels":labels
        })

    def get_vectors(self, project_id, doc_ids:List[str])-> List[Dict[str,np.ndarray]]:
        """get embeddings of documents in project

        Args:
            project_id (_type_): project_id
            doc_ids (List[str]): list of ids to retrieva data for

        Returns:
            list of dictionaries like this: {"id":"uuid", "vector":[0.0, 0.1 ...]}
        """
        result=[]
        for ids_batch in tqdm(batchify(doc_ids,100), total=int(len(doc_ids)/100), desc="Get vectors", unit="batch",  delay=2):
            for result_item in self._call_endpoint("PUT", f"/projects/{project_id}/doc/export-vectors", body=ids_batch, entityClass=dict):
                result.append({"id":result_item["id"], "vector":np.array(result_item["vector"])})
        return result


    def add_documents(self, project_id:str, data:pandas.DataFrame, upsert=False, batch_size=100 )->Union[List[str], None]:
        """Add documents to project

        Args:
            project_id (str): project id (uuid)
            data (pandas.DataFrame): dataframe with data... must have key + text column
            schedule (bool, optional): Whether to schedule execution on labelatorio (async execution). Defaults to False. It's obligatory to shedule execution for more than 100 records
            skip_if_exists (bool, optional): whether to check for duplicated by column [key] and skipp adding these records. Defaults to False.

        Raises:
            Exception: Columun [key/text] must be present in data

        Returns:
            List[str]: list of ids if [schedule] = False
            None: if [schedule] = True
        """
        if "key" not in data.columns:
            data=data.copy()
            data["key"] =data.index
        if "text" not in data.columns:
            raise Exception("column named 'text' must be present in data")


        data.to_dict(orient="records")
        documents = data.to_dict(orient="records")
        def send(data):
            return self._call_endpoint("POST", f"/projects/{project_id}/doc", query_params={"upsert":upsert},entityClass=dict,body=data)


        ids = []
        for batch in tqdm(batchify(documents,batch_size), total=(int(len(documents)/batch_size)),desc="Add documents",unit="batch", delay=2):
            for item in send(batch):
                ids.append(item)
        return ids

    def exclude(self, project_id:str, doc_ids:List[str])-> None: 
        """Exclude document 
        (undoable action... document is still present in project, but filtered out from common requests)

        Args:
            project_id (str): Uuid of project
            doc_id (str): id of document to delete
        """
        self._call_endpoint("PUT", f"/projects/{project_id}/doc/excluded",body=doc_ids, entityClass=None)

    def delete(self, project_id:str, doc_id:str)-> None: 
        """Delete document! 

        Args:
            project_id (str): Uuid of project
            doc_id (str): id of document to delete
        """
        self._call_endpoint("DELETE", f"/projects/{project_id}/doc/{doc_id}", entityClass=None)


    def delete_all(self, project_id:str)-> None:
        """Bulk delete of all documents in project!

        Args:
            project_id (str): Uuid of project
        """
        self._call_endpoint("DELETE", f"/projects/{project_id}/doc/all", entityClass=None)

    def export_to_dataframe(self, project_id:str)->pandas.DataFrame:
        """Export all documents into pandas dataframe

        Args:
            project_id (str): Uuid of project

        Returns:
           DataFrame
        """
        
        #TODO: !!! toto treba nahradiť sa sortovanie a incrementaciu kym su data!
        total_count = self.count(project_id)

        all_documnents=[]
        page_size = 100
        for i in tqdm(range(0,total_count,page_size), desc="Export to dataframe", unit="batch",  delay=2):
            after = i
            #before = i+page_size
            
            queried_docs = self._call_endpoint("GET", f"/projects/{project_id}/doc/search", query_params={
                "after":after,
                "before":after+page_size,
            }, entityClass=dict)

            for doc in  queried_docs:
                all_documnents.append(DocumentsEndpointGroup._preprocess_text_data(doc))
            

        return pandas.DataFrame(all_documnents).set_index("_i", verify_integrity=True)
        
class ModelsEndpointGroup(EndpointGroup[data_model.ModelInfo]):
    def __init__(self, client: Client) -> None:
        super().__init__(client)     

   

    def get_info(self,project_id:str, model_id:str)  -> data_model.ModelInfo:
        """Get model details

        Args:
            project_id (str): Uuid of project
            model_id (str): Uuid of the model

        Returns:
            data_model.ModelInfo: _description_
        """
        return self._call_endpoint("GET", f"projects/{project_id}/models/{model_id}")

    def delete(self, project_id:str,model_id:str)-> None: 
        """Delete model

        Args:
            project_id (str): Uuid of project
            model_id (str): Uuid of the model

        """
        return self._call_endpoint("DELETE", f"projects/{project_id}/models/{model_id}")

    def get_all(self,project_id:str)-> List[data_model.ModelInfo]:
        """Get all models for project

        Args:
            project_id (str): Uuid of project

        Returns:
            data_model.ModelInfo: _description_
        """
        return self._call_endpoint("GET", f"projects/{project_id}/models")

    def download(self,project_id:str, model_id:str, target_path:str=None, unzip=True )->str:
        """Download model files

        Args:
            project_id (str): Uuid of project
            model_id (str): Model Uuid
            target_path (str): target directory where to save files
            unzip (bool, optional): Model is zipped after download...  whether to unzip the model, to be able to load it. Defaults to True.

        Returns:
            Path to zipped model or folder with model files
        """
        if not target_path:
            target_path=os.getcwd()
        auth_params = self._call_endpoint("GET", 
            f"/login/getAuthUrlParams",
            query_params={
                            "project_id":project_id,
                            "parameter":model_id},
            entityClass=dict)
        auth_params["file_na,e"]=model_id+".zip"

        request_url = self.url_for_path(f"/projects/{project_id}/models/{model_id}/download")
        response = requests.get(request_url, stream=True,  params=auth_params)
        zip_filename=os.path.join(target_path,model_id+".zip")
        with open(zip_filename, "wb") as handle:
            for data in tqdm(response.iter_content(chunk_size=1024),unit="MB"):
                handle.write(data)
        
        if unzip:
            result_folder = os.path.join(target_path,model_id)
            with ZipFile(zip_filename, 'r') as zip_ref:
                zip_ref.extractall(result_folder)
            os.remove(zip_filename)
            return result_folder
        else:
            return zip_filename


                
    def apply_predictions(self, project_id:str,model_id:str)-> None: 
        """Apply predictions from model
        Args:
            project_id (str): Uuid of project
            model_id (str): Model Uuid
        """
        self._call_endpoint("PUT", f"/projects/{project_id}/models/{model_id}/apply-predict", entityClass=None)

    def apply_embeddings(self, project_id:str,model_id:str)-> None: 
        """Regenerate embeddings and reindex by new model

        Args:
            project_id (str): Uuid of project
             model_id (str): Model Uuid
        """
        self._call_endpoint("PUT", f"/projects/{project_id}/models/{model_id}/apply-embeddings", entityClass=None)



    def train(self, project_id:str, model_training_request:data_model.ModelTrainingRequest)-> None: 
        """Start training task

        Args:
            project_id (str): Uuid of project
            model_training_request (data_model.ModelTrainingRequest): Training settings
        """
        self._call_endpoint("PUT", f"/projects/{project_id}/models/train", body=model_training_request.to_dict(), entityClass=None)