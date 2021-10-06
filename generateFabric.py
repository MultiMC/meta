#!/usr/bin/python3
from fabricutil import *
from jsonobject import *
from datetime import datetime
from pprint import pprint
import os, copy

# turn loader versions into packages
loaderRecommended = []
loaderVersions = []
intermediaryRecommended = []
intermediaryVersions = []

def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

def loadJarInfo(mavenKey, variantName):
    with open(f"upstream/{variantName}/jars/" + mavenKey.replace(":", ".") + ".json", 'r', encoding='utf-8') as jarInfoFile:
        return FabricJarInfo(json.load(jarInfoFile))

def processLoaderVersion(loaderVersion, it, loaderData, variantName, variant):
    verStable = isFabricVerStable(loaderVersion)
    if (len(loaderRecommended) < 1) and verStable:
        loaderRecommended.append(loaderVersion)
    versionJarInfo = loadJarInfo(it["maven"], variantName)
    version = MultiMCVersionFile(name=variant["name"], uid=variant["loader_uid"], version=loaderVersion)
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid=variant["intermediary_uid"])]
    version.order = 10
    if verStable:
        version.type = "release"
    else:
        version.type = "snapshot"
    if isinstance(loaderData.mainClass, dict):
        version.mainClass = loaderData.mainClass["client"]
    else:
        version.mainClass = loaderData.mainClass
    version.libraries = []
    version.libraries.extend(loaderData.libraries.common)
    version.libraries.extend(loaderData.libraries.client)
    loaderLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url=variant["maven"])
    version.libraries.append(loaderLib)
    loaderVersions.append(version)

def processIntermediaryVersion(it, variantName, variant):
    intermediaryRecommended.append(it["version"])
    versionJarInfo = loadJarInfo(it["maven"], variantName)
    version = MultiMCVersionFile(name="Intermediary Mappings", uid=variant["intermediary_uid"], version=it["version"])
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.minecraft', equals=it["version"])]
    version.order = 11
    version.type = "release"
    version.libraries = []
    version.volatile = True
    mappingLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url=variant["maven"])
    version.libraries.append(mappingLib)
    intermediaryVersions.append(version)

for variantName, variant in variants.items():
    print(f"--- {variantName} ---")

    loaderRecommended.clear()
    loaderVersions.clear()
    intermediaryRecommended.clear()
    intermediaryVersions.clear()

    mkdirs(f"multimc/{variant['loader_uid']}")
    mkdirs(f"multimc/{variant['intermediary_uid']}")

    print("Processing loader versions...")
    with open(f"upstream/{variantName}/meta-v2/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
        loaderVersionIndex = json.load(loaderVersionIndexFile)
        for it in loaderVersionIndex:
            if "name" in it and it["name"] in variant["exclude"]:
                continue

            version = it["version"]
            print(f"Processing {version}...")
            with open(f"upstream/{variantName}/loader-installer-json/" + version + ".json", 'r', encoding='utf-8') as loaderVersionFile:
                ldata = json.load(loaderVersionFile)
                ldata = FabricInstallerDataV1(ldata)
                processLoaderVersion(version, it, ldata, variantName, variant)

    print("Processing Intermediary versions...")
    with open(f"upstream/{variantName}/meta-v2/intermediary.json", 'r', encoding='utf-8') as intermediaryVersionIndexFile:
        intermediaryVersionIndex = json.load(intermediaryVersionIndexFile)
        for it in intermediaryVersionIndex:
            print(f"Processing {it['version']}...")
            processIntermediaryVersion(it, variantName, variant)

    print("Writing loader versions...")
    for version in loaderVersions:
        print(f"Writing {version.version}...")
        outFilepath = f"multimc/{variant['loader_uid']}/%s.json" % version.version
        with open(outFilepath, 'w') as outfile:
            json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

    print("Writing shared loader data...")
    sharedData = MultiMCSharedPackageData(uid = variant["loader_uid"], name = variant["name"])
    sharedData.recommended = loaderRecommended
    sharedData.description = variant["description"]
    sharedData.projectUrl = variant["url"]
    sharedData.authors = variant["authors"]
    sharedData.write()

    print("Writing Intermediary versions...")
    for version in intermediaryVersions:
        print(f"Writing {version.version}...")
        outFilepath = f"multimc/{variant['intermediary_uid']}/%s.json" % version.version
        with open(outFilepath, 'w') as outfile:
            json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

    print("Writing shared Intermediary data...")
    sharedData = MultiMCSharedPackageData(uid = variant["intermediary_uid"], name = 'Intermediary Mappings')
    sharedData.recommended = intermediaryRecommended
    sharedData.description = "Intermediary mappings allow using Fabric Loader with mods for Minecraft in a more compatible manner."
    sharedData.projectUrl = variant["url"]
    sharedData.authors = variant["authors"]
    sharedData.write()
