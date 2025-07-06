#!/usr/bin/python3
from __future__ import print_function
import sys
import os
import re
from metautil import *
from forgeutil import *
from jsonobject import *
from distutils.version import LooseVersion

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# Contruct a set of libraries out of a Minecraft version file, for filtering.
mcVersionCache = {}
def loadMcVersionFilter(version):
    if version in mcVersionCache:
        return mcVersionCache[version]
    libSet = set()
    with open("multimc/net.minecraft/%s.json" % version, 'r', encoding='utf-8') as mcFile:
        mcVersion = MultiMCVersionFile(json.load(mcFile))
        for lib in mcVersion.libraries:
            libSet.add(lib.name)
        mcVersionCache[version] = libSet
        return libSet

'''
Match a library coordinate to a set of library coordinates.
 * Block those that pass completely.
 * For others, block those with lower versions than in the set.
'''
def shouldIgnoreArtifact(libSet, match):
    for ver in libSet:
        if ver.group == match.group and ver.artifact == match.artifact and ver.classifier == match.classifier:
            if ver.version == match.version:
                # Everything is matched perfectly - this one will be ignored
                return True
            else:
                # We say the lib matches (is the same) also when the new version is lower than the old one
                if LooseVersion(ver.version) > LooseVersion(match.version):
                    # eprint ("Lower version on %s:%s:%s: OLD=%s NEW=%s" % (ver.group, ver.artifact, ver.classifier, ver.version, match.version))
                    return True
                # Otherwise it did not match - new version is higher and this is an upgrade
                return False
    # No match found in the set - we need to keep this
    return False

def versionFromProfile(profile, version):
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    mcversion = profile.install.minecraft
    result.requires = [DependencyEntry(uid='net.minecraft', equals=mcversion)]
    result.mainClass = profile.versionInfo.mainClass
    args = profile.versionInfo.minecraftArguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9\\.]+)")
    match = expression.search(args)
    while match != None:
        tweakers.append(match.group(1));
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args);
    if len(tweakers) > 0:
        args = args.strip()
        result.addTweakers = tweakers;
    # result.minecraftArguments = args
    result.releaseTime = profile.versionInfo.time
    libs = []
    mcFilter = loadMcVersionFilter(mcversion)
    for forgeLib in profile.versionInfo.libraries:
        if forgeLib.name.isLwjgl():
            continue
        if forgeLib.name.isLog4j():
            continue
        if shouldIgnoreArtifact(mcFilter, forgeLib.name):
            continue
        fixedName = forgeLib.name
        if fixedName.group == "net.minecraftforge":
            if fixedName.artifact == "minecraftforge":
                fixedName.artifact = "forge"
                fixedName.classifier = "universal"
                fixedName.version = "%s-%s" % (mcversion, fixedName.version)
            elif fixedName.artifact == "forge":
                fixedName.classifier = "universal"
        ourLib = MultiMCLibrary(name=fixedName)
        if forgeLib.url == "http://files.minecraftforge.net/maven/":
            ourLib.url = "https://maven.minecraftforge.net/"
        else:
            ourLib.url = forgeLib.url
        #if forgeLib.checksums and len(forgeLib.checksums) == 2:
        #    ourLib.mmcHint = "forge-pack-xz"
        libs.append(ourLib)
    result.libraries = libs
    result.order = 5
    return result

