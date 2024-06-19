import json
import requests
import os

import requests 


import minsearch

def prepare_knowledge_base() -> minsearch.Index:
    docs_url = 'https://github.com/DataTalksClub/llm-zoomcamp/blob/main/01-intro/documents.json?raw=1'
    docs_response = requests.get(docs_url)
    docs_raw = docs_response.json()

    documents = []

    for course_dict in docs_raw:
        for doc in course_dict["documents"]:
            doc["course"] = course_dict["course"]
            documents.append(doc)

    index = minsearch.Index(
        text_fields=["question", "text", "section"],
        keyword_fields=["course"]
    )
    index.fit(documents)

    return index


def simple_search(query, index):
    boost = {"question": 3.0, "section": 0.5}

    results = index.search(
        query=query,
        filter_dict={"course": "data-engineering-zoomcamp"},
        boost_dict=boost,
        num_results=5
    )

    return results


def build_prompt(query, search_results):
    prompt_template = """
You're a course teaching assistant. Answer the QUESTION based on the CONTEXT from the FAQ database.
Use only the facts from the CONTEXT when answering the QUESTION.

QUESTION: {question}

CONTEXT: 
{context}
""".strip()

    context = ""
    
    for doc in search_results:
        context = context + f"section: {doc["section"]}\nquestion: {doc["question"]}\nanswer: {doc["text"]}\n\n"
    
    prompt = prompt_template.format(question=query, context=context).strip()
    return prompt


def llm(prompt):

    OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        data=json.dumps({
            "model": "google/gemma-7b-it:free",
            "messages": [
            { "role": "user", "content": prompt }
            ]
        })
        )
    
    return response.json()["choices"][0]["message"]["content"].strip()


def elasticsearch_search(query):
    from elasticsearch import Elasticsearch
    es_client = Elasticsearch("http://localhost:9200")

    index_settings = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "text": {"type": "text"},
                "section": {"type": "text"},
                "question": {"type": "text"},
                "course": {"type": "keyword"} 
            }
        }
    }

    index_name = "course-questions"

    try:
        es_client.indices.create(index=index_name, body=index_settings)
    except:
        print("The index is created already")

    docs_url = 'https://github.com/DataTalksClub/llm-zoomcamp/blob/main/01-intro/documents.json?raw=1'
    docs_response = requests.get(docs_url)
    docs_raw = docs_response.json()

    documents = []

    for course_dict in docs_raw:
        for doc in course_dict["documents"]:
            doc["course"] = course_dict["course"]
            documents.append(doc)

    from tqdm.auto import tqdm
    for doc in tqdm(documents):
        es_client.index(index=index_name, document=doc)

    search_query = {
        "size": 5,
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["question^3", "text", "section"],
                        "type": "best_fields"
                    }
                },
                "filter": {
                    "term": {
                        "course": "data-engineering-zoomcamp"
                    }
                }
            }
        }
    }

    response = es_client.search(index=index_name, body=search_query)

    result_docs = []
    for hit in response["hits"]["hits"]:
        result_docs.append(hit["_source"])

    return result_docs


def rag(query, index):
    search_results = elasticsearch_search(query)
    prompt = build_prompt(query, search_results)
    answer = llm(prompt)
    return answer


index = prepare_knowledge_base()
query = "is it too late to enroll the course?"
print(elasticsearch_search(query))

# print(rag(query, index))