from overwatch import eband
from databasics import msg_factory

def get_threads(sconn, query):
    __threads = search(sconn, query, True)
    __threads = map(lambda x: x.data['thread'][0], __threads)
    return __threads

def get_members(sconn, tids):
    #compose the query
    query = map(lambda x: sconn.query_field('thread', x, sconn.OP_OR), tids)
    query = sconn.query_composite( sconn.OP_OR, query )

    results = search(sconn, query)
    results = map(msg_factory, results)
    return results

def search(sconn, query, collapse=False, minrank=0, maxrank=99999999):
    __searchkwargs = {'checkatleast': -1, 'sortby': '-sent'}
    if collapse: __searchkwargs['collapse'] = 'thread'
    __results = sconn.search(query, minrank, maxrank, **__searchkwargs)
    return __results

