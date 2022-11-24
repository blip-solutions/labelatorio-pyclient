import time
import labelatorio

CLASSIFICATION_NODE_URL="http://localhost:8000"
QNA_NODE_URL="http://localhost:8003"

def test_predictions():
    client = labelatorio.serving.NodeClient(url=CLASSIFICATION_NODE_URL)
    test_prediction = client.predict("test", test=True)
    assert test_prediction and test_prediction.predictions, "Missing predictions"

    assert test_prediction and len(test_prediction.predictions)==1, "There should be exactly one prediciton"
    
    test_prediction = client.predict("test", explain=True)

    for p in test_prediction.predictions:
        assert isinstance(p.explanations,list), "Missing explanations"

    test_prediction1 = client.predict(labelatorio.PredictionRequestRecord(text="test"), test=True)
    test_prediction2 = client.predict([labelatorio.PredictionRequestRecord(text="test")], test=True)
    assert test_prediction1.dict() ==test_prediction2.dict(), "reponses should be the same"

    query=[labelatorio.PredictionRequestRecord(text="test"),labelatorio.PredictionRequestRecord(text="another test")]
    test_prediction = client.predict(query, test=True)
    assert test_prediction and len(query)==len(query), "Number of predictions doesnt match"

def test_questions():
    client = labelatorio.serving.NodeClient(url=QNA_NODE_URL)
    test_prediction = client.get_answer("test", test=True)
    assert test_prediction and test_prediction.predictions, "Missing predictions"

    assert test_prediction and len(test_prediction.predictions)==1, "There should be exactly one prediciton"
    
    

   


if __name__=="__main__":
    test_predictions()
    test_questions()