def versionFromModernizedInstaller(installerVersion : MojangVersionFile, version: ForgeVersion):
    eprint("Generating Modernized Forge %s." % version.longVersion)
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    mcversion = version.mcversion
    result.requires = [DependencyEntry(uid='net.minecraft', equals=mcversion)]
    result.mainClass = installerVersion.mainClass
    args = installerVersion.minecraftArguments
    tweakers = []
    expression = re.compile("--tweakClass ([a-zA-Z0-9\\.]+)")
    match = expression.search(args)
    while match != None:
        tweakers.append(match.group(1));
        args = args[:match.start()] + args[match.end():]
        match = expression.search(args);
    if len(tweakers) > 0:
        args = args.strip()
        result.addTweakers = tweakers;
    # result.minecraftArguments = args
    result.releaseTime = installerVersion.releaseTime
    libs = []
    mcFilter = loadMcVersionFilter(mcversion)
    for upstreamLib in installerVersion.libraries:
        mmcLib = MultiMCLibrary(upstreamLib.to_json())
        if mmcLib.name.isLwjgl():
            continue
        if mmcLib.name.isLog4j():
            continue
        if shouldIgnoreArtifact(mcFilter, mmcLib.name):
            continue
        if mmcLib.name.group == "net.minecraftforge":
            if mmcLib.name.artifact == "forge":
                fixedName = mmcLib.name
                fixedName.classifier = "universal"
                mmcLib.downloads.artifact.path = fixedName.getPath()
                mmcLib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % fixedName.getPath()
                mmcLib.name = fixedName
                libs.append(mmcLib)
                continue
            elif mmcLib.name.artifact == "minecraftforge":
                fixedName = mmcLib.name
                fixedName.artifact = "forge"
                fixedName.classifier = "universal"
                fixedName.version = "%s-%s" % (mcversion, fixedName.version)
                mmcLib.downloads.artifact.path = fixedName.getPath()
                mmcLib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % fixedName.getPath()
                mmcLib.name = fixedName
                libs.append(mmcLib)
                continue
        libs.append(mmcLib)

    result.libraries = libs
    result.order = 5
    return result

def versionFromLegacy(version, legacyinfo : ForgeLegacyInfo):
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    mcversion = version.mcversion_sane
    result.requires = [DependencyEntry(uid='net.minecraft', equals=mcversion)]
    result.releaseTime = legacyinfo.releaseTime
    result.order = 5
    if mcversion in fmlLibsMapping:
        result.addTraits = ["legacyFML"]
    url = version.url()
    classifier = None
    if "universal" in url:
        classifier = "universal"
    else:
        classifier = "client"
    coord = GradleSpecifier("net.minecraftforge:forge:%s:%s" % (version.longVersion,classifier))
    mainmod = MultiMCLibrary(name = coord)
    mainmod.downloads = MojangLibraryDownloads()
    mainmod.downloads.artifact = MojangArtifact()
    mainmod.downloads.artifact.path = None
    mainmod.downloads.artifact.url = version.url()
    mainmod.downloads.artifact.sha1 = legacyinfo.sha1
    mainmod.downloads.artifact.size = legacyinfo.size
    result.jarMods = [mainmod]
    return result

