from metautil import *
import jsonobject

class FabricInstallerArguments(JsonObject):
    client = ListProperty(StringProperty)
    common = ListProperty(StringProperty)
    server = ListProperty(StringProperty)

class FabricInstallerLaunchwrapper(JsonObject):
    tweakers = ObjectProperty(FabricInstallerArguments, required=True)

class FabricInstallerLibrariesV1(JsonObject):
    client = ListProperty(MultiMCLibrary)
    common = ListProperty(MultiMCLibrary)
    server = ListProperty(MultiMCLibrary)

class FabricLibraryV2(JsonObject):
    md5 = StringProperty(exclude_if_none=True, default=None)
    sha1 = StringProperty(default=None)
    sha256 = StringProperty(exclude_if_none=True, default=None)
    sha512 = StringProperty(exclude_if_none=True, default=None)
    size = IntegerProperty(exclude_if_none=True, default=None)
    url = StringProperty(required=True)
    name = GradleSpecifierProperty(required=True)

    def toMmcLibrary(self) -> MultiMCLibrary:
        return MultiMCLibrary(
            extract = None,
            name = self.name,
            downloads = MojangLibraryDownloads(
                artifact = MojangArtifact(
                    path = None,
                    sha1 = self.sha1,
                    size = self.size,
                    url = self.url
                ),
                classifiers = None
            ),
            natives = None,
            rules = None,
            url = None,
            mmcHint = None
        )

class FabricInstallerLibrariesV2(JsonObject):
    client = ListProperty(FabricLibraryV2)
    common = ListProperty(FabricLibraryV2)
    server = ListProperty(FabricLibraryV2)
    development = ListProperty(FabricLibraryV2)

class FabricInstallerDataV1(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibrariesV1, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(FabricInstallerArguments, required=False)
    launchwrapper = ObjectProperty(FabricInstallerLaunchwrapper, required=False)

class FabricInstallerDataV2(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibrariesV2, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(FabricInstallerArguments, required=False)
    launchwrapper = ObjectProperty(FabricInstallerLaunchwrapper, required=False)
    min_java_version = IntegerProperty(exclude_if_none=True, default=None)

class FabricJarInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()
