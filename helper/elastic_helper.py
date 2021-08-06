import re

from elasticsearch import Elasticsearch
from helper.env_variables import *


def __get_es_instance():
    es_url = os.getenv('ES_URL')
    auth = re.search('https://(.*)@', es_url).group(1).split(':')
    host = es_url.replace('https://%s:%s@' % (auth[0], auth[1]), '')

    # optional port
    match = re.search('(:\d+)', host)
    if match:
        p = match.group(0)
        host = host.replace(p, '')
        port = int(p.split(':')[1])
    else:
        port = 443

    # Connect to cluster over SSL using auth for best security:
    es_header = [{
        'host': host,
        'port': port,
        'use_ssl': True,
        'http_auth': (auth[0], auth[1])
    }]

    # Instantiate the new Elasticsearch connection:
    es_obj = Elasticsearch(es_header)
    return es_obj


def __create_index_if_not_exists(index_name):
    if not es.indices.exists(index_name):
        es.indices.create(index=index_name, ignore=400)


def __delete_index_if_exists(index_name):
    if es.indices.exists(index_name):
        es.indices.delete(index_name)


es = __get_es_instance()
es.indices.forcemerge(index='_all', only_expunge_deletes=True)

es_token_index_name = os.getenv('ES_TOKEN_INDEX_NAME')
es_trade_details_index_name = os.getenv('ES_TRADE_DETAILS')
es_trade_history_details_index_name = os.getenv('ES_TRADE_HISTORY_DETAILS')
