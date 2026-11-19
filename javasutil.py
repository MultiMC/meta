import json
from pprint import pprint
from jsonobject import *
from properties import *

class PistonAvailability(JsonObject):
    group = IntegerProperty()
    progress = IntegerProperty()

class PistonArtifact(JsonObject):
    sha1 = StringProperty()
    size = IntegerProperty()
    url = StringProperty()

class PistonVersion(JsonObject):
    name = StringProperty()
    released = ISOTimestampProperty()

class PistonRelease(JsonObject):
    availability = ObjectProperty(PistonAvailability)
    manifest = ObjectProperty(PistonArtifact)
    version = ObjectProperty(PistonVersion)

# NOTE: this will blow up when Mojang adds a JRE-like product
class PlatformJREManifest(JsonObject):
    jre_legacy = ListProperty(PistonRelease, name="jre-legacy")
    java_runtime_alpha = ListProperty(PistonRelease, name="java-runtime-alpha")
    java_runtime_beta = ListProperty(PistonRelease, name="java-runtime-beta")
    java_runtime_gamma = ListProperty(PistonRelease, name="java-runtime-gamma")
    java_runtime_gamma_snapshot = ListProperty(PistonRelease, name="java-runtime-gamma-snapshot")
    java_runtime_delta = ListProperty(PistonRelease, name="java-runtime-delta")
    minecraft_java_exe = ListProperty(PistonRelease, name="minecraft-java-exe")

# NOTE: this will blow up when Mojang adds a new platform
class AllPlatformsJREManifest(JsonObject):
    gamecore = ObjectProperty(PlatformJREManifest, name="gamecore")
    linux_amd64 = ObjectProperty(PlatformJREManifest, name="linux")
    linux_x86 = ObjectProperty(PlatformJREManifest, name="linux-i386")
    macos_amd64 = ObjectProperty(PlatformJREManifest, name="mac-os")
    macos_arm64 = ObjectProperty(PlatformJREManifest, name="mac-os-arm64")
    windows_arm64 = ObjectProperty(PlatformJREManifest, name="windows-arm64")
    windows_amd64 = ObjectProperty(PlatformJREManifest, name="windows-x64")
    windows_x86 = ObjectProperty(PlatformJREManifest, name="windows-x86")

class JavaVersion(JsonObject):
    download = ObjectProperty(PistonArtifact)

class RuntimeJavaVersion(JsonObject):
    major = IntegerProperty()
    minor = IntegerProperty()
    security = IntegerProperty()
    build = IntegerProperty(exclude_if_none=True, default=None)
    buildstr = StringProperty(exclude_if_none=True, default=None)
    name = StringProperty(exclude_if_none=True, default=None)

    def __str__(self):
        version = "%d.%d.%d" % (self.major, self.minor, self.security)
        if self.build is not None:
            version = "%s+%d" % (version, self.build)
        if self.buildstr is not None:
            version = "%s-%s" % (version, self.buildstr)
        return version

class JavaChecksum(JsonObject):
    type = StringProperty()
    hash = StringProperty()

class JavaRuntime(JsonObject):
    name = StringProperty()
    vendor = StringProperty()
    url = StringProperty()
    releaseTime = ISOTimestampProperty()
    checksum = ObjectProperty(JavaChecksum, exclude_if_none=True, default=None)
    downloadType = StringProperty()
    packageType = StringProperty()
    version = ObjectProperty(RuntimeJavaVersion)
    runtimeOS = StringProperty()

JAVA_RUNTIME_BASE_DIR = "java_runtime"
JAVA_ADOPTIUM_DIR = "adoptium"
JAVA_OPENJ9_DIR = "ibm"
JAVA_AZUL_DIR = "azul"

JAVA_MINECRAFT_COMPONENT = "net.minecraft.java"
JAVA_ADOPTIUM_COMPONENT = "net.adoptium.java"
JAVA_OPENJ9_COMPONENT = "com.ibm.java"
JAVA_AZUL_COMPONENT = "com.azul.java"


class VersionIndex(JsonObject):
    java8 = ObjectProperty(JavaVersion, name="8") # legacy -> 8
    java16 = ObjectProperty(JavaVersion, name="16") # alpha -> 16
    java17 = ObjectProperty(JavaVersion, name="17") # beta, gamma-snapshot, gamma -> 17
    java21 = ObjectProperty(JavaVersion, name="21") # delta -> 21

class PlatformIndex(JsonObject):
    arm64 = ObjectProperty()
    amd64 = ObjectProperty()
    x86 = ObjectProperty()

class AllIndex(JsonObject):
    linux = ObjectProperty(PlatformIndex)
    windows = ObjectProperty(PlatformIndex)
    mac = ObjectProperty(PlatformIndex)

class JREIndexWrap:
    def __init__(self, json):
        self.original = AllPlatformsJREManifest.wrap(json)
        # self.latest = self.index.latest
        # versionsDict = {}
        # for version in self.index.versions:
        #     versionsDict[version.id] = version
        # self.versions = versionsDict
