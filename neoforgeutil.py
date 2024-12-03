from metautil import *
from collections import namedtuple

# A post-processed entry constructed from the reconstructed Neoforge version index
class NeoforgeVersion:
    def __init__(self, entry):
        self.package = entry.package
        self.build = entry.build
        self.rawVersion = entry.version
        if self.package == "neoforge":
            self.rawVersion = entry.longversion
        self.mcversion = entry.mcversion
        self.mcversion_sane = self.mcversion.replace("_pre", "-pre", 1)
        self.branch = entry.branch
        self.installer_filename = None
        self.installer_url = None
        self.universal_filename = None
        self.universal_url = None
        self.changelog_url = None
        self.longVersion = entry.longversion

        for classifier, fileentry in entry.files.items():
            extension = fileentry.extension
            filename = fileentry.filename(self.longVersion)
            url = fileentry.url(self.longVersion)
            if (classifier == "installer") and (extension == "jar"):
                self.installer_filename = filename
                self.installer_url = url
            if (classifier == "universal" or classifier == "client") and (extension == "jar" or extension == "zip"):
                self.universal_filename = filename
                self.universal_url = url
            if (classifier == "changelog") and (extension == "txt"):
                self.changelog_url = url

    def name(self):
        return "Neoforge %d" % (self.build)

    def filename(self):
        return self.installer_filename

    def url(self):
        return self.installer_url

    def isSupported(self):
        if self.url() == None:
            return False

        versionElements = self.rawVersion.split('.')
        if len(versionElements) < 1:
            return False

        majorVersionStr = versionElements[0]
        if not majorVersionStr.isnumeric():
            return False

        return True

class NeoforgeFile(JsonObject):
    classifier = StringProperty(required=True)
    extension = StringProperty(required=True)
    legacy = BooleanProperty(required=True)

    def filename(self, longversion):
        return "%s-%s-%s.%s" % (self.package(), longversion, self.classifier, self.extension)

    def url(self, longversion):
        return "https://maven.neoforged.net/releases/net/neoforged/%s/%s/%s" % (self.package(), longversion, self.filename(longversion))

    def package(self):
        return "forge" if self.legacy else "neoforge"

class NeoforgeEntry(JsonObject):
    package = StringProperty(required=True,choices=["neoforge","forge"])
    longversion = StringProperty(required=True)
    mcversion = StringProperty(required=True)
    version = StringProperty(required=True)
    build = IntegerProperty(required=True)
    branch = StringProperty()
    latest = BooleanProperty()
    recommended = BooleanProperty()
    files = DictProperty(NeoforgeFile)

class NeoforgeMcVersionInfo(JsonObject):
    latest = StringProperty()
    recommended = StringProperty()
    versions = ListProperty(StringProperty())

class DerivedNeoforgeIndex(JsonObject):
    versions = DictProperty(NeoforgeEntry)
    by_mcversion = DictProperty(NeoforgeMcVersionInfo)

class NeoforgeLibrary(MojangLibrary):
    url = StringProperty(exclude_if_none=True)
    serverreq = BooleanProperty(exclude_if_none=True, default=None)
    clientreq = BooleanProperty(exclude_if_none=True, default=None)
    checksums = ListProperty(StringProperty)
    comment = StringProperty()

class NeoforgeVersionFile(MojangVersionFile):
    libraries = ListProperty(NeoforgeLibrary, exclude_if_none=True, default=None) # overrides Mojang libraries
    inheritsFrom = StringProperty()
    jar = StringProperty()

class DataSpec(JsonObject):
    client = StringProperty()
    server = StringProperty()

class ProcessorSpec(JsonObject):
    jar = StringProperty()
    classpath = ListProperty(StringProperty)
    args = ListProperty(StringProperty)
    outputs = DictProperty(StringProperty)
    sides = ListProperty(StringProperty, exclude_if_none=True, default=None)

class NeoforgeInstallerProfileV1(JsonObject):
    _comment = ListProperty(StringProperty)
    spec = DecimalProperty(required=True, choices=[1])
    profile = StringProperty()
    version = StringProperty()
    icon = StringProperty()
    json = StringProperty()
    path = GradleSpecifierProperty()
    logo = StringProperty()
    minecraft = StringProperty()
    welcome = StringProperty()
    data = DictProperty(DataSpec)
    processors = ListProperty(ProcessorSpec)
    libraries = ListProperty(MojangLibrary)
    hideExtract = BooleanProperty()
    serverJarPath = StringProperty()
    mirrorList = StringProperty(exclude_if_none=True, default=None)
    serverJarPath = StringProperty(exclude_if_none=True, default=None)

class InstallerInfo(JsonObject):
    sha1hash = StringProperty()
    sha256hash = StringProperty()
    size = IntegerProperty()
