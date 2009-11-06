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

def search(sconn, query, collapse=False):
    __searchargs = (0, 99999999)
    __searchkwargs = {'checkatleast': -1, 'sortby': '-sent'}
    if collapse: __searchkwargs['collapse'] = 'thread'
    __results = sconn.search(query, *__searchargs, **__searchkwargs)
    return __results

