
from datetime import datetime
from dateutil import parser
from typing import *
from dataclasses_json import dataclass_json, config
from dataclasses import  dataclass
from marshmallow import fields
import uuid
import labelatorio.enums as enums
from collections.abc import Sequence 

from dataclasses import dataclass, field


@dataclass_json
@dataclass
class TextDocument:
    id:str
    key:str
    text:str
    topic_id:Union[str,None]=None
    topic_propability:Union[float,None] = None
    labels:Union[List[str],None] =None
    predicted_labels:Union[List[str],None] = None
    predicted_label_scores:Union[Dict[str, float],None]=None
    context_data:Union[Dict[str,str],None]=None
    excluded:bool = False
    _i:Union[int,None] = None

    COL_ID="id"
    COL_KEY="key"
    COL_TEXT="text"
    COL_LABELS="labels"
    COL_TOPIC_ID="topic_id"
    COL_TOPIC_PROPABILITY="topic_propability"
    COL_PREDICTED_LABELS="predicted_labels"
    COL_PREDICTED_LABEL_SCORES="predicted_label_scores"
    COL_CONTEXT_DATA="context_data"
    COL_EXCLUDED="excluded"
    COL_IINDEX="_i"
    _COL_VECTOR="vector"

    def __getitem__(self, key: str):
        # mimicking some dataframe access ops to be abble to use for bulk insert in repository
        return getattr(self,key)

    def __contains__(self, key:str):
        # mimicking some dataframe access ops to be abble to use for bulk insert in repository
        return hasattr(self, key)
            
    def keys(self):
        return [
            TextDocument.COL_ID, 
            TextDocument.COL_KEY, 
            TextDocument.COL_LABELS, 
            TextDocument.COL_TOPIC_ID, 
            TextDocument.COL_TOPIC_PROPABILITY, 
            TextDocument.COL_PREDICTED_LABELS, 
            TextDocument.COL_CONTEXT_DATA, 
            TextDocument.COL_EXCLUDED,
            TextDocument.COL_IINDEX
            ]


@dataclass_json
@dataclass
class ScoredDocumentResponse:
    score:float
    doc:TextDocument


@dataclass_json
@dataclass
class TopicKeyword():
    word:str
    score:float
    


@dataclass_json
@dataclass
class Topic:
    topic_id:str
    topic_name:str
    topic_keywords:Union[List[TopicKeyword],None] = None
    representative_samples:Union[List[TextDocument],None] =None
    size:Union[int,None] = None
    centroid:Union[List[float],None] = None

    def __post_init__(self, *args, **kwargs):
        if self.representative_samples and len(self.representative_samples)>0 and isinstance(self.representative_samples[0],Dict):
            self.representative_samples=[TextDocument.from_dict(rs) for rs in self.representative_samples]
    


@dataclass_json
@dataclass
class ProjectBasicStatistics():
    total_count:int
    labeled_count:int


@dataclass_json
@dataclass
class ProjectStatistics(ProjectBasicStatistics):
    by_label_count:Dict[str,int]


@dataclass_json
@dataclass
class LabelSettings:
    label:Optional[str] = None
    icon:Optional[str] = None
    key_bindings:Optional[str] = None
    color:Optional[str] = None
    keywords:Optional[List[str]]=None

@dataclass_json
@dataclass
class Project:
    id:Union[str,None]
    name:str
    task_type:str = None
    source:Optional[str] =None
    data_source_files:Union[List[str],None] = None
    current_model_name:Optional[str] =None
    query:Union[None,str] = None
    task_type:Optional[str] =None
    labels:Optional[List[str]] = None
    statistics:Union[ProjectBasicStatistics,None] = None
    data_import_state:Union[str,None] = None
    label_settings:Optional[Dict[str,LabelSettings]] = None

    def new(name:str, task_type:str, ):
        if  task_type not in enums.TaskTypes.get_all():
            raise Exception(f"Invalid task_type: {task_type}")
            
        return Project(id=None, name=name, task_type=task_type)

@dataclass_json
@dataclass
class ProjectInfo:
    id:Union[str,None]
    name:str
    # task_type:str
    # labels:str
    # label_settings:Optional[Dict[str,LabelSettings]] = None




@dataclass_json
@dataclass
class TrainingParams:
    labels_filter:Union[List[str],None] = None
    learning_rate:float = 5e-5
    weight_decay:float = 0
    split:int = 70
    warmup_steps:int = 0

    def __post_init__(self, *args, **kwargs):
        self.learning_rate = float(self.learning_rate)
        self.weight_decay = float(self.weight_decay)
        self.split = int(self.split)
        self.warmup_steps = int(self.warmup_steps)


@dataclass_json
@dataclass
class ModelInfo:
    id:Union[str,None]
    project_id:str
    model_name:str
    task_type:Union[str,None]
    created_at:datetime =field(
        metadata=config(
            encoder=datetime.isoformat,
            decoder=parser.parse,
            mm_field=fields.DateTime(format='iso')
        )
    )
    model_origin:str=None
    train_params: TrainingParams = None
    metrics: Dict[str,str]=None
    is_ready:bool = True

    def new(project_id:str, task_type:str, model_name:str, model_origin:str, train_params:TrainingParams) -> "ModelInfo":
        return ModelInfo(ModelInfo.create_model_id(project_id), project_id=project_id, model_name=model_name, task_type=task_type, created_at=datetime.utcnow(), model_origin=model_origin,train_params=train_params)

    def create_model_id(project_id):
        return f"{project_id}--{uuid.uuid4()}"

    
@dataclass_json
@dataclass
class ModelTrainingRequest:
    task_type:str
    from_model:str
    model_name:str=None
    max_num_epochs:int=5
    training_params:"ClassificationTrainingParams"=None


@dataclass_json
@dataclass
class TrainingParamsBase:
    learning_rate:float = 5e-5
    weight_decay:float = 0
    split:int = 70
    warmup_steps:int = 0

    def __post_init__(self, *args, **kwargs):
        self.learning_rate = float(self.learning_rate)
        self.weight_decay = float(self.weight_decay)
        self.split = int(self.split)
        self.warmup_steps = int(self.warmup_steps)

@dataclass_json
@dataclass
class ClassificationTrainingParams(TrainingParamsBase):
    labels_filter:Union[List[str],None] = None

@dataclass_json
@dataclass
class SimilarityTrainingParams(TrainingParamsBase):
    classification_pretraining:bool=False
    classification_pretraining_steps:int=3