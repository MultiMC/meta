from jsonobject import *
import datetime
import iso8601

class ISOTimestampProperty(AbstractDateProperty):
    _type = datetime.datetime

    def _wrap(self, value):
        try:
            return iso8601.parse_date(value)
        except ValueError as e:
            raise ValueError(
                'Invalid ISO date/time {0!r} [{1}]'.format(value, e))

    def _unwrap(self, value):
        return value, value.isoformat()


class GradleSpecifier:
    '''
        A gradle specifier - a maven coordinate. Like one of these:
        "org.lwjgl.lwjgl:lwjgl:2.9.0"
        "net.java.jinput:jinput:2.0.5"
        "net.minecraft:launchwrapper:1.5"
    '''

    def __init__(self, name):
        atSplit = name.split('@')

        components = atSplit[0].split(':')
        self.group = components[0]
        self.artifact = components[1]
        self.version = components[2]

        self.extension = 'jar'
        if len(atSplit) == 2:
            self.extension = atSplit[1]

        if len(components) == 4:
            self.classifier = components[3]
        else:
            self.classifier = None

    def toString(self):
        extensionStr = ''
        if self.extension != 'jar':
            extensionStr = "@%s" % self.extension
        if self.classifier:
            return "%s:%s:%s:%s%s" % (self.group, self.artifact, self.version, self.classifier, extensionStr)
        else:
            return "%s:%s:%s%s" % (self.group, self.artifact, self.version, extensionStr)

    def getFilename(self):
        if self.classifier:
            return "%s-%s-%s.%s" % (self.artifact, self.version, self.classifier, self.extension)
        else:
            return "%s-%s.%s" % (self.artifact, self.version, self.extension)

    def getBase(self):
        return "%s/%s/%s/" % (self.group.replace('.','/'), self.artifact, self.version)

    def getPath(self):
        return self.getBase() + self.getFilename()


    def __repr__(self):
        return "GradleSpecifier('" + self.toString() + "')"

    def isLwjgl(self):
        return self.group in ("org.lwjgl", "org.lwjgl.lwjgl", "net.java.jinput", "net.java.jutils")

    def isLog4j(self):
        return self.group == "org.apache.logging.log4j"


    def __lt__(self, other):
        return self.toString() < other.toString()

    def __eq__(self, other):
        return self.group == other.group and self.artifact == other.artifact and self.version == other.version and self.classifier == other.classifier

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return self.toString().__hash__()

class GradleSpecifierProperty(JsonProperty):
    def wrap(self, value):
        return GradleSpecifier(value)

    def unwrap(self, value):
        return value, value.toString()
