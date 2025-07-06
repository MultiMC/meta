#!/usr/bin/python3

import os
import json
import copy
import datetime
import iso8601

from operator import itemgetter

from pprint import pprint

from metautil import *

from pkg_resources import parse_version

from collections import defaultdict
from collections import namedtuple
from datetime import datetime
import hashlib

def addOrGetBucket(buckets, rules):
    ruleHash = None
    if rules:
        ruleHash = hash(json.dumps(rules.to_json()))

    bucket = None
    if ruleHash in buckets:
        bucket = buckets[ruleHash]
    else:
        bucket = MultiMCVersionFile(
            {
                "name": "LWJGL",
                "version": "undetermined",
                "uid": "org.lwjgl"
            }
        )
        bucket.type = "release"
        buckets[ruleHash] = bucket
    return bucket

def hashVersion(lwjgl):
    lwjglObjectCopy = copy.deepcopy(lwjgl)
    lwjglObjectCopy.releaseTime = datetime.fromtimestamp(0)
    return hashlib.sha1(json.dumps(lwjglObjectCopy.to_json()).encode("utf-8", "strict")).hexdigest()

def sort_libs_by_name(library):
    return library.name

LWJGLEntry = namedtuple('LWJGLEntry', ('version', 'sha1'))

lwjglVersionVariants = defaultdict(list)

def addLWJGLVersion(versionVariants, lwjglObject):
    lwjglObjectCopy = copy.deepcopy(lwjglObject)
    libraries = list(lwjglObjectCopy.libraries)
    libraries.sort(key=sort_libs_by_name)
    lwjglObjectCopy.libraries = libraries

    lwjglVersion = lwjglObjectCopy.version
    lwjglObjectHash = hashVersion(lwjglObjectCopy)
    found = False
    for variant in versionVariants[lwjglVersion]:
        existingHash = variant.sha1
        if lwjglObjectHash == existingHash:
            found = True
            break
    if not found:
        print("!!! New variant for LWJGL version %s" % (lwjglVersion))
        versionVariants[lwjglVersion].append(LWJGLEntry(version=lwjglObjectCopy, sha1=lwjglObjectHash))

def removePathsFromLib(lib):
    if lib.downloads.artifact:
        lib.downloads.artifact.path = None
    if lib.downloads.classifiers:
        for key, value in lib.downloads.classifiers.items():
            value.path = None

def adaptNewStyleArguments(arguments):
    outarr = []
    # we ignore the jvm arguments entirely.
    # grab the strings, log the complex stuff
    for arg in arguments.game:
        if isinstance(arg, str):
            if arg == '--clientId':
                continue
            if arg == '${clientid}':
                continue
            if arg == '--xuid':
                continue
            if arg == '${auth_xuid}':
                continue
            outarr.append(arg)
        else:
            print("!!! Unrecognized structure in Minecraft game arguments:")
            pprint(arg)
    return ' '.join(outarr)

def isOnlyOS(rules, specifier, osName):
    allowsOS = False
    allowsAll = False
    #print("Considering", specifier, "rules", rules)
    if rules:
        for rule in rules:
            if rule.action == "allow" and rule.os and rule.os.name == osName:
                allowsOS = True
            if rule.action == "allow" and not rule.os:
                allowsAll = True
        if allowsOS and not allowsAll:
            return True
    return False


# get the local version list
staticVersionlist = None
with open("static/minecraft.json", 'r', encoding='utf-8') as legacyIndexFile:
    staticVersionlist = LegacyOverrideIndex(json.load(legacyIndexFile))

found_any_lwjgl3 = False

