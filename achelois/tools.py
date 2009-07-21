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
    y = map(int, x.split(u','))
    return datetime(y[0], y[1], y[2], y[3], y[4], y[5])

def uniencode_date(x):
    '''turn a datetime tuple into a unicode string seperated by commas'''
    return u','.join(map(unicode,x)[:6])

def deuniNone(x):
    '''remove unicoded None's if found'''
    try: x.remove(u'None')
    except: pass
    return x

def catapillar(x,sep=u' '):
    index = unicode.index
    append = list.append
    r = []
    while 1:
        if sep in x:
            i = index(x, sep)
            append(r, x[:i])
            x = x[i:]
        else: break
    if r: return r
    return x

def catapillar2(x,sep=u' '):
    index = unicode.index
    append = list.append
    c = 0
    r = []
    while 1:
        if sep in x[c:]:
            i = index(x[c:], sep)
            append(r, x[c:c+i])
            c += i
        else: break
    if r: return r
    return x
