
from os import path, mkdir
#try: import json
#except ImportError:
import simplejson
json = simplejson


settingsdir = path.expanduser('~/.nara')
_settingsfile = 'settings.json'
settingsfile = path.join(settingsdir, _settingsfile)

_xapidx = 'xap.idx'
xapidx = path.join(settingsdir, _xapidx)

settings = None
def load_settings():
    if not path.exists(settingsdir):
        mkdir(settingsdir)

    global settings
    with open(settingsfile) as f:
        settings = json.load(f)
def get_settings():
    global settings
    if not settings: load_settings()
    return settings

def save_settings():
    if not path.exists(settingsdir):
        mkdir(settingsdir)

    global settings
    with open(settingsfile) as f:
        json.dump(settings, f)

'''
settings = {
    "ixmetadir": "/tank/projects/emailtest/index_dir", 
    "maildirinc": [
        "INBOX", 
        "INBOX.MIEN", 
        "INBOX.Read", 
        "INBOX.alertsite", 
        "INBOX.atg errors", 
        "INBOX.hp sim", 
        "INBOX.misc", 
        "INBOX.mom", 
        "INBOX.monit", 
        "INBOX.nagios", 
        "INBOX.networkperf", 
        "INBOX.receipt", 
        "INBOX.save", 
        "INBOX.scom", 
        "Sent", 
        "Sent Items"
    ], 
    "rdir": "/tank/projects/emailtest/offlineimap/dlobue"
    }
    '''