def processVersionWithSerparateLWJGL(versionFile):
    libs_minecraft = []
    is_lwjgl_3 = False
    buckets = {}
    for lib in versionFile.libraries:
        mmcLib = MultiMCLibrary(lib.to_json())
        removePathsFromLib(mmcLib)
        specifier = mmcLib.name
        ruleHash = None
        if specifier.isLwjgl():
            rules = None
            if mmcLib.rules:
                rules = mmcLib.rules
                mmcLib.rules = None
            if isOnlyOS(rules, specifier, "osx"):
                print("Candidate library ",  specifier, " is only for macOS and is therefore ignored.")
                continue
            if isOnlyOS(rules, specifier, "windows"):
                print("Candidate library ",  specifier, " is only for Windows and is therefore ignored.")
                continue
            if isOnlyOS(rules, specifier, "linux"):
                print("Candidate library ",  specifier, " is only for Linux and is therefore ignored.")
                continue
            bucket = addOrGetBucket(buckets, rules)
            if specifier.group == "org.lwjgl.lwjgl" and specifier.artifact == "lwjgl":
                bucket.version = specifier.version
            if specifier.group == "org.lwjgl" and specifier.artifact == "lwjgl":
                is_lwjgl_3 = True
                found_any_lwjgl3 = True
                bucket.version = specifier.version
            if not bucket.libraries:
                bucket.libraries = []
            bucket.libraries.append(mmcLib)
            bucket.releaseTime = versionFile.releaseTime
        else:
            # FIXME: workaround for insane log4j nonsense from December 2021. Probably needs adjustment.
            if mmcLib.name.isLog4j():
                if parse_version(mmcLib.name.version) >= parse_version("2.16.0"):
                    libs_minecraft.append(mmcLib)
                else:
                    print("Bad log4j detected")
                    log4jVersion = '2.16.0'
                    if mmcLib.name.version == '2.0-beta9':
                        log4jVersion = '2.0-beta9-fixed'

                    replacementLib = MultiMCLibrary(name=GradleSpecifier("org.apache.logging.log4j:%s:%s" % (mmcLib.name.artifact, log4jVersion)))
                    replacementLib.downloads = MojangLibraryDownloads()
                    replacementLib.downloads.artifact = MojangArtifact()
                    replacementLib.downloads.artifact.url = "https://files.multimc.org/maven/%s" % (replacementLib.name.getPath())

                    if log4jVersion == "2.16.0":
                        if mmcLib.name.artifact == "log4j-api":
                            replacementLib.downloads.artifact.sha1 = "f821a18687126c2e2f227038f540e7953ad2cc8c"
                            replacementLib.downloads.artifact.size = 301892
                        elif mmcLib.name.artifact == "log4j-core":
                            replacementLib.downloads.artifact.sha1 = "539a445388aee52108700f26d9644989e7916e7c"
                            replacementLib.downloads.artifact.size = 1789565
                        elif mmcLib.name.artifact == "log4j-slf4j18-impl":
                            replacementLib.downloads.artifact.sha1 = "0c880a059056df5725f5d8d1035276d9749eba6d"
                            replacementLib.downloads.artifact.size = 21249
                        else:
                            raise Exception("ERROR: unhandled log4j artifact %s!" % mmcLib.name.artifact)
                    elif log4jVersion == "2.0-beta9-fixed":
                        if mmcLib.name.artifact == "log4j-api":
                            replacementLib.downloads.artifact.sha1 = "b61eaf2e64d8b0277e188262a8b771bbfa1502b3"
                            replacementLib.downloads.artifact.size = 107347
                        elif mmcLib.name.artifact == "log4j-core":
                            replacementLib.downloads.artifact.sha1 = "677991ea2d7426f76309a73739cecf609679492c"
                            replacementLib.downloads.artifact.size = 677588
                        else:
                            raise Exception("ERROR: unhandled log4j artifact %s!" % mmcLib.name.artifact)
                    libs_minecraft.append(replacementLib)
            else:
                libs_minecraft.append(mmcLib)
    if len(buckets) == 1:
        for key in buckets:
            keyBucket = buckets[key]
            keyBucket.libraries = sorted(keyBucket.libraries, key=itemgetter('name'))
            addLWJGLVersion(lwjglVersionVariants, keyBucket)
            print("Found only candidate LWJGL", keyBucket.version, key)
    else:
        # multiple buckets for LWJGL. [None] is common to all, other keys are for different sets of rules
        for key in buckets:
            if key == None:
                continue
            keyBucket = buckets[key]
            if None in buckets:
                keyBucket.libraries = sorted(keyBucket.libraries + buckets[None].libraries, key=itemgetter('name'))
            else:
                keyBucket.libraries = sorted(keyBucket.libraries, key=itemgetter('name'))
            addLWJGLVersion(lwjglVersionVariants, keyBucket)
            print("Found candidate LWJGL", keyBucket.version, key)
        # remove the common bucket...
        if None in buckets:
            del buckets[None]
    versionFile.libraries = libs_minecraft
    depentry = None

    if is_lwjgl_3:
        depentry = DependencyEntry(uid='org.lwjgl3')
    else:
        depentry = DependencyEntry(uid='org.lwjgl')
    if len(buckets) == 1:
        suggestedVersion = next(iter(buckets.values())).version
        # HACK: forcing hard dependencies here for now... the UI doesn't know how to filter by this and it looks odd, but it works
        if is_lwjgl_3:
            depentry.suggests = suggestedVersion
            depentry.equals = suggestedVersion
        else:
            depentry.suggests = '2.9.4-nightly-20150209'
    else:
        badVersions1 = {'3.1.6', '3.2.1'}
        ourVersions = set()

        for lwjgl in iter(buckets.values()):
            ourVersions = ourVersions.union({lwjgl.version})

        if ourVersions == badVersions1:
            print("Found broken 3.1.6/3.2.1 combo, forcing LWJGL to 3.2.1")
            suggestedVersion = '3.2.1'
            depentry.suggests = suggestedVersion
        else:
            raise Exception("ERROR: cannot determine single suggested LWJGL version in %s" % mojangVersionFile.id)

    # if it uses LWJGL 3, add the trait that enables starting on first thread on macOS
    if is_lwjgl_3:
        if not versionFile.addTraits:
            versionFile.addTraits = []
        versionFile.addTraits.append("FirstThreadOnMacOS")
    versionFile.requires = [depentry]
    versionFile.order = -2
    # process 1.13 arguments into previous version
    if not mojangVersionFile.minecraftArguments and mojangVersionFile.arguments:
        versionFile.minecraftArguments = adaptNewStyleArguments(mojangVersionFile.arguments)
    filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
    if versionFile.version in staticVersionlist.versions:
        ApplyLegacyOverride (versionFile, staticVersionlist.versions[versionFile.version])
    with open(filenameOut, 'w') as outfile:
        json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

