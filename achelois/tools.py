
def flatten(x):
    result = []
    for el in x:
        if u'None' in el: continue
        try: el.__iter__
        except: result.append(el)
        else: result.extend(flatten(el))
    return result
