#!/usr/bin/python3
from __future__ import print_function
import sys
import os
import re
from metautil import *
from neoforgeutil import *
from jsonobject import *
from distutils.version import LooseVersion

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def versionFromBuildSystemInstaller(installerVersion : MojangVersionFile, installerProfile: NeoforgeInstallerProfileV1, version: NeoforgeVersion):
    eprint("Generating NeoForge %s." % version.longVersion)
    result = MultiMCVersionFile({"name": "NeoForge", "version": version.rawVersion, "uid": "net.neoforged" })
    result.requires = [DependencyEntry(uid='net.minecraft', equals=version.mcversion_sane)]
    result.mainClass = "io.github.zekerzhayard.forgewrapper.installer.Main"

    mavenLibs = []

    # load the locally cached installer file info and use it to add the installer entry in the json
    with open("upstream/neoforge/installer_info/%s.json" % version.longVersion, 'r', encoding='utf-8') as f:
        installerInfo = InstallerInfo(json.load(f))
        InstallerLib = MultiMCLibrary(name=GradleSpecifier("net.neoforged:%s:%s:installer" % (version.package, version.longVersion)))
        InstallerLib.downloads = MojangLibraryDownloads()
        InstallerLib.downloads.artifact = MojangArtifact()
        InstallerLib.downloads.artifact.url = "https://maven.neoforged.net/%s" % (InstallerLib.name.getPath())
        InstallerLib.downloads.artifact.sha1 = installerInfo.sha1hash
        InstallerLib.downloads.artifact.size = installerInfo.size
        mavenLibs.append(InstallerLib)

    for upstreamLib in installerProfile.libraries:
        mmcLib = MultiMCLibrary(upstreamLib.to_json())
        if mmcLib.name.isLog4j():
            continue
        mavenLibs.append(mmcLib)

    result.mavenFiles = mavenLibs

    libraries = []

    wrapperLib = MultiMCLibrary(name=GradleSpecifier("io.github.zekerzhayard:ForgeWrapper:mmc5"))
    wrapperLib.downloads = MojangLibraryDownloads()
    wrapperLib.downloads.artifact = MojangArtifact()
    wrapperLib.downloads.artifact.url = "https://files.multimc.org/maven/%s" % (wrapperLib.name.getPath())
    wrapperLib.downloads.artifact.sha1 = "d82cb39636a5092a8e5b5de82ccfe5f7e70e8d49"
    wrapperLib.downloads.artifact.size = 35390
    libraries.append(wrapperLib)

    for upstreamLib in installerVersion.libraries:
        mmcLib = MultiMCLibrary(upstreamLib.to_json())
        if mmcLib.name.isLog4j():
            continue
        libraries.append(mmcLib)
    result.libraries = libraries

    result.releaseTime = installerVersion.releaseTime
    result.order = 5
    mcArgs = "--username ${auth_player_name} --version ${version_name} --gameDir ${game_directory} --assetsDir ${assets_root} --assetIndex ${assets_index_name} --uuid ${auth_uuid} --accessToken ${auth_access_token} --userType ${user_type} --versionType ${version_type}"
    for arg in installerVersion.arguments.game:
        mcArgs += " %s" % arg
    result.minecraftArguments = mcArgs
    return result

# load the locally cached version list
with open("upstream/neoforge/derived_index.json", 'r', encoding='utf-8') as f:
    main_json = json.load(f)
    remoteVersionlist = DerivedNeoforgeIndex(main_json)

recommendedVersions = []

for id, entry in remoteVersionlist.versions.items():
    if entry.mcversion == None:
        eprint ("Skipping %s with invalid MC version" % id)
        continue

    version = NeoforgeVersion(entry)
    if version.url() == None:
        eprint ("Skipping %s with no valid files" % id)
        continue
    eprint ("Processing NeoForge %s" % version.rawVersion)
    versionElements = version.rawVersion.split('.')
    if len(versionElements) < 1:
        eprint ("Skipping version %s with not enough version elements" % (id))
        continue

    majorVersionStr = versionElements[0]
    if not majorVersionStr.isnumeric():
        eprint ("Skipping version %s with non-numeric major version %s" % (id, majorVersionStr))
        continue

    majorVersion = int(majorVersionStr)

    if entry.recommended:
        recommendedVersions.append(version.longVersion)

    # If we do not have the corresponding Minecraft version, we ignore it
    if not os.path.isfile("multimc/net.minecraft/%s.json" % version.mcversion_sane):
        eprint ("Skipping %s with no corresponding Minecraft version %s" % (id, version.mcversion_sane))
        continue

    outVersion = None

    # Path for new-style build system based installers
    installerVersionFilepath = "upstream/neoforge/version_manifests/%s.json" % version.longVersion
    profileFilepath = "upstream/neoforge/installer_manifests/%s.json" % version.longVersion

    eprint(installerVersionFilepath)
    if os.path.isfile(installerVersionFilepath):
        with open(installerVersionFilepath, 'r', encoding='utf-8') as installerVersionFile:
            installerVersion = MojangVersionFile(json.load(installerVersionFile))
        with open(profileFilepath, 'r', encoding='utf-8') as profileFile:
            installerProfile = NeoforgeInstallerProfileV1(json.load(profileFile))
        outVersion = versionFromBuildSystemInstaller(installerVersion, installerProfile, version)
    else:
        # If we do not have the Neoforge json, we ignore this version
        eprint ("Skipping %s with missing profile json" % id)
        continue

    outFilepath = "multimc/net.neoforged/%s.json" % outVersion.version
    with open(outFilepath, 'w') as outfile:
        json.dump(outVersion.to_json(), outfile, sort_keys=True, indent=4)

recommendedVersions.sort()

print ('Recommended versions:', recommendedVersions)

sharedData = MultiMCSharedPackageData(uid = 'net.neoforged', name = "NeoForge")
sharedData.projectUrl = 'https://neoforged.net/'
sharedData.recommended = recommendedVersions
sharedData.write()