def versionFromBuildSystemInstaller(installerVersion : MojangVersionFile, installerProfile: ForgeInstallerProfileV2, version: ForgeVersion):
    eprint("Generating Forge %s." % version.longVersion)
    result = MultiMCVersionFile({"name":"Forge", "version":version.rawVersion, "uid":"net.minecraftforge" })
    result.requires = [DependencyEntry(uid='net.minecraft', equals=version.mcversion_sane)]
    result.mainClass = "io.github.zekerzhayard.forgewrapper.installer.Main"

    # FIXME: Add the size and hash here
    mavenLibs = []

    # load the locally cached installer file info and use it to add the installer entry in the json
    with open("upstream/forge/installer_info/%s.json" % version.longVersion, 'r', encoding='utf-8') as f:
        installerInfo = InstallerInfo(json.load(f))
        InstallerLib = MultiMCLibrary(name=GradleSpecifier("net.minecraftforge:forge:%s:installer" % (version.longVersion)))
        InstallerLib.downloads = MojangLibraryDownloads()
        InstallerLib.downloads.artifact = MojangArtifact()
        InstallerLib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % (InstallerLib.name.getPath())
        InstallerLib.downloads.artifact.sha1 = installerInfo.sha1hash
        InstallerLib.downloads.artifact.size = installerInfo.size
        mavenLibs.append(InstallerLib)

    for upstreamLib in installerProfile.libraries:
        mmcLib = MultiMCLibrary(upstreamLib.to_json())
        if mmcLib.name.group == "net.minecraftforge":
            if mmcLib.name.artifact == "forge":
                if mmcLib.name.classifier == "universal":
                    mmcLib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % mmcLib.name.getPath()
                    mavenLibs.append(mmcLib)
                    continue
        if mmcLib.name.isLog4j():
            continue
        mavenLibs.append(mmcLib)

    result.mavenFiles = mavenLibs

    libraries = []

    # wrapperLib = MultiMCLibrary(name=GradleSpecifier("io.github.zekerzhayard:ForgeWrapper:mmc4"))
    # wrapperLib.downloads = MojangLibraryDownloads()
    # wrapperLib.downloads.artifact = MojangArtifact()
    # wrapperLib.downloads.artifact.url = "https://files.multimc.org/maven/%s" % (wrapperLib.name.getPath())
    # wrapperLib.downloads.artifact.sha1 = "9a7d2f13be2070525909f30a26f3832db611009a"
    # wrapperLib.downloads.artifact.size = 36203
    # libraries.append(wrapperLib)

    # wrapperLib = MultiMCLibrary(name=GradleSpecifier("io.github.zekerzhayard:ForgeWrapper:mmc5"))
    # wrapperLib.downloads = MojangLibraryDownloads()
    # wrapperLib.downloads.artifact = MojangArtifact()
    # wrapperLib.downloads.artifact.url = "https://files.multimc.org/maven/%s" % (wrapperLib.name.getPath())
    # wrapperLib.downloads.artifact.sha1 = "d82cb39636a5092a8e5b5de82ccfe5f7e70e8d49"
    # wrapperLib.downloads.artifact.size = 35390
    # libraries.append(wrapperLib)

    wrapperLib = MultiMCLibrary(name=GradleSpecifier("io.github.zekerzhayard:ForgeWrapper:mmc6"))
    wrapperLib.downloads = MojangLibraryDownloads()
    wrapperLib.downloads.artifact = MojangArtifact()
    wrapperLib.downloads.artifact.url = "https://files.multimc.org/maven/%s" % (wrapperLib.name.getPath())
    wrapperLib.downloads.artifact.sha1 = "8dfb7d1151a7260ecb7ab7c01ac362df80469261"
    wrapperLib.downloads.artifact.size = 28912
    libraries.append(wrapperLib)

    for upstreamLib in installerVersion.libraries:
        mmcLib = MultiMCLibrary(upstreamLib.to_json())
        if mmcLib.name.group == "net.minecraftforge":
            if mmcLib.name.artifact == "forge" and not mmcLib.name.classifier:
                fixedName = mmcLib.name
                fixedName.classifier = "launcher"
                mmcLib.downloads.artifact.path = fixedName.getPath()
                mmcLib.downloads.artifact.url = "https://maven.minecraftforge.net/%s" % fixedName.getPath()
                mmcLib.name = fixedName
                libraries.append(mmcLib)
                continue
        # forge 49.0.4+ sets an empty client download https://github.com/MinecraftForge/MinecraftForge/commit/5c15aa3322db8a3f95e97390638f80eb6d4e5d15
        # so we need clear the url to stop mmc from downloading it
        if not mmcLib.downloads.artifact.url and mmcLib.name.classifier == "client":
            continue
        if mmcLib.name.isLog4j():
            continue
        libraries.append(mmcLib)
    result.libraries = libraries

    result.releaseTime = installerVersion.releaseTime
    result.order = 5
    mcArgs = "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} --assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} --accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    for arg in installerVersion.arguments.game:
        mcArgs += " %s" % arg
    if "--fml.forgeVersion" not in installerVersion.arguments.game:
        mcArgs += " --fml.forgeVersion %s" % version.rawVersion
    if "--fml.mcVersion" not in installerVersion.arguments.game:
        mcArgs += " --fml.mcVersion %s" % version.mcversion
    if "--fml.forgeGroup" not in installerVersion.arguments.game:
        mcArgs += " --fml.forgeGroup net.minecraftforge"
    result.minecraftArguments = mcArgs
    return result


# load the locally cached version list
with open("upstream/forge/derived_index.json", 'r', encoding='utf-8') as f:
    main_json = json.load(f)
    remoteVersionlist = DerivedForgeIndex(main_json)

recommendedVersions = []

tsPath = "static/forge-legacyinfo.json"

legacyinfolist = None
with open(tsPath, 'r', encoding='utf-8') as tsFile:
    legacyinfolist = ForgeLegacyInfoList(json.load(tsFile))

