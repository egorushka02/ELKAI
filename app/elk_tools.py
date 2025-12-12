"""
Инструменты для работы с Elasticsearch.
"""
from elasticsearch import Elasticsearch
from typing import List, Dict, Any
from app.config import settings

def _build_es_client() -> Elasticsearch:
    host = settings.elasticsearch_host
    port = settings.elasticsearch_port
    user = settings.elasticsearch_username
    pwd  = settings.elasticsearch_password
    index_pattern = settings.elasticsearch_index_pattern

    # Формируем base_url
    base_url = f"http://{host}:{port}"
    if user and pwd:
        base_url = f"http://{user}:{pwd}@{host}:{port}"

    # Создаем клиент для ES 8.14
    client = Elasticsearch(
        base_url,
        verify_certs=False,
        ssl_show_warn=False,
        request_timeout=30
    )
    
    # Сохраняем паттерн в клиенте, чтобы не прокидывать его каждый раз
    client._index_pattern = index_pattern
    return client

es = _build_es_client()

def kql_to_es_query(kql: str, size: int = 100) -> Dict[str, Any]:
    return {
        "query": {"query_string": {"query": kql, "default_field": "*"}},
        "size": size,
        "sort": [{"@timestamp": {"order": "desc"}}],
        "_source": True,
    }

def execute_kql(kql: str, size: int = 100) -> Dict[str, Any]:
    query_body = kql_to_es_query(kql, size)
    
    # Используем старый API с body для совместимости
    resp = es.search(
        index=es._index_pattern,
        body=query_body
    )
    
    return {
        "total": resp["hits"]["total"]["value"] if isinstance(resp["hits"]["total"], dict) else resp["hits"]["total"],
        "hits": [hit["_source"] for hit in resp["hits"]["hits"]],
    }