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
import labelatorio.enums as enums
from labelatorio.query_model import DocumentQueryFilter, Or
import time


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
        
        if url.lower().startswith("http:") and "." in url:
            print("Force to use https for any url that is has a domain")
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
        self.similarity_links=SimilarityLinkEndpointGroup(self)
        self.models=ModelsEndpointGroup(self)
        self.tasks=TaskEndpointGroup(self)
        self.serving_nodes=ServingNodesEndpointGroup(self)
        self.topics=TopicsEndpointGroup(self)

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
        from labelatorio import __version__
        print(f"Labelator.io client version {__version__}")
        print(f" logged in as: {user}")
        print(f" tennant_id: {payload.get('tennant_id')}")



T = TypeVar('T')

class EndpointGroup(Generic[T]):
    def __init__(self, client: Client) -> None:
        self.client=client

    def _url_for_path(self, endpoint_path:str):
        return self.client.url+endpoint_path

    def _get_entity_type(self):
        return next(base.__args__[0] for base in self.__class__.__orig_bases__ if len(base.__args__)==1)

    def _call_endpoint(self,method,endpoint_path,query_params=None,body=None, entityClass=T, ignore_err_status_codes=None):
        request_url = self._url_for_path(endpoint_path)

        if dataclasses.is_dataclass(body):
            body=body.to_dict()

        if entityClass==T:
            entityClass=self._get_entity_type()
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
            if response.status_code==ignore_err_status_codes \
                or isinstance(ignore_err_status_codes,list) and (response.status_code in ignore_err_status_codes):
                return None
            raise Exception(f"Error response from server: {response.status_code}: {response.text}")


class ProjectEndpointGroup(EndpointGroup[data_model.Project]):
    def __init__(self, client: Client) -> None:
        super().__init__(client)    

    def new(self,name:str, task_type:str)  -> data_model.Project:
        newProject = data_model.Project.new(name, task_type)
        return self.save(newProject)

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
        """Fuzzy search by project name 
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
            false_positives (str, optional): filter to search label in false_positives predictions, additionally "null" and "!null" special values are supported for finding document with or without false_positives
            false_negatives (str, optional): filter to search label in false_negatives predictions, additionally "null" and "!null" special values are supported for finding document with or without false_negatives
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
        query_params={key:value for key,value in query_params.items() if value}

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
        """General function to get and search in TextDocuments

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
            false_positives (str, optional): filter to search label in false_positives predictions, additionally "null" and "!null" special values are supported for finding document with or without false_positives
            false_negatives (str, optional): filter to search label in false_negatives predictions, additionally "null" and "!null" special values are supported for finding document with or without false_negatives
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

    def query(self,
            project_id: str, 
            query:Union[DocumentQueryFilter,Or, Dict],
            order_by:str = None,
            skip:int = 0,
            take:int=50
    ) -> Union[List[data_model.TextDocument],List[data_model.ScoredDocumentResponse]]:
        """_summary_

        Args:
            project_id (str): Uuid of project
            query (Union[DocumentQueryFilter,Or,Dict]): Where query to match the documents
            order_by (str, optional): Sort by field. Defaults to None.
            skip (int, optional): paging - skip. Defaults to 0.
            take (int, optional): paging - take. Defaults to 50.

        Returns:
            Union[List[data_model.TextDocument],List[data_model.ScoredDocumentResponse]]: _description_
        """
        responseData = self._call_endpoint("POST", f"/projects/{project_id}/doc/query", body=query, query_params={"order_by":order_by, "skip":skip, "take":take},entityClass=dict)
        
        return [data_model.ScoredDocumentResponse.from_dict(item) if "score" in item else data_model.TextDocument.from_dict(item) for item in responseData  ]
            
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


    def add_documents(self, project_id:str, data:Union[pandas.DataFrame,List[dict]], upsert:bool=True, batch_size:int=100 )->List[dict]:
        """Add documents to project

        Args:
            project_id (str): project id (uuid)
            data (pandas.DataFrame): dataframe with data... must have key + text column
            upsert (bool): if false, duplicates with same key will be allowed,note that records inserted with upsert=False will have id's will not be possible upsert by key anymore
        Raises:
            Exception: Columun [text] must be present in data

        Returns:
            List[str]: list of ids 
        """
        if isinstance(data, pandas.DataFrame):
            if "text" not in data.columns:
                raise Exception("column named 'text' must be present in data")
            
            documents = data.replace({np.nan:None}).to_dict(orient="records")
        else:
            for rec in data:
                if "text" not in rec:
                    raise Exception("column named 'text' must be present in data")
            documents=data
        
        def send(data):
            return self._call_endpoint("POST", f"/projects/{project_id}/doc", query_params={"upsert":upsert},entityClass=dict,body=data)


        response_data = []
        for batch in tqdm(batchify(documents,batch_size), total=(int(len(documents)/batch_size)),desc="Add documents",unit="batch", delay=2):
            for item in send(batch):
                response_data.append(item)
        return response_data

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

    
    def delete_by_query(self, project_id:str, query:Union[DocumentQueryFilter,Or], wait_for_completion=False)-> None: 
        """_Delete documents by provided query

        Args:
            project_id (str): Uuid of project
            query (Union[DocumentQueryFilter,Or]): query filter to match the documents to be deleted
            wait_for_completion (bool, optional): Triggers synchronous exectuion. Limits the number of records to be deleted to 10 000 (but can be run in loop until no data remains). Defaults to False.

        Returns:
            None
        """

        self._call_endpoint("DELETE", f"/projects/{project_id}/doc/", body=query, query_params={"wait_for_completion":wait_for_completion}, entityClass=None)


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
        
        total_count = self.count(project_id)

        all_documnents=[]
        page_size = 1000
        for i in tqdm(range(0,total_count,page_size), desc="Export to dataframe", unit="batch",  delay=2):
            after = i
            #before = i+page_size
            
            queried_docs = self._call_endpoint("GET", f"/projects/{project_id}/doc/search", query_params={
                "after":after-1,
                "before":after+page_size,
                "take":page_size
            }, entityClass=dict)

            for doc in  queried_docs:
                all_documnents.append(DocumentsEndpointGroup._preprocess_text_data(doc))
            

        return pandas.DataFrame(all_documnents).set_index("_i", verify_integrity=True)
        

