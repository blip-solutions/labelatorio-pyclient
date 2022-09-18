from typing import List, TypeVar
from functools import wraps
import inspect
T = TypeVar('T')


def dict_initializer(func):
    """
    Automatically assigns the parameters.

    >>> class process:
    ...     @initializer
    ...     def __init__(self, cmd, reachable=False, user='root'):
    ...         pass
    >>> p = process('halt', True)
    >>> p.cmd, p.reachable, p.user
    ('halt', True, 'root')
    """


    @wraps(func)
    def wrapper(self, *args, **kargs):
        for key, val in kargs.items():
            self[key]=val

    
        func(self, *args, **kargs)

    return wrapper



class Or(dict):
    """
    example:
    {
        "Or":[
            {
                "field":"value",
                "field2":"!value",
                "field2":{">":32,"<":45}
            },
            {
                "field":"42"
            }
        ]
    }
    """
    def __init__(self, *args) -> None:
        self["Or"]=args




class DocumentQueryFilter(dict):
    
    @dict_initializer
    def __init__(self, 
        _i = None,
        id = None,
        key = None,
        text = None,
        labels = None,
        topic_id = None,
        topic_propability = None,
        predicted_labels = None,
        context_data = None,
        predicted_label_scores = None,
        excluded = None,
        similar_to_phrase:str = None,
        similar_to_doc:str = None,
        similar_to_vec:List[float] = None,
        false_positives:bool = None,
        false_negatives:bool = None
    ):
        pass



    def Or(self, antother: "DocumentQueryFilter")->Or:
        return Or(self, antother)