def processVersionWithMergedLWJGL(versionFile):
    filenameOut = "multimc/net.minecraft/%s.json" % versionFile.version
    versionFile.addTraits.append("FirstThreadOnMacOS")
    versionFile.minecraftArguments = adaptNewStyleArguments(mojangVersionFile.arguments)
    with open(filenameOut, 'w') as outfile:
        json.dump(versionFile.to_json(), outfile, sort_keys=True, indent=4)

for filename in os.listdir('upstream/mojang/versions'):
    with open("upstream/mojang/versions/" + filename) as json_file:
        print("Processing", filename)
        mojangVersionFile = MojangVersionFile(json.load(json_file))
        versionFile = MojangToMultiMC(mojangVersionFile, "Minecraft", "net.minecraft", mojangVersionFile.id)
        if versionFile.releaseTime < iso8601.parse_date("2023-08-30T11:24:35+00:00"):
            print("Processing with separate LWJGL:", filename)
            processVersionWithSerparateLWJGL(versionFile)
        else:
            print("Processing with merged LWJGL:", filename)
            processVersionWithMergedLWJGL(versionFile)


def processSingleVariant(lwjglVariant):
    lwjglVersion = lwjglVariant.version
    versionObj = copy.deepcopy(lwjglVariant)
    if lwjglVersion[0] == '2':
        filename = "multimc/org.lwjgl/%s.json" % lwjglVersion
        versionObj.name = 'LWJGL 2'
        versionObj.uid = 'org.lwjgl'
        versionObj.conflicts = [DependencyEntry(uid='org.lwjgl3')]
    elif lwjglVersion[0] == '3':
        filename = "multimc/org.lwjgl3/%s.json" % lwjglVersion
        versionObj.name = 'LWJGL 3'
        versionObj.uid = 'org.lwjgl3'
        versionObj.conflicts = [DependencyEntry(uid='org.lwjgl')]
        # remove jutils and jinput from LWJGL 3 -- this is a dependency that Mojang kept in, but doesn't belong there anymore
        filteredLibraries = list(filter(lambda lib: not lib.name.artifact in ["jutils", "jinput"], versionObj.libraries))
        versionObj.libraries = filteredLibraries
    else:
        raise Exception("LWJGL version not recognized: %s" % versionObj.version)

    versionObj.volatile = True
    versionObj.order = -1
    good = True
    for lib in versionObj.libraries:
        if not lib.natives:
            continue
        checkedDict = {'linux', 'windows', 'osx'}
        if not checkedDict.issubset(lib.natives.keys()):
            print("Missing system classifier!", versionObj.version, lib.name, lib.natives.keys())
            good = False
            break
        if lib.downloads:
            for entry in checkedDict:
                bakedEntry = lib.natives[entry]
                if not bakedEntry in lib.downloads.classifiers:
                    print("Missing download for classifier!", versionObj.version, lib.name, bakedEntry, lib.downloads.classifiers.keys())
                    good = False
                    break
    if good:
        with open(filename, 'w') as outfile:
            json.dump(versionObj.to_json(), outfile, sort_keys=True, indent=4)
    else:
        print("Skipped LWJGL", versionObj.version)


