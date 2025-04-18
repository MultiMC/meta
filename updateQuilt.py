#!/usr/bin/python3
import os, requests
from cachecontrol import CacheControl
import datetime
import hashlib, json
import zipfile
from quiltutil import *

from cachecontrol.caches import FileCache

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

blacklist = ("0.17.5-beta.5", "0.17.5-beta.4")

def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()

class MavenSpecifier:
    def __init__(self, mavenKey):
        mavenParts = mavenKey.split(":", 3)
        self.group = mavenParts[0]
        self.name = mavenParts[1]
        self.version = mavenParts[2]

    def path(self):
        return self.group.replace(".", "/") + "/" + self.name + "/" + self.version + "/"

    def filename(self, ext):
        return self.name + "-" + self.version + ext

    def url(self, server, ext):
        return server + self.path() + self.filename(ext)


def get_maven_url(mavenKey, server, ext):
    mavenParts = mavenKey.split(":", 3)
    mavenVerUrl = server + mavenParts[0].replace(".", "/") + "/" + mavenParts[1] + "/" + mavenParts[2] + "/"
    mavenUrl = mavenVerUrl + mavenParts[1] + "-" + mavenParts[2] + ext
    return mavenUrl

def get_json_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        version_json = r.json()
        json.dump(version_json, f, sort_keys=True, indent=4)
        return version_json

def get_binary_file(path, url):
    with open(path, 'w', encoding='utf-8') as f:
        r = sess.get(url)
        r.raise_for_status()
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=128):
                f.write(chunk)

def compute_jar_file(path, url):
    jarPath = path + ".jar"
    get_binary_file(jarPath, url)
    tstamp = datetime.datetime.fromtimestamp(0)
    with zipfile.ZipFile(jarPath, 'r') as jar:
        allinfo = jar.infolist()
        for info in allinfo:
            tstampNew = datetime.datetime(*info.date_time)
            if tstampNew > tstamp:
                tstamp = tstampNew
    data = QuiltJarInfo()
    data.releaseTime = tstamp
    data.sha1 = filehash(jarPath, hashlib.sha1)
    data.sha256 = filehash(jarPath, hashlib.sha256)
    data.size = os.path.getsize(jarPath)
    with open(path + ".json", 'w') as outfile:
        json.dump(data.to_json(), outfile, sort_keys=True, indent=4)

mkdirs("upstream/quilt/meta-v3")
mkdirs("upstream/quilt/loader-installer-json")
mkdirs("upstream/quilt/jars")

# get the version list for each component we are interested in
#for component in ["intermediary", "loader"]:
for component in ["loader"]:
    index = get_json_file("upstream/quilt/meta-v3/" + component + ".json", "https://meta.quiltmc.org/v3/versions/" + component)
    for it in index:
        spec = MavenSpecifier(it["maven"])
        jarMavenUrl = spec.url("https://maven.quiltmc.org/repository/release/", ".jar");
        if spec.version in blacklist:
            print("Ignoring ", jarMavenUrl)
            continue
        print("Looking up", jarMavenUrl)
        compute_jar_file("upstream/quilt/jars/" + it["maven"].replace(":", "."), jarMavenUrl)

# for each loader, download installer JSON file from maven
with open("upstream/quilt/meta-v3/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
    loaderVersionIndex = json.load(loaderVersionIndexFile)
    for it in loaderVersionIndex:
        spec = MavenSpecifier(it["maven"])
        mavenUrl = spec.url("https://maven.quiltmc.org/repository/release/", ".json")
        if spec.version in blacklist:
            print("Ignoring metadata from", mavenUrl)
            continue
        print("Getting metadata from", mavenUrl)
        get_json_file("upstream/quilt/loader-installer-json/" + it["version"] + ".json", mavenUrl)
