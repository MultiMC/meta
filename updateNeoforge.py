#!/usr/bin/python3
'''
 Get the source files necessary for generating NeoForge versions
'''
from __future__ import print_function
import sys

import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

import json
import copy
import re
import zipfile
from metautil import *
from jsonobject import *
from neoforgeutil import *
import os.path
import datetime
import hashlib
from pathlib import Path
from contextlib import suppress

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def filehash(filename, hashtype, blocksize=65536):
    hash = hashtype()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), b""):
            hash.update(block)
    return hash.hexdigest()

forever_cache = FileCache('http_cache', forever=True)
sess = CacheControl(requests.Session(), forever_cache)

# get the remote version list fragments
r = sess.get('https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge')
r.raise_for_status()
main_json = r.json()["versions"]
assert type(main_json) == list

# get the remote version list fragments
r = sess.get("https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/forge")
r.raise_for_status()
legacy_json = r.json()["versions"]
assert type(legacy_json) == list

main_json = legacy_json + main_json

newIndex = DerivedNeoforgeIndex()

versionExpression = re.compile("^(?P<mcminor>[0-9]+)\\.(?P<mcpatch>[0-9]+)\\.(?P<build>[0-9]+)(?:-(?P<branch>[a-zA-Z0-9_]+))?$")
legacyVersionExpression = re.compile("^(?P<mc_version>[0-9a-zA-Z_\\.]+)-(?P<version>[0-9\\.]+\\.(?P<build>[0-9]+))(-(?P<branch>[a-zA-Z0-9\\.]+))?$")

def getSingleNeoforgeFilesManifest(longversion, legacy):
    pathThing = "upstream/neoforge/files_manifests/%s.json" % longversion
    files_manifest_file = Path(pathThing)
    from_file = False
    if files_manifest_file.is_file():
        with open(pathThing, 'r') as f:
            files_json=json.load(f)
            from_file = True
    else:
        fileUrl = 'https://maven.neoforged.net/api/maven/details/releases/net/neoforged/%s/%s' % ("forge" if legacy else "neoforge", longversion)
        r = sess.get(fileUrl)
        r.raise_for_status()
        files_json = r.json()

    retDict = dict()

    for file in files_json.get('files'):
        assert type(file) == dict

        if file["type"] != 'FILE':
            continue
        if file["name"].endswith((".md5", ".sha1", ".sha256", ".sha512", ".pom", ".asc")):
            continue

        fileName = file["name"]
        filePrefix = '%s-%s-' %  ("forge" if legacy else "neoforge", longversion)

        assert fileName.startswith(filePrefix)
       
        fileSuffix = fileName[len(filePrefix):]
        classifier, extension = os.path.splitext(fileSuffix)

        fileObj = NeoforgeFile(
            classifier=classifier,
            extension=extension[1:],
            legacy=legacy
        )
        retDict[classifier] = fileObj

    if not from_file:
        with open(pathThing, 'w', encoding='utf-8') as f:
            json.dump(files_json, f, sort_keys=True, indent=4)

    return retDict

print("")
print("Making dirs...")
os.makedirs("upstream/neoforge/jars/", exist_ok=True)
os.makedirs("upstream/neoforge/installer_info/", exist_ok=True)
os.makedirs("upstream/neoforge/installer_manifests/", exist_ok=True)
os.makedirs("upstream/neoforge/version_manifests/", exist_ok=True)
os.makedirs("upstream/neoforge/files_manifests/", exist_ok=True)

print("")
print("Processing versions:")
for longversion in main_json:
    assert type(longversion) == str
    match = versionExpression.match(longversion)
    legacy = False

    if not match:
        match = legacyVersionExpression.match(longversion)
        if not match:
            pprint(longversion)
            assert match
        legacy = True
        package = "forge"
        branch = match.group("branch")
        build = int(match.group("build"))
        mcversion = match.group("mc_version")
        ver = match.group("version")
    else:
        package = "neoforge"
        branch = match.group("branch")
        build = int(match.group("build"))
        mcversion = '1.%s.%s' % (match.group('mcminor'), match.group('mcpatch'))
        ver = match.group("build")

    try:
        files = getSingleNeoforgeFilesManifest(longversion, legacy)
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            continue
        else:
            raise
    except:
        raise

    entry = NeoforgeEntry(
        package=package,
        longversion=longversion,
        mcversion=mcversion,
        version=ver,
        build=build,
        branch=branch,
        latest=False,
        # TODO:
        recommended=False,
        files=files
    )
    newIndex.versions[longversion] = entry
    if not newIndex.by_mcversion:
        newIndex.by_mcversion = dict()
    if not mcversion in newIndex.by_mcversion:
        newIndex.by_mcversion.setdefault(mcversion, NeoforgeMcVersionInfo())
    newIndex.by_mcversion[mcversion].versions.append(longversion)

    if entry.recommended:
        newIndex.by_mcversion[mcversion].recommended = longversion

