from metautil import *
import jsonobject

variants = {
    "fabric": {
        "name": "Fabric Loader",
        "description": "Fabric Loader is a tool to load Fabric-compatible mods in game environments.",
        "url": "https://fabricmc.net",
        "authors": ["Fabric Developers"],
        "meta": "https://meta.fabricmc.net",
        "maven": "https://maven.fabricmc.net",
        "loader_uid": "net.fabricmc.fabric-loader",
        "intermediary_uid": "net.fabricmc.intermediary",
        "exclude": [],
    },
    "legacy-fabric": {
        "name": "Fabric Loader 1.8.9",
        "description": "Fabric Loader for 1.8.9 and below.",
        "url": "https://legacyfabric.net",
        "authors": ["Legacy Fabric Developers"],
        "meta": "https://meta.legacyfabric.net",
        "maven": "https://maven.legacyfabric.net",
        "loader_uid": "net.legacyfabric.fabric-loader-189",
        "intermediary_uid": "net.legacyfabric.intermediary",
        "exclude": ["fabric-loader"],
    },
}

# barebones semver-like parser
def isFabricVerStable(ver):
    s = ver.split("+")
    return ("-" not in s[0])

class FabricInstallerArguments(JsonObject):
    client = ListProperty(StringProperty)
    common = ListProperty(StringProperty)
    server = ListProperty(StringProperty)

class FabricInstallerLaunchwrapper(JsonObject):
    tweakers = ObjectProperty(FabricInstallerArguments, required=True)

class FabricInstallerLibraries(JsonObject):
    client = ListProperty(MultiMCLibrary)
    common = ListProperty(MultiMCLibrary)
    server = ListProperty(MultiMCLibrary)

class FabricInstallerDataV1(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibraries, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(FabricInstallerArguments, required=False)
    launchwrapper = ObjectProperty(FabricInstallerLaunchwrapper, required=False)

class FabricJarInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()
