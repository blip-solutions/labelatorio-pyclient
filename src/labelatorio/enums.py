


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