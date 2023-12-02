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
    development = ListProperty(MultiMCLibrary, required=False)

class FabricInstallerDataV1(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibrariesV1, required=True)
    mainClass = jsonobject.DefaultProperty()
    arguments = ObjectProperty(FabricInstallerArguments, required=False)
    launchwrapper = ObjectProperty(FabricInstallerLaunchwrapper, required=False)

'''

This format was introduced with version 0.15.0
{
    "name": "org.ow2.asm:asm:9.6",
    "md5": "6f8bccf756f170d4185bb24c8c2d2020",
    "sha1": "aa205cf0a06dbd8e04ece91c0b37c3f5d567546a",
    "sha256": "3c6fac2424db3d4a853b669f4e3d1d9c3c552235e19a319673f887083c2303a1",
    "sha512": "01a5ea6f5b43bf094c52a50e18325a60af7bb02e74d24f9bc2c727d43e514578fd968b30ff22f9d2720caec071458f9ff82d11a21fbb1ebc42d8203e737c4b52",
    "size": 123598,
    "url": "https://maven.fabricmc.net/"
},
'''

class FabricLibrary (JsonObject):
    name = GradleSpecifierProperty(required = True)
    url = StringProperty(exclude_if_none=True, default=None)
    size = IntegerProperty()
    md5 = StringProperty(exclude_if_none=True, default=None)
    sha1 = StringProperty(exclude_if_none=True, default=None)
    sha256 = StringProperty(exclude_if_none=True, default=None)
    sha512 = StringProperty(exclude_if_none=True, default=None)

    def toMmcLibrary(self) -> MultiMCLibrary:
        return MultiMCLibrary(
            name = self.name,
            downloads = MojangLibraryDownloads(
                artifact = MojangArtifact(
                    sha1 = self.sha1,
                    size = self.size,
                    url = self.url + self.name.getPath(),
                ),
            ),
        )


class FabricInstallerLibrariesV2(JsonObject):
    client = ListProperty(FabricLibrary)
    common = ListProperty(FabricLibrary)
    server = ListProperty(FabricLibrary)
    development = ListProperty(FabricLibrary, required=False)

class FabricInstallerDataV2(JsonObject):
    version = IntegerProperty(required=True)
    libraries = ObjectProperty(FabricInstallerLibrariesV2, required=True)
    mainClass = jsonobject.DefaultProperty()
    min_java_version = IntegerProperty(required=True)


class FabricJarInfo(JsonObject):
    releaseTime = ISOTimestampProperty()
    size = IntegerProperty()
    sha256 = StringProperty()
    sha1 = StringProperty()
