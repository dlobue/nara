from datetime import datetime

def flatten(x):
    result = []
    for el in x:
        if u'None' in el: continue
        try: el.__iter__
        except: result.append(el)
        else: result.extend(flatten(el))
    return result

def flatnique(x):
    return list(set(sum(x,[])))

def unidecode_date(x):
    '''turn a unicoded date string made using uniencode_date back into a datetime object'''
    return datetime(map(int, x.split(u','))[:6])

def uniencode_date(x):
    '''turn a datetime tuple into a unicode string seperated by commas'''
    return u','.join(map(unicode,x)[:6])

def deuniNone(x):
    '''remove unicoded None's if found'''
    try: x.remove(u'None')
    except: pass
    return x
