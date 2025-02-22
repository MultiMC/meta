import json
from pprint import pprint
from jsonobject import *
from properties import *

'''
Mojang index files look like this:
{
    "latest": {
        "release": "1.11.2",
        "snapshot": "17w06a"
    },
    "versions": [
        ...
        {
            "id": "17w06a",
            "releaseTime": "2017-02-08T13:16:29+00:00",
            "time": "2017-02-08T13:17:20+00:00",
            "type": "snapshot",
            "url": "https://launchermeta.mojang.com/mc/game/7db0c61afa278d016cf1dae2fba0146edfbf2f8e/17w06a.json"
        },
        ...
    ]
}
'''

class MojangIndexEntry(JsonObject):
    id = StringProperty()
    releaseTime = ISOTimestampProperty()
    time = ISOTimestampProperty()
    type = StringProperty()
    url = StringProperty()
    sha1 = StringProperty(exclude_if_none=True, default=None)
    complianceLevel = IntegerProperty(exclude_if_none=True, default=None)

class MojangIndex(JsonObject):
    latest = DictProperty(StringProperty)
    versions = ListProperty(MojangIndexEntry)

class MojangIndexWrap:
    def __init__(self, json):
        self.index = MojangIndex.wrap(json)
        self.latest = self.index.latest
        versionsDict = {}
        for version in self.index.versions:
            versionsDict[version.id] = version
        self.versions = versionsDict


class MojangArtifactBase (JsonObject):
    sha1 = StringProperty(exclude_if_none=True, default=None)
    size = IntegerProperty(exclude_if_none=True, default=None)
    url = StringProperty()

class MojangArtifact (MojangArtifactBase):
    path = StringProperty(exclude_if_none=True, default=None)

class MojangAssets (MojangArtifactBase):
    id = StringProperty()
    totalSize = IntegerProperty()

class MojangLibraryDownloads(JsonObject):
    artifact = ObjectProperty(MojangArtifact, exclude_if_none=True, default=None)
    classifiers = DictProperty(MojangArtifact, exclude_if_none=True, default=None)

class MojangLibraryExtractRules(JsonObject):
    exclude = ListProperty(StringProperty)

'''
            "rules": [
                {
                    "action": "allow"
                },
                {
                    "action": "disallow",
                    "os": {
                        "name": "osx"
                    }
                }
            ]
'''

class OSRule (JsonObject):
    name = StringProperty(choices=["osx", "linux", "windows"], required = True)
    version = StringProperty(exclude_if_none=True, default=None)

class MojangRule (JsonObject):
    action = StringProperty(choices=["allow", "disallow"], required = True)
    os = ObjectProperty(OSRule, exclude_if_none=True, default=None)

class MojangLibrary (JsonObject):
    extract = ObjectProperty(MojangLibraryExtractRules, exclude_if_none=True, default=None)
    name = GradleSpecifierProperty(required = True)
    downloads = ObjectProperty(MojangLibraryDownloads, exclude_if_none=True, default=None)
    natives = DictProperty(StringProperty, exclude_if_none=True, default=None)
    rules = ListProperty(MojangRule, exclude_if_none=True, default=None)

class MojangLoggingArtifact (MojangArtifactBase):
    id = StringProperty()

class MojangLogging (JsonObject):
    file = ObjectProperty(MojangLoggingArtifact, required = True)
    argument = StringProperty(required = True)
    type = StringProperty(required = True, choices=["log4j2-xml"])

class MojangArguments (JsonObject):
    game = ListProperty(exclude_if_none=True, default=None)
    jvm = ListProperty(exclude_if_none=True, default=None)

class JavaVersion (JsonObject):
    component = StringProperty(default="jre-legacy")
    majorVersion = IntegerProperty(default=8)

