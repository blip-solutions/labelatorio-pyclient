Labelator.io - python client
==========================

Python client for **[Labelator.io](https://www.Labelato.io)** - labeling and ML training studio



## Install
```
pip install labelatorio
```

## Getting your API token
![Click on "user" icon in the rigth-top corner, select "User settings". Click on Get API token. Copy token into clipboard. ](/docs/get_token.png "Get your api token")



## Usage


### Connecting client

``` python
    import labelatorio
    client = labelatorio.Client(api_token="your_api_token")

```

### Getting project info

Package requirements are handled using pip. To install them do

```python
# get project by id
existing_project = client.projects.get("2fab1778-e8b1-4327-ac83-16dd0e783ab4")

# if you have just name
existing_project = client.projects.get_by_name("my name")

# or if you don't know the exact name
existing_project = client.projects.search("my name")
```

### Adding, updating documents

```python
df = pd.DataFrame({
        "key":["first","second"], # mandatory
        "text":["this is my first text", "completely different text..."],  # mandatory
        "my_custom_column":["note 1",None] # optional
        "labels":[["ClassA"],None] #optional if you have labels - should be defined in project
    })

ids = client.documents.add_documents(project_id, data=df)

client.documents.set_labels(project_id,ids[1],["ClassB"])
```

### Quering documents

```python
# simple keyword search ... 
found = client.documents.search(keyword="completely different") 

# find all documents where "ClassA" was predicted
found = client.documents.search( predicted_label="ClassA")

# find all documents where "ClassA" was incorrectly predicted
found = client.documents.search( false_positives="ClassA")

```