passVariants = [
    "dc788960f7e74062aee7cee0e1e7d0a14c342418", # 2.9.0
    "cc1241e6cc967857961c7385ba078242d866d896", # 2.9.1
    "569845af361b8cd54de7153c142053425944da57", # 2.9.1-nightly-20131120
    "838930186ce1f4222f71b737ee17725d0fd14e5a", # 2.9.3
    "079b297aa801e551cc96b5e06c44e4a921807c8a", # 2.9.4-nightly-20150209
    "ac1d55d1e61bab404746f2a5a46baf8aac2a6c04", # 3.1.2
    "30e698945af19139b38cb6d15b8fbd52df492df6", # 3.1.6
    "399028b2274897c0c0b15a1ae48882e29b47111a", # 3.2.1
    "15d5562e9a3d11edec17c8e2de084a96fe9f371d", # 3.2.2 - our fixed version
    "b17498f09fd1fc3343d4652305268493331f81c4", # 3.3.1
]

badVariants = [
    "032bfe9afc34cf1271037f734a6e7a8835fdfff0", # 2.9.0 - duplication nation
    "859f5679c60fce520a7c8cfe0c5663f848ff51ab", # 2.9.0 - broken natives
    "7811cd3ba93467842b1823ca8e571f3d49421291", # 3.1.6
    "194e5109cbdfb8d5a7da918c449b7414cd609629", # 3.2.1
    "18cd83db93dda6e452775962a5590486d54c505d", # 3.2.1 - missing linux natives
    "74f2ae137e9767f0cfbe10ca9db38adaba08a4a6", # 3.2.2 - missing tinyfd
    "eaeeca768920d981bdc8ea698305f4e9723c6ba8", # 3.2.2 - missing osx natives
    "80104df786febbb139bf456d820494de3d594d94", # 3.2.2 - also missing osx natives
    "8a85feb57480e9cbb0b9c54e7b1751816122cf97", # 3.2.2 - missing other osx natives
    "65d4ba873bc1244fda9fd7fabd5f6d917316a4e8", # 3.2.2 - introduced in 21w42a, missing jinput and jutils
    "2bc9e4c3a40dbde9f1eafa17592e2d9a2c71cc20", # 3.2.2 - whatever mad thing that happened recently
    "6b8dc232a0e58f2f48cfb0df9bc6eb046245d93e", # 3.2.2 - format change?
    "cffcac1b048962f5d03492c86b2452d294947e5b", # 3.3.1 - missing all the natives because of single OS rule filtering them out. TODO: fix for ARM support
    "bf013b99ff09b22e8c275b9cbd2d5734db1c5743", # 3.3.1 - previous good one, but failed now
]

# Add our own 3.2.2, with hookers and blackjack.
with open("static/lwjgl-3.2.2.json", 'r', encoding='utf-8') as lwjgl322file:
    lwjgl322 = MultiMCVersionFile(json.load(lwjgl322file))
    addLWJGLVersion(lwjglVersionVariants, lwjgl322)

for lwjglVersionVariant in lwjglVersionVariants:
    decidedVariant = None
    passedVariants = 0
    unknownVariants = 0
    print("%d variant(s) for LWJGL %s:" % (len(lwjglVersionVariants[lwjglVersionVariant]), lwjglVersionVariant))

    for variant in lwjglVersionVariants[lwjglVersionVariant]:
        if variant.sha1 in badVariants:
            print("Variant %s ignored because it's marked as bad." % (variant.sha1))
            continue
        if variant.sha1 in passVariants:
            print("Variant %s accepted." % (variant.sha1))
            decidedVariant = variant
            passedVariants += 1
            continue

        print("Variant %s:" % (variant.sha1))
        print(json.dumps(variant.version.to_json(), sort_keys=True, indent=4))
        print("")
        unknownVariants += 1
    print("")

    if decidedVariant and passedVariants == 1 and unknownVariants == 0:
        processSingleVariant(decidedVariant.version)
    else:
        raise Exception("No variant decided for version %s out of %d possible ones and %d unknown ones." % (lwjglVersionVariant, passedVariants, unknownVariants))

lwjglSharedData = MultiMCSharedPackageData(uid = 'org.lwjgl', name = 'LWJGL 2')
lwjglSharedData.recommended = ['2.9.4-nightly-20150209']
lwjglSharedData.write()

if found_any_lwjgl3:
    lwjglSharedData = MultiMCSharedPackageData(uid = 'org.lwjgl3', name = 'LWJGL 3')
    lwjglSharedData.recommended = ['3.1.2']
    lwjglSharedData.write()

with open("upstream/mojang/version_manifest_v2.json", 'r', encoding='utf-8') as localIndexFile:
    localVersionlist = MojangIndexWrap(json.load(localIndexFile))

mcSharedData = MultiMCSharedPackageData(uid = 'net.minecraft', name = 'Minecraft')
mcSharedData.recommended = [localVersionlist.latest['release']]
mcSharedData.write()
