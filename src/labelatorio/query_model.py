from typing import List, TypeVar, Optional, Dict, Union
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
        _i:Optional[int] = None,
        id:Union[str,List[str],None] = None,
        key:Union[str,List[str],None] = None,
        text:Union[str,List[str],None] = None,
        labels:Union[str,List[str],None] = None,
        topic_id:Union[str,List[str],None] = None,
        predicted_labels:Union[str,List[str],None] = None,
        predicted_label_scores:Optional[Dict[str,float]]  = None,
        excluded:Optional[bool] = None,
        similar_to_phrase:Optional[str] = None,
        similar_to_doc:Optional[str] = None,
        min_score:Optional[float] = None,
        similar_to_vec:Optional[List[float]] = None,
        false_positives:Union[str,List[str],None] = None,
        false_negatives:Union[str,List[str],None] = None,
        context_data:Optional[Dict[str,str]] =None
    ):
        pass



    def Or(self, antother: "DocumentQueryFilter")->Or:
        return Or(self, antother)