print("")
print("Post processing promotions and adding missing 'latest':")
for mcversion, info in newIndex.by_mcversion.items():
    latestVersion = info.versions[-1]
    info.latest = latestVersion
    newIndex.versions[latestVersion].latest = True
    print("Added %s as latest for %s" % (latestVersion, mcversion))

print("")
print("Dumping index files...")

with open("upstream/neoforge/maven-metadata.json", 'w', encoding='utf-8') as f:
    json.dump(main_json, f, sort_keys=True, indent=4)

with open("upstream/neoforge/derived_index.json", 'w', encoding='utf-8') as f:
    json.dump(newIndex.to_json(), f, sort_keys=True, indent=4)

versions = []

print("Grabbing installers and dumping installer profiles...")
# get the installer jars - if needed - and get the installer profiles out of them
for id, entry in newIndex.versions.items():
    eprint ("Updating NeoForge %s" % id)
    if entry.mcversion == None:
        eprint ("Skipping %d with invalid MC version" % entry.build)
        continue

    version = NeoforgeVersion(entry)
    print(version.longVersion)

    if version.url() == None:
        eprint ("Skipping %d with no valid files" % version.build)
        continue

    jarFilepath = "upstream/neoforge/jars/%s" % version.filename()

    installerInfoFilepath = "upstream/neoforge/installer_info/%s.json" % version.longVersion
    profileFilepath = "upstream/neoforge/installer_manifests/%s.json" % version.longVersion
    versionJsonFilepath = "upstream/neoforge/version_manifests/%s.json" % version.longVersion
    installerRefreshRequired = False
    if not os.path.isfile(profileFilepath):
        installerRefreshRequired = True
    if not os.path.isfile(installerInfoFilepath):
        installerRefreshRequired = True

    if installerRefreshRequired:
        # grab the installer if it's not there
        if not os.path.isfile(jarFilepath):
            eprint ("Downloading %s" % version.url())
            rfile = sess.get(version.url(), stream=True)
            rfile.raise_for_status()
            with open(jarFilepath, 'wb') as f:
                for chunk in rfile.iter_content(chunk_size=128):
                    f.write(chunk)

    eprint ("Processing %s" % version.url())
    # harvestables from the installer
    if not os.path.isfile(profileFilepath):
        print(jarFilepath)
        with zipfile.ZipFile(jarFilepath, 'r') as jar:
            with suppress(KeyError):
                with jar.open('version.json', 'r') as profileZipEntry:
                    versionJsonData = profileZipEntry.read();
                    versionJsonJson = json.loads(versionJsonData)
                    profileZipEntry.close()

                    # Process: does it parse?
                    doesItParse = MojangVersionFile(versionJsonJson)

                    with open(versionJsonFilepath, 'wb') as versionJsonFile:
                        versionJsonFile.write(versionJsonData)
                        versionJsonFile.close()

            with jar.open('install_profile.json', 'r') as profileZipEntry:
                installProfileJsonData = profileZipEntry.read()
                profileZipEntry.close()

                # Process: does it parse?
                installProfileJsonJson = json.loads(installProfileJsonData)
                atLeastOneFormatWorked = False
                exception = None
                try:
                    doesItParseV1 = NeoforgeInstallerProfileV1(installProfileJsonJson)
                    atLeastOneFormatWorked = True
                except BaseException as err:
                    exception = err

                if not atLeastOneFormatWorked:
                    if version.isSupported():
                        raise exception
                    else:
                        eprint ("Version %s is not supported and won't be generated later." % version.longVersion)

                with open(profileFilepath, 'wb') as profileFile:
                    profileFile.write(installProfileJsonData)
                    profileFile.close()

    # installer info v1
    if not os.path.isfile(installerInfoFilepath):
        installerInfo = InstallerInfo()
        eprint ("SHA1 %s" % jarFilepath)
        installerInfo.sha1hash = filehash(jarFilepath, hashlib.sha1)
        eprint ("SHA256 %s" % jarFilepath)
        installerInfo.sha256hash = filehash(jarFilepath, hashlib.sha256)
        eprint ("SIZE %s" % jarFilepath)
        installerInfo.size = os.path.getsize(jarFilepath)
        eprint ("DUMP %s" % jarFilepath)
        with open(installerInfoFilepath, 'w', encoding='utf-8') as installerInfoFile:
            json.dump(installerInfo.to_json(), installerInfoFile, sort_keys=True, indent=4)
            installerInfoFile.close()