class UnknownVersionException(Exception):
    """Exception raised for unknown Mojang version file format versions.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message

def validateSupportedMojangVersion(version):
    supportedVersion = 21
    if version > supportedVersion:
        raise UnknownVersionException("Unsupported Mojang format version: %d. Max supported is: %d" % (version, supportedVersion))

class MojangVersionFile (JsonObject):
    arguments = ObjectProperty(MojangArguments, exclude_if_none=True, default=None)
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    assets = StringProperty(exclude_if_none=True, default=None)
    downloads = DictProperty(MojangArtifactBase, exclude_if_none=True, default=None)
    id = StringProperty(exclude_if_none=True, default=None)
    libraries = ListProperty(MojangLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    processArguments = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    minimumLauncherVersion = IntegerProperty(exclude_if_none=True, default=None, validators=validateSupportedMojangVersion)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    time = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)
    inheritsFrom = StringProperty(exclude_if_none=True, default=None)
    logging = DictProperty(MojangLogging, exclude_if_none=True, default=None)
    complianceLevel = IntegerProperty(exclude_if_none=True, default=None)
    javaVersion = ObjectProperty(JavaVersion, exclude_if_none=True, default=None)

CurrentMultiMCFormatVersion = 1
def validateSupportedMultiMCVersion(version):
    if version > CurrentMultiMCFormatVersion:
        raise UnknownVersionException("Unsupported MultiMC format version: %d. Max supported is: %d" % (version, CurrentMultiMCFormatVersion))

class MultiMCLibrary (MojangLibrary):
    url = StringProperty(exclude_if_none=True, default=None)
    mmcHint = StringProperty(name="MMC-hint", exclude_if_none=True, default=None)

class VersionedJsonObject(JsonObject):
    formatVersion = IntegerProperty(default=CurrentMultiMCFormatVersion, validators=validateSupportedMultiMCVersion)

class DependencyEntry (JsonObject):
    uid = StringProperty(required=True)
    equals = StringProperty(exclude_if_none=True, default=None)
    suggests = StringProperty(exclude_if_none=True, default=None)

class MultiMCVersionFile (VersionedJsonObject):
    name = StringProperty(required=True)
    version = StringProperty(required=True)
    uid = StringProperty(required=True)
    requires = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    conflicts = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    volatile = BooleanProperty(exclude_if_none=True, default=None)
    assetIndex = ObjectProperty(MojangAssets, exclude_if_none=True, default=None)
    libraries = ListProperty(MultiMCLibrary, exclude_if_none=True, default=None)
    mavenFiles = ListProperty(MultiMCLibrary, exclude_if_none=True, default=None)
    mainJar = ObjectProperty(MultiMCLibrary, exclude_if_none=True, default=None)
    jarMods = ListProperty(MultiMCLibrary, exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    appletClass = StringProperty(exclude_if_none=True, default=None)
    minecraftArguments = StringProperty(exclude_if_none=True, default=None)
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    type = StringProperty(exclude_if_none=True, default=None)
    addTraits = ListProperty(StringProperty, name="+traits", exclude_if_none=True, default=None)
    addTweakers = ListProperty(StringProperty, name="+tweakers", exclude_if_none=True, default=None)
    order = IntegerProperty(exclude_if_none=True, default=None)

class UnknownComplianceLevelException(Exception):
    """Exception raised for unknown Mojang compliance level

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message


# Convert Mojang version file object to a MultiMC version file object
def MojangToMultiMC (file, name, uid, version):
    mmcFile = MultiMCVersionFile(
        {
            "name": name,
            "uid": uid,
            "version": version
        }
    )
    mmcFile.assetIndex = file.assetIndex
    mmcFile.libraries = file.libraries
    mmcFile.mainClass = file.mainClass
    if file.id:
        mainJar = MultiMCLibrary(
            {
                "name": "com.mojang:minecraft:%s:client" % file.id,
            }
        )
        cldl = file.downloads['client']
        mainJar.downloads = MojangLibraryDownloads()
        mainJar.downloads.artifact = MojangArtifact()
        mainJar.downloads.artifact.path = None
        mainJar.downloads.artifact.url = cldl.url
        mainJar.downloads.artifact.sha1 = cldl.sha1
        mainJar.downloads.artifact.size = cldl.size
        mmcFile.mainJar = mainJar

    mmcFile.minecraftArguments = file.minecraftArguments
    mmcFile.releaseTime = file.releaseTime
    # time should not be set.
    mmcFile.type = file.type
    maxSupportedLevel = 1
    if file.complianceLevel:
        if file.complianceLevel == 0:
            pass
        elif file.complianceLevel == 1:
            if not mmcFile.addTraits:
                mmcFile.addTraits = []
            mmcFile.addTraits.append("XR:Initial")
        else:
            raise UnknownComplianceLevelException("Unsupported Mojang compliance level: %d. Max supported is: %d" % (file.complianceLevel, maxSupportedLevel))
    return mmcFile

