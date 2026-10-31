"""Small offline API integration smoke test for the materialized SQLite database."""
from fastapi.testclient import TestClient
from app import app

def main():
    client=TestClient(app)
    health=client.get('/health/model'); assert health.status_code==200
    stories=client.get('/stories'); assert stories.status_code==200 and stories.json()['items']
    story_id=stories.json()['items'][0]['id']; detail=client.get(f'/stories/{story_id}'); assert detail.status_code==200
    assert detail.json()['articles'][0]['prediction'] is not None
    article_id=detail.json()['articles'][0]['id']; assert client.get(f'/articles/{article_id}').status_code==200
    prediction=client.post('/predict',json={'text':'The government announced a policy after a parliamentary debate.'}); assert prediction.status_code==200
    print({'health':health.status_code,'stories':len(stories.json()['items']),'article':article_id,'predict':prediction.status_code})
if __name__=='__main__':main()