legacyVersions = [
    "1.1",
    "1.2.3",
    "1.2.4",
    "1.2.5",
    "1.3.2",
    "1.4.1",
    "1.4.2",
    "1.4.3",
    "1.4.4",
    "1.4.5",
    "1.4.6",
    "1.4.7",
    "1.5",
    "1.5.1",
    "1.5.2",
    "1.6.1",
    "1.6.2",
    "1.6.3",
    "1.6.4",
    "1.7.10",
    "1.7.10-pre4",
    "1.7.2",
    "1.8",
    "1.8.8",
    "1.8.9",
    "1.9",
    "1.9.4",
    "1.10",
    "1.10.2",
    "1.11",
    "1.11.2",
    "1.12",
    "1.12.1",
    "1.12.2",
]

for id, entry in remoteVersionlist.versions.items():
    if entry.mcversion == None:
        eprint ("Skipping %s with invalid MC version" % id)
        continue

    version = ForgeVersion(entry)
    if version.url() == None:
        eprint ("Skipping %s with no valid files" % id)
        continue
    eprint ("Processing Forge %s" % version.rawVersion)
    versionElements = version.rawVersion.split('.')
    if len(versionElements) < 1:
        eprint ("Skipping version %s with not enough version elements" % (id))
        continue

    majorVersionStr = versionElements[0]
    if not majorVersionStr.isnumeric():
        eprint ("Skipping version %s with non-numeric major version %s" % (id, majorVersionStr))
        continue

    majorVersion = int(majorVersionStr)
    #if majorVersion >= 37:
    #    eprint ("Skipping unsupported major version %d (%s)" % (majorVersion, id))
    #    continue

    if entry.recommended:
        recommendedVersions.append(version.rawVersion)

    # If we do not have the corresponding Minecraft version, we ignore it
    if not os.path.isfile("multimc/net.minecraft/%s.json" % version.mcversion_sane):
        eprint ("Skipping %s with no corresponding Minecraft version %s" % (id, version.mcversion_sane))
        continue

    outVersion = None

    # Path for new-style build system based installers
    installerVersionFilepath = "upstream/forge/version_manifests/%s.json" % version.longVersion
    profileFilepath = "upstream/forge/installer_manifests/%s.json" % version.longVersion

    eprint(installerVersionFilepath)
    if os.path.isfile(installerVersionFilepath):
        with open(installerVersionFilepath, 'r', encoding='utf-8') as installerVersionFile:
            installerVersion = MojangVersionFile(json.load(installerVersionFile))
        if entry.mcversion in legacyVersions:
            outVersion = versionFromModernizedInstaller(installerVersion, version)
        else:
            with open(profileFilepath, 'r', encoding='utf-8') as profileFile:
                installerProfile = ForgeInstallerProfileV2(json.load(profileFile))
            outVersion = versionFromBuildSystemInstaller(installerVersion, installerProfile, version)
    else:
        if version.usesInstaller():

            # If we do not have the Forge json, we ignore this version
            if not os.path.isfile(profileFilepath):
                eprint ("Skipping %s with missing profile json" % id)
                continue
            with open(profileFilepath, 'r', encoding='utf-8') as profileFile:
                profile = ForgeInstallerProfile(json.load(profileFile))
                outVersion = versionFromProfile(profile, version)
        else:
            # Generate json for legacy here
            if version.mcversion_sane == "1.6.1":
                continue
            build = version.build
            if not str(build).encode('utf-8').decode('utf8') in legacyinfolist.number:
                eprint("Legacy build %d is missing in legacy info. Ignoring." % build)
                continue

            outVersion = versionFromLegacy(version, legacyinfolist.number[build])

    outFilepath = "multimc/net.minecraftforge/%s.json" % outVersion.version
    with open(outFilepath, 'w') as outfile:
        json.dump(outVersion.to_json(), outfile, sort_keys=True, indent=4)

recommendedVersions.sort()

print ('Recommended versions:', recommendedVersions)

sharedData = MultiMCSharedPackageData(uid = 'net.minecraftforge', name = "Forge")
sharedData.projectUrl = 'https://www.minecraftforge.net/forum/'
sharedData.recommended = recommendedVersions
sharedData.write()
