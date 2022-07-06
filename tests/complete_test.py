import json
import time
import labelatorio
import pandas as pd
from labelatorio import data_model
from labelatorio import enums
import random


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
    
    client.projects.get

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

    ids = client.documents.add_documents(project_id, data=df)

    client.documents.set_labels(project_id,ids[:10],["A"])
    client.documents.set_labels(project_id,ids[10:20],["B"])
    client.documents.set_labels(project_id,ids[20:30],["C"])

    stats=client.projects.get_stats(project_id=project_id)

    assert stats.labeled_count==30  , "labeled count should be 30 but got {stats.labeled_count}"
    
    assert stats.total_count==TOTAL_COUNT, "total count should be {TOTAL_COUNT} but got {stats.total_count}"

    client.documents.exclude(project_id, [ids[-1]])

    client.documents.delete(project_id, ids[-2])

    found = client.documents.search(project_id, key="1")[0]
    assert found.labels==["A"],"document with key 1 should have label A set"
    
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
    
    client.models.apply_predictions(project_id, model_id=models[0].id)
    file_path = client.models.download(project_id, model_id=models[0].id)
    import shutil
    shutil.rmtree(file_path)


if __name__=="__main__":
    test_complete_scenario()

    

