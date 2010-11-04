
from os import path, mkdir
#try: import json
#except ImportError:
import simplejson
json = simplejson


settingsdir = path.expanduser('~/.nara')
_settingsfile = 'settings.json'
settingsfile = path.join(settingsdir, _settingsfile)

_sourcesfile = 'sources.json'
sourcesfile = path.join(settingsdir, _sourcesfile)

_xapidx = 'xap.idx'
xapidx = path.join(settingsdir, _xapidx)

_convdb = 'conv.idx'
convdb = path.join(settingsdir, _convdb)

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


sources = None
def load_sources():
    if not path.exists(settingsdir):
        mkdir(settingsdir)

    global sources
    with open(sourcesfile) as f:
        sources = json.load(f)
def get_sources():
    global sources
    if not sources: load_sources()
    return sources

def save_sources():
    if not path.exists(settingsdir):
        mkdir(settingsdir)

    global sources
    with open(sourcesfile) as f:
        json.dump(sources, f)

