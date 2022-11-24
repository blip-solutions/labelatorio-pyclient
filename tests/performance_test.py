import json
import labelatorio
import asyncio

def test_get_proj_perfomance():
    with open('_tst_api_token.json', 'r') as jsonFile:
        tokenObj=json.load(jsonFile)
    client = labelatorio.Client(api_token=tokenObj["apiToken"] ) #, url="http://localhost:4000")

    
    projects = client.projects.search(search_name=None)
    
    loop = asyncio.get_event_loop()
    for i in range(500):
        tasks = [
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
            loop.create_task(get_project(client, projects[0].id)),
        ]
        loop.run_until_complete(asyncio.wait(tasks))
        print(i)
    loop.close()

        

async def get_project(client, project_id):
    client.projects.get(project_id)


if __name__=="__main__":
    test_get_proj_perfomance()