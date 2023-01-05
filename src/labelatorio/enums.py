


class StrEnum:
    def __repr__(self):
        return '<%s.%s>' % (self.__class__.__name__, self.name)

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_all(cls):
        return [v for k,v in vars(cls).items() if not k.startswith("_") and isinstance(v,str) ]




class ProjectSources(StrEnum):
    BIG_QUERY="bigquery"
    FILES="files"


class TaskTypes(StrEnum):
    MULTILABEL_TEXT_CLASSIFICATION="MultiLabelTextClassification"
    TEXT_CLASSIFICATION="TextClassification"
    TEXT_SIMILARITY="TextSimilarity"


class TaskStatusStates(StrEnum):
    PENDING="PENDING"
    RUNNING="RUNNING"
    FINISHED="FINISHED"
    ERROR="ERROR"
    TIMEOUT="TIMEOUT"
    STOPPED="STOPPED"

    def is_done(staus:str):
        if staus==TaskStatusStates.PENDING or staus==TaskStatusStates.RUNNING:
            return False
        else: 
            return True
        


class RouteHandlingTypes(StrEnum):
    MANUAL="manual"
    MODEL_REVIEW="model-review"
    MODEL_AUTO="model-auto"

class RouteRuleType(StrEnum):
    ANCHORS="anchors"
    TRUE_POSITIVES="true-predictions"


class NodeStatusTypes(StrEnum):
    PENDING="PENDING"
    UPDATING="UPDATING"
    READY="READY"
    CONFIG_OUT_OF_DATE="CONFIG_OUT_OF_DATE"
    OFFLINE="OFFLINE"
    ERROR="ERROR"

class NodeTypes(StrEnum):
    CPU="CPU"
    GPU="GPU"


class NodeDeploymentTypes:
    MANAGED="managed"
    SELF_HOSTED="self-hosted"