class MultiMCSharedPackageData(VersionedJsonObject):
    name = StringProperty(required=True)
    uid = StringProperty(required=True)
    recommended = ListProperty(StringProperty, exclude_if_none=True, default=None)
    authors = ListProperty(StringProperty, exclude_if_none=True, default=None)
    description = StringProperty(exclude_if_none=True, default=None)
    projectUrl = StringProperty(exclude_if_none=True, default=None)

    def write(self):
        try:
            with open("multimc/%s/package.json" % self.uid, 'w') as file:
                json.dump(self.to_json(), file, sort_keys=True, indent=4)
        except EnvironmentError as e:
            print("Error while trying to save shared packaged data for %s:" % self.uid, e)

def writeSharedPackageData(uid, name):
    desc = MultiMCSharedPackageData({
        'name': name,
        'uid': uid
        })
    with open("multimc/%s/package.json" % uid, 'w') as file:
        json.dump(desc.to_json(), file, sort_keys=True, indent=4)

def readSharedPackageData(uid):
    with open("multimc/%s/package.json" % uid, 'r') as file:
        return MultiMCSharedPackageData(json.load(file))

class MultiMCVersionIndexEntry(JsonObject):
    version = StringProperty()
    type = StringProperty(exclude_if_none=True, default=None)
    releaseTime = ISOTimestampProperty()
    requires = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    conflicts = ListProperty(DependencyEntry, exclude_if_none=True, default=None)
    recommended = BooleanProperty(exclude_if_none=True, default=None)
    volatile = BooleanProperty(exclude_if_none=True, default=None)
    sha256 = StringProperty()

class MultiMCVersionIndex(VersionedJsonObject):
    name = StringProperty()
    uid = StringProperty()
    versions = ListProperty(MultiMCVersionIndexEntry)

class MultiMCPackageIndexEntry(JsonObject):
    name = StringProperty()
    uid = StringProperty()
    sha256 = StringProperty()

class MultiMCPackageIndex(VersionedJsonObject):
    packages = ListProperty(MultiMCPackageIndexEntry)

'''
The MultiMC static override file for legacy looks like this:
{
    "versions": [
        ...
        {
            "id": "c0.0.13a",
            "checksum": "3617fbf5fbfd2b837ebf5ceb63584908",
            "releaseTime": "2009-05-31T00:00:00+02:00",
            "type": "old_alpha",
            "mainClass": "com.mojang.minecraft.Minecraft",
            "appletClass": "com.mojang.minecraft.MinecraftApplet",
            "+traits": ["legacyLaunch", "no-texturepacks"]
        },
        ...
    ]
}
'''

class LegacyOverrideEntry(JsonObject):
    releaseTime = ISOTimestampProperty(exclude_if_none=True, default=None)
    mainClass = StringProperty(exclude_if_none=True, default=None)
    appletClass = StringProperty(exclude_if_none=True, default=None)
    addTraits = ListProperty(StringProperty, name="+traits", exclude_if_none=True, default=None)

class LegacyOverrideIndex(JsonObject):
    versions = DictProperty(LegacyOverrideEntry)

def ApplyLegacyOverride (mmcFile, legacyOverride):
    # simply hard override classes
    mmcFile.mainClass = legacyOverride.mainClass
    mmcFile.appletClass = legacyOverride.appletClass
    # if we have an updated release time (more correct than Mojang), use it
    if legacyOverride.releaseTime != None:
        mmcFile.releaseTime = legacyOverride.releaseTime
    # add traits, if any
    if legacyOverride.addTraits:
        if not mmcFile.addTraits:
            mmcFile.addTraits = []
        mmcFile.addTraits = mmcFile.addTraits + legacyOverride.addTraits
    # remove all libraries - they are not needed for legacy
    mmcFile.libraries = None
    # remove minecraft arguments - we use our own hardcoded ones
    mmcFile.minecraftArguments = None