class SimilarityLinkEndpointGroup(EndpointGroup[Tuple[dict,dict]]):
    def query(self,
            project_id: str, 
            link_type:str,
            select:Optional[List[str]]=None,
            query:Union[DocumentQueryFilter,Or,None]=None,
            fetch_all=True,
            skip:int = 0,
            take:int = 50
    ) -> List[Tuple[dict,dict]]:
        """query the similarity links
        
        Note: Be aware that links are both sided so eventually each link is effectively returned twice, with swapped items in the resulting tuple

        Args:
            project_id (str): Uuid of project
            link_type (str): positive|negative
            select (str): list of fields to select
            query (Union[DocumentQueryFilter,Or,None], optional): query over the left side (source of the link)
            fetch_all (bool): whether to fetch all links matching the query_filter if defined. Defaults to true
            skip (int, optional): paging - items to skip (ignored if fetch_all=True ). Defaults to 0.
            take (int, optional): paging - items to take (ignored if fetch_all=True ). Defaults to 50.

        Returns:
            Union[List[Tuple[dict,dict]],Iterator[Tuple[dict,dict]]]: return list or itterator (if fetch_all=False) of tuples of two items (left, right side of the link)
        """

        def fetch_data():
            responseData = self._call_endpoint("POST", f"/projects/{project_id}/doc/similar/links/{link_type}/query", 
                body=query, 
                query_params={ 
                    "skip":skip, 
                    "take":take, 
                    "select": ",".join(select) if select else None},
                entityClass=dict
                )
            for rec in responseData:
                yield tuple(rec) 
       
        if fetch_all:
            result = []
            page=1
            page_size=500

            while True:
                previous_len=len(result)
                for item in self.query(project_id,link_type, select, query, fetch_all=False, skip=(page-1)*page_size, take=page_size):
                    result.append(item)

                if len(result)==previous_len: #if not more data was fetched
                    return result
                else:
                    page=page+1

        else:
            return list(fetch_data())

