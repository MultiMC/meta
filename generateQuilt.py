#!/usr/bin/python3
from quiltutil import *
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

mkdirs("multimc/org.quiltmc.quilt-loader")
mkdirs("multimc/org.quiltmc.intermediary")

def loadJarInfo(mavenKey):
    with open("upstream/quilt/jars/" + mavenKey.replace(":", ".") + ".json", 'r', encoding='utf-8') as jarInfoFile:
        return QuiltJarInfo(json.load(jarInfoFile))

def processLoaderVersion(loaderVersion, it, loaderData):
    verStable = isQuiltVerStable(loaderVersion)
    if (len(loaderRecommended) < 1) and verStable:
        loaderRecommended.append(loaderVersion)
    versionJarInfo = loadJarInfo(it["maven"])
    version = MultiMCVersionFile(name="Quilt Loader", uid="org.quiltmc.quilt-loader", version=loaderVersion)
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='org.quiltmc.intermediary')]
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
    loaderLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.quiltmc.org/repository/release/")
    version.libraries.append(loaderLib)
    loaderVersions.append(version)

def processIntermediaryVersion(it):
    intermediaryRecommended.append(it["version"])
    versionJarInfo = loadJarInfo(it["maven"])
    version = MultiMCVersionFile(name="Intermediary Mappings", uid="org.quiltmc.intermediary", version=it["version"])
    version.releaseTime = versionJarInfo.releaseTime
    version.requires = [DependencyEntry(uid='net.minecraft', equals=it["version"])]
    version.order = 11
    version.type = "release"
    version.libraries = []
    version.volatile = True
    mappingLib = MultiMCLibrary(name=GradleSpecifier(it["maven"]), url="https://maven.quiltmc.org/repository/release/")
    version.libraries.append(mappingLib)
    intermediaryVersions.append(version)

with open("upstream/quilt/meta-v3/loader.json", 'r', encoding='utf-8') as loaderVersionIndexFile:
    loaderVersionIndex = json.load(loaderVersionIndexFile)
    for it in loaderVersionIndex:
        version = it["version"]
        with open("upstream/quilt/loader-installer-json/" + version + ".json", 'r', encoding='utf-8') as loaderVersionFile:
            ldata = json.load(loaderVersionFile)
            ldata = QuiltInstallerDataV1(ldata)
            processLoaderVersion(version, it, ldata)

with open("upstream/quilt/meta-v3/intermediary.json", 'r', encoding='utf-8') as intermediaryVersionIndexFile:
    intermediaryVersionIndex = json.load(intermediaryVersionIndexFile)
    for it in intermediaryVersionIndex:
        processIntermediaryVersion(it)

for version in loaderVersions:
    outFilepath = "multimc/org.quiltmc.quilt-loader/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = MultiMCSharedPackageData(uid = 'org.quiltmc.quilt-loader', name = 'Quilt Loader')
sharedData.recommended = loaderRecommended
sharedData.description = "Quilt Loader is a tool to load Quilt-compatible mods in game environments."
sharedData.projectUrl = "https://quiltmc.org"
sharedData.authors = ["Quilt Developers"]
sharedData.write()

for version in intermediaryVersions:
    outFilepath = "multimc/org.quiltmc.intermediary/%s.json" % version.version
    with open(outFilepath, 'w') as outfile:
        json.dump(version.to_json(), outfile, sort_keys=True, indent=4)

sharedData = MultiMCSharedPackageData(uid = 'org.quiltmc.intermediary', name = 'Intermediary Mappings')
sharedData.recommended = intermediaryRecommended
sharedData.description = "Intermediary mappings allow using Quilt Loader with mods for Minecraft in a more compatible manner."
sharedData.projectUrl = "https://quiltmc.org"
sharedData.authors = ["Quilt Developers"]
sharedData.write()
