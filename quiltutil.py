from metautil import *
import jsonobject

# barebones semver-like parser
def isQuiltVerStable(ver):
    s = ver.split("+")
    return ("-" not in s[0])

class QuiltInstallerArguments(JsonObject):
    client = ListProperty(StringProperty)
    common = ListProperty(StringProperty)
    server = ListProperty(StringProperty)

class QuiltInstallerLaunchwrapper(JsonObject):
    tweakers = ObjectProperty(QuiltInstallerArguments, required=True)

class QuiltInstallerLibraries(JsonObject):
    client = ListProperty(MultiMCLibrary)
    common = ListProperty(MultiMCLibrary)
    server = ListProperty(MultiMCLibrary)

class QuiltInstallerDataV1(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(QuiltInstallerLibraries, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(QuiltInstallerArguments, required=False)
    launchwrapper = ObjectProperty(QuiltInstallerLaunchwrapper, required=False)

class QuiltJarInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()