class ModelsEndpointGroup(EndpointGroup[data_model.ModelInfo]):
    def __init__(self, client: Client) -> None:
        super().__init__(client)     


    def get_info(self, model_name:str, project_id:str=None)  -> data_model.ModelInfo:
        """Get model details

        Args:
            project_id (str): Uuid of project
            model_name_or_id (str): Uuid of the model

        Returns:
            data_model.ModelInfo: _description_
        """
        
        
        if "/" in model_name or project_id:
            if project_id:
                query={"project_id":project_id}
            else:
                query=None
            return self._call_endpoint("GET", f"models/info/{model_name}", query_params=query)
        else:
            raise Exception("if project_id is not set, model_name must be in this pattern: '{project_name}/{model_name}'")

    def delete(self, project_id:str,model_name_or_id:str)-> None: 
        """Delete model

        Args:
            project_id (str): Uuid of project
            model_name_or_id (str): Uuid of the model

        """
        return self._call_endpoint("DELETE", f"projects/{project_id}/models/{model_name_or_id}")

    def get_all(self,project_id:str)-> List[data_model.ModelInfo]:
        """Get all models for project

        Args:
            project_id (str): Uuid of project

        Returns:
            data_model.ModelInfo: _description_
        """
        return self._call_endpoint("GET", f"projects/{project_id}/models")

    def download(self,project_id:str, model_name_or_id:str, target_path:str=None, unzip=True):
        if not target_path:
            target_path= os.getcwd()
        file_urls = self._call_endpoint("GET", f"/projects/{project_id}/models/download-urls",query_params={"model_name_or_id":model_name_or_id}, entityClass=dict)
        if not file_urls:
            raise Exception("There seams to be no files for this model!")
        for fileUrl in file_urls:
            response = requests.get(fileUrl["url"], stream=True)
            (path,file_name) = os.path.split(fileUrl["file"])
            path = os.path.join(target_path,path)
            if not os.path.exists(path):
                os.makedirs(path)
            
            file_path=os.path.join(target_path, fileUrl["file"])
            with open(file_path, "wb") as handle:
                for data in tqdm(response.iter_content(chunk_size=1024*1024),unit="MB",desc=fileUrl["file"]):
                    handle.write(data)
            
            if unzip and file_path.lower().endswith(".zip"):
               
                with ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(target_path)
                os.remove(file_path)


                
    def apply_predictions(self, project_id:str,model_name_or_id:str)-> "TaskStatusHandle": 
        """Apply predictions from model
        Args:
            project_id (str): Uuid of project
            model_name_or_id (str): Model Uuid
        """
        return TaskStatusHandle(self._call_endpoint("PUT", f"/projects/{project_id}/models/{model_name_or_id}/apply-predict", entityClass=dict), self.client)

    def apply_embeddings(self, project_id:str,model_name_or_id:str)-> "TaskStatusHandle": 
        """Regenerate embeddings and reindex by new model

        Args:
            project_id (str): Uuid of project
             model_name_or_id (str): Model Uuid
        """
        return TaskStatusHandle(self._call_endpoint("PUT", f"/projects/{project_id}/models/{model_name_or_id}/apply-embeddings", entityClass=dict), self.client)



    def train(self, project_id:str, model_training_request:data_model.ModelTrainingRequest)-> "TaskStatusHandle": 
        """Start training task

        Args:
            project_id (str): Uuid of project
            model_training_request (data_model.ModelTrainingRequest): Training settings
        """
        return TaskStatusHandle(self._call_endpoint("PUT", f"/projects/{project_id}/models/train", body=model_training_request.to_dict(), entityClass=dict), self.client)


class TaskEndpointGroup(EndpointGroup[data_model.TaskStatus]):

    def get_latest(self, project_id:Optional[str]=None)-> List[data_model.TaskStatus]: 
        return self._call_endpoint("GET", f"/projects/tasks", query_params={"project_id":project_id} if project_id else None)

    def get_task_status(self, task_id:str)-> data_model.TaskStatus: 
        return self._call_endpoint("GET", f"/projects/tasks/{task_id}")

class ServingNodesEndpointGroup(EndpointGroup[data_model.NodeInfo]):

    def get_nodes(self)-> List[data_model.NodeInfo]: 
        """Returns list of serving nodes

        Returns:
            List[data_model.NodeInfo]
        """
        return self._call_endpoint("GET", f"/serving/nodes")

    def create_node(self, node_name:str, deployment_type:str, node_type:Optional[str]=None, host_url:Optional[str]=None)-> data_model.NodeInfo: 
        """Creates a serving node.
        Based on deployment_type you should set node_type or host_url
        - For deployment_type==managed: set node_type (CPU|GPU)
        - For deployment_type==self-hosted: set host_url so testing the node and calling refresh commands would be possible. If Node is not available on accessible from the internet, it is not needed.


        Args:
            node_name (str): node name must be url compatible name
            deployment_type (str): one of labelatorio.enums.NodeDeploymentTypes options (managed|self-hosted)
            node_type (Optional[str], optional):  one of labelatorio.enums.NodeTypes options (CPU|GPU)
            host_url (Optional[str], optional): url at which the Node will be hosted. Automatically assigned for managed nodes

        Returns:
            data_model.NodeInfo: the created NodeInfo
        """
        return self._call_endpoint("POST", f"/serving/nodes", body=data_model.NodeInfo(node_name=node_name, node_type=node_type, deployment_type=deployment_type, host_url=host_url))

    def get_node(self, node_name:str)-> data_model.NodeInfo: 
        """Get node by its name

        Args:
            node_name (str): _description_

        Returns:
            data_model.NodeInfo: _description_
        """
        return self._call_endpoint("GET", f"/serving/nodes/{node_name}")

    def update_node(self, node_name:str, host_url:str)-> data_model.NodeInfo: 
        return self._call_endpoint("PATCH", f"/serving/nodes/{node_name}", body={"host_url":host_url})

    def delete_node(self, node_name:str):
        return self._call_endpoint("DELETE", f"/serving/nodes/{node_name}", entityClass=dict)

    def start_node(self, node_name:str): 
        return self._call_endpoint("POST", f"/serving/nodes/{node_name}/start", entityClass=dict)

    def stop_node(self, node_name:str): 
        return self._call_endpoint("POST", f"/serving/nodes/{node_name}/stop", entityClass=dict)

    def get_node_settings(self, node_name:str)-> data_model.NodeSettings: 
        return self._call_endpoint("GET", f"/serving/nodes-settings/{node_name}", entityClass=data_model.NodeSettings)

    def update_node_settings(self, node_name:str, settings:data_model.NodeSettings) ->data_model.NodeSettings: 
        return self._call_endpoint("PUT", f"/serving/nodes-settings/{node_name}", body=settings, entityClass=data_model.NodeSettings)


