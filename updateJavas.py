#!/usr/bin/python3
import json

from pprint import pprint
from javasutil import *

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

def get_version_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        assetId = version_json["assetIndex"]["id"]
        assetUrl = version_json["assetIndex"]["url"]
        json.dump(version_json, f, sort_keys=True, indent=4)
        return assetId, assetUrl

def get_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)

# get the local version list
localJRElist = None
try:
    with open("upstream/jres/all.json", 'r', encoding='utf-8') as localIndexFile:
        localJRElist = JREIndexWrap(json.load(localIndexFile))
except:
    localJRElist = JREIndexWrap({})
# localIDs = set(localJRElist.versions.keys())

# get the remote package list
r = sess.get('https://launchermeta.mojang.com/v1/products/java-runtime/2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json')
r.raise_for_status()
main_json = r.json()
remoteJRElist = JREIndexWrap(main_json)
# remoteIDs = set(remoteJRElist.versions.keys())

# versions not present locally but present remotely are new
# newIDs = remoteIDs.difference(localIDs)

# versions present both locally and remotely need to be checked
# checkedIDs = remoteIDs.difference(newIDs)

# versions that actually need to be updated have updated timestamps or are new
# updatedIDs = newIDs
# for id in checkedIDs:
#     remoteVersion = remoteJRElist.versions[id]
#     localVersion = localJRElist.versions[id]
#     if remoteVersion.time > localVersion.time:
#         updatedIDs.add(id)

# update versions
# for id in updatedIDs:
#     version = remoteJRElist.versions[id]
#     print("Updating " + version.id + " to timestamp " + version.releaseTime.strftime('%s'))
#     assetId, assetUrl = get_version_file( "upstream/jres/versions/" + id + '.json', version.url)
#     assets[assetId] = assetUrl

with open("upstream/jres/all.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)
