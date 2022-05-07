#!/usr/bin/python3
from fabricutil import *
from jsonobject import *
from datetime import datetime
from pprint import pprint
import os, copy

# turn loader versions into packages
loaderRecommended = {}
loaderVersions = {}
intermediaryRecommended = {}
intermediaryVersions = {}
kinds = ["fabricmc","legacy-fabric"]
for i in kinds:
    i = i.replace("-", "")
    loaderRecommended[i] = []
    loaderVersions[i] = []
    intermediaryRecommended[i] = []
    intermediaryVersions[i] = []

def mkdirs(path):
    if not os.path.exists(path):
        os.makedirs(path)

mkdirs("multimc/net.fabricmc.fabric-loader")
mkdirs("multimc/net.fabricmc.intermediary")

mkdirs("multimc/net.legacyfabric.fabric-loader")
mkdirs("multimc/net.legacyfabric.intermediary")

def loadJarInfo(mavenKey):
    with open("upstream/fabric/jars/" + mavenKey.replace(":", ".") + ".json", 'r', encoding='utf-8') as jarInfoFile:
        return FabricJarInfo(json.load(jarInfoFile))

def processLoaderVersion(loaderVersion, it, loaderData, kind):
    verStable = it["stable"]
    if (len(loaderRecommended) < 1) and verStable:
        loaderRecommended[kind].append(loaderVersion)
    versionJarInfo = loadJarInfo(it["maven"])
    version = MultiMCVersionFile(name="Fabric Loader", uid="net." + kind + ".fabric-loader", version=loaderVersion)
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net." + kind " .intermediary')]
    version.order = 10
    version.type = "release"
    if isinstance(loaderData.mainClass, dict):
        version.mainClass = loaderData.mainClass["client"]
    else:
        version.mainClass = loaderData.mainClass
    version.libraries = []
    version.libraries.extend(loaderData.libraries.common)
    version.libraries.extend(loaderData.libraries.client)
    loaderLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.fabricmc.net")
    version.libraries.append(loaderLib)
    loaderVersions[kind].append(version)

def processIntermediaryVersion(it, kind):
    intermediaryRecommended[kind].append(it["version"])
    versionJarInfo = loadJarInfo(it["maven"])
    version = MultiMCVersionFile(name="Intermediary Mappings", uid="net." + kind + ".intermediary", version=it["version"])
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.minecraft', equals=it["version"])]
    version.order = 11
    version.type = "release"
    version.libraries = []
    version.volatile = True
    mappingLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven." + kind + ".net")
    version.libraries.append(mappingLib)
    intermediaryVersions[kind].append(version)

for i in kinds:
    j = i.replace("mc","")
    i = i.replace("-","")
    with open("upstream/" + j + "/meta-v2/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
        loaderVersionIndex = json.load(loaderVersionIndexFile)
        for it in loaderVersionIndex:
            version = it["version"]
            with open("upstream/fabric/loader-installer-json/" + version + ".json", 'r', encoding='utf-8') as loaderVersionFile:
                ldata = json.load(loaderVersionFile)
                ldata = FabricInstallerDataV1(ldata)
                processLoaderVersion(version, it, ldata, i)

    with open("upstream/" + j + "/meta-v2/intermediary.json", 'r', encoding='utf-8') as intermediaryVersionIndexFile:
        intermediaryVersionIndex = json.load(intermediaryVersionIndexFile)
        for it in intermediaryVersionIndex:
            processIntermediaryVersion(it, i)

    for version in loaderVersions[i]:
        outFilepath = "multimc/net." + i + ".fabric-loader/%s.json" % version.version
        with open(outFilepath, 'w') as outfile:
            json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

    sharedData = MultiMCSharedPackageData(uid = 'net.fabricmc.fabric-loader', name = 'Fabric Loader')
    sharedData.recommended = loaderRecommended
    sharedData.description = "Fabric Loader is a tool to load Fabric-compatible mods in game environments."
    sharedData.projectUrl = "https://fabricmc.net"
    sharedData.authors = ["Fabric Developers"]
    sharedData.write()

    for version in intermediaryVersions:
        outFilepath = "multimc/net." + i + ".intermediary/%s.json" % version.version
        with open(outFilepath, 'w') as outfile:
            json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

    sharedData = MultiMCSharedPackageData(uid = 'net.' + i + '.intermediary', name = 'Intermediary Mappings')
    sharedData.recommended = intermediaryRecommended
    sharedData.description = "Intermediary mappings allow using Fabric Loader with mods for Minecraft in a more compatible manner."
    sharedData.projectUrl = "https://" + i + ".net"
    sharedData.authors = ["Fabric Developers"]
    sharedData.write()