class TopicsEndpointGroup(EndpointGroup[data_model.Topic]):
    def get_all(self, project_id)-> List[data_model.Topic]: 
        results=[]
        page_size=500
        page=0
        while True:
            subresults = self._call_endpoint("GET", f"/projects/{project_id}/topic/search", query_params={"skip":page_size*page,"take":page_size})
            results+=subresults
            page+=1
            if not subresults:
                break
        return results

    def regenerate(self, project_id)-> "TaskStatusHandle": 
        return TaskStatusHandle(self._call_endpoint("POST", f"/projects/{project_id}/topic/regenerate", entityClass=dict), self.client)

    def get_topic(self, project_id, topic_id)-> data_model.Topic: 
        return self._call_endpoint("GET", f"/projects/{project_id}/topic/{topic_id}")
    
    def get_topic_stats(self, project_id, topic_id)-> dict: 
        return self._call_endpoint("GET", f"/projects/{project_id}/topic/{topic_id}/stats", entityClass=dict)
    
    def search_topics(self, project_id, keyword:str, take=50)-> List[data_model.Topic]: 
        return self._call_endpoint("GET", f"/projects/{project_id}/topic/search", query_params={"keyword":keyword, "skip":0,"take":take})




class TaskStatusHandle:
    def __init__(self, task_id:Union[str,dict], client: Client) -> None:
        self.task_id=task_id if isinstance(task_id,str) else task_id["task_id"]
        self.client= client
        self.current_status:data_model.TaskStatus =None

    def __str__(self):
        if self.current_status:
            return f"{self.current_status.task_name} "+tqdm.format_meter(self.current_status.progress_current or 0, self.current_status.progress_total or 0, elapsed=self.current_status.duration_sec or 0) + f" [{self.current_status.state}]" +(f" >> Current subtask: {self.current_status.current_subtask}" if self.current_status.current_subtask else "" + (f"task_id: {self.task_id}") )
        else:
            return f"TaskStatusHandle(task_id:{self.task_id}, current_status:None)"

    def __repr__(self) -> str:
        return str(self)

    def wait_until_finished(self, polling_interval_sec:int = 15, timeout_sec:int = 60*60*6,  print_progress:bool=True):
        wait_itterator = self._get_wait_until_finished_polling_generator(polling_interval_sec,timeout_sec)
        last_print_len=0
        print_out=""
        print("")
        for _it in wait_itterator:
            if print_progress:
                print_out=str(self)
                print('\r'+print_out, end= (" "*(last_print_len-len(print_out))), flush=True)
                last_print_len=len(print_out)
        if print_progress:
            print('\r'+str(self), end=(" "*(last_print_len-len(print_out))), flush=True)

    def refresh_status(self):
        self.current_status = self.client.tasks.get_task_status(self.task_id)
        return self
    
    def is_finished(self):
        return enums.TaskStatusStates.is_done(self.current_status.state)

    def _get_wait_until_finished_polling_generator(self, polling_interval_sec:int, timeout_sec:int):
        
        polling_interval_sec = polling_interval_sec if polling_interval_sec>0 else 15
        for _it in range(int((timeout_sec+polling_interval_sec)/polling_interval_sec)):
            if not self.refresh_status().is_finished():
                yield self
                time.sleep(polling_interval_sec)
            else:
                break
            
        return self



