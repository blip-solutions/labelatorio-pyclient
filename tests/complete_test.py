import json
import time
import labelatorio
import pandas as pd
from labelatorio import data_model
from labelatorio import enums, DocumentQueryFilter
import random
import os


def _generate_test_data(count:int):
    WORDS_FIRST=["this","that","he"]
    WORDS_SECOND=["is","was","will be"]
    WORDS_THIRD=["short","looong","quiet"]

    keys=[]
    sententes=[]
    for i in range(count):
        keys.append(i)
        sententes.append(f"{random.choice(WORDS_FIRST)} {random.choice(WORDS_SECOND)} {random.choice(WORDS_THIRD)}")
    return {
        "key":keys,
        "text":sententes
    }

def test_complete_scenario():
    with open('_tst_api_token.json', 'r') as jsonFile:
        tokenObj=json.load(jsonFile)
    client = labelatorio.Client(api_token=tokenObj["apiToken"], url="http://localhost:4000")
    

    existing_project = client.projects.get_by_name("unit-test")  
    if existing_project:
         the_project =client.projects.get(project_id=existing_project.id)
    else:
        the_project = data_model.Project.new("unit-test", task_type=enums.TaskTypes.TEXT_CLASSIFICATION)
    the_project.labels=["A","B","C"]
    the_project= client.projects.save(the_project)
    project_id = the_project.id
       
    client.documents.delete_all(project_id)

    TOTAL_COUNT = 500
    df = pd.DataFrame(_generate_test_data(TOTAL_COUNT))

    ids = [res["id"] for res in client.documents.add_documents(project_id, data=df)]
    time.sleep(10)

    client.documents.set_labels(project_id,ids[:10],["A"])
    client.documents.set_labels(project_id,ids[10:20],["B"])
    client.documents.set_labels(project_id,ids[20:30],["C"])
    
    data_df = client.documents.export_to_dataframe(project_id=project_id)
    assert len(data_df)==len(ids), "Size of exported DF doesnt match what we've imported"

    stats=client.projects.get_stats(project_id=project_id)

    assert stats.labeled_count==30  , "labeled count should be 30 but got {stats.labeled_count}"
    
    assert stats.total_count==TOTAL_COUNT, "total count should be {TOTAL_COUNT} but got {stats.total_count}"

    client.documents.exclude(project_id, [ids[-1]])

    client.documents.delete(project_id, ids[-2])

    found = client.documents.search(project_id, key="1")[0]
    assert found.labels==["A"],"document with key 1 should have label A set"

    found = client.documents.query(project_id, query=DocumentQueryFilter(key="1").Or(DocumentQueryFilter(key="2")))
    assert len(found)==2, f"two records queried, but got {len(found)}"

    found = client.documents.search(project_id, false_positives="ClassA")

    neigbours = client.documents.get_neighbours(project_id, found[0].id, min_score=0.5, take=10)
    assert len(neigbours)==10, f"10 records were requested, len{len(neigbours)} returned"

    client.models.train(project_id, data_model.ModelTrainingRequest(
                    task_type=enums.TaskTypes.TEXT_CLASSIFICATION,
                    from_model= the_project.current_model_name,
                    model_name="myDummyModel",
                    max_num_epochs=1
                )
            )
    
    while True:
        time.sleep(30)
        models = client.models.get_all(project_id)
        if models and models[0].is_ready:
            break
    
    cache_model = ".cache/tests"
    if not os.path.exists(cache_model):
        os.makedirs(cache_model)
    client.models.apply_predictions(project_id, model_name_or_id=models[0].id)
    client.models.download(project_id, model_name_or_id=models[0].id, target_path=cache_model)
    import shutil
    shutil.rmtree(cache_model)


if __name__=="__main__":
    test_complete_scenario()

    

