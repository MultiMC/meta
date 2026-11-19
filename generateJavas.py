#!/usr/bin/python3
import datetime
import json
import os
import re

import iso8601
from javasutil import (
    JavaChecksum,
    JavaRuntime,
    RuntimeJavaVersion,
    JAVA_RUNTIME_BASE_DIR,
    JAVA_ADOPTIUM_DIR,
    JAVA_OPENJ9_DIR,
    JAVA_AZUL_DIR,
    JAVA_MINECRAFT_COMPONENT,
    JAVA_ADOPTIUM_COMPONENT,
    JAVA_OPENJ9_COMPONENT,
    JAVA_AZUL_COMPONENT,
)
from metautil import MultiMCVersionFile, MultiMCSharedPackageData


UPSTREAM_DIR = "upstream"
LAUNCHER_DIR = "multimc"
MOJANG_JAVA_FILE = os.path.join(UPSTREAM_DIR, "jres", "all.json")

OS_NAMES = ("mac-os", "linux", "windows")
OS_TRANSLATIONS = {
    "osx": "mac-os",
    "mac": "mac-os",
    "macos": "mac-os",
}
ARCHITECTURES = ("x64", "x86", "arm64", "arm32", "riscv64")
ARCH_TRANSLATIONS = {
    64: "x64",
    32: "x86",
    "x32": "x86",
    "i386": "x86",
    "aarch64": "arm64",
    "x86_64": "x64",
    "arm": "arm32",
}
MOJANG_OS_MAP = {
    "linux": "linux-x64",
    "linux-i386": "linux-x86",
    "mac-os": "mac-os-x64",
    "mac-os-arm64": "mac-os-arm64",
    "windows-arm64": "windows-arm64",
    "windows-x64": "windows-x64",
    "windows-x86": "windows-x86",
}
MOJANG_MAJOR_MAP = {
    "jre-legacy": 8,
    "java-runtime-alpha": 17,
    "java-runtime-beta": 17,
    "java-runtime-gamma": 17,
    "java-runtime-gamma-snapshot": 17,
    "java-runtime-delta": 21,
    "java-runtime-epsilon": 25,
}
EXTRA_RUNTIME_PLATFORMS = {
    8: {
        "mac-os-arm64",
        "windows-arm64",
        "windows-arm32",
        "linux-arm32",
        "linux-arm64",
    },
    17: {
        "windows-arm32",
        "linux-arm32",
        "linux-arm64",
        "linux-x86",
        "linux-riscv64",
    },
    21: {"windows-arm32", "linux-arm32", "linux-arm64", "linux-x86", "linux-riscv64"},
    25: {"windows-arm32", "linux-arm32", "linux-arm64", "linux-x86", "linux-riscv64"},
}


def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def translate_os(value):
    value = value.lower()
    if value in OS_NAMES:
        return value
    return OS_TRANSLATIONS.get(value)


def translate_arch(value):
    if isinstance(value, str):
        value = value.lower()
    if value in ARCHITECTURES:
        return value
    return ARCH_TRANSLATIONS.get(value)


def runtime_version(major, minor=0, security=0, build=None, buildstr=None, name=None):
    values = {"major": major, "minor": minor, "security": security}
    if build is not None:
        values["build"] = build
    if buildstr is not None:
        values["buildstr"] = buildstr
    if name is not None:
        values["name"] = name
    return RuntimeJavaVersion(values)


def make_runtime(
    name,
    vendor,
    url,
    release_time,
    download_type,
    package_type,
    version,
    runtime_os,
    checksum=None,
):
    values = {
        "name": name,
        "vendor": vendor,
        "url": url,
        "releaseTime": release_time.isoformat(),
        "downloadType": download_type,
        "packageType": package_type,
        "version": version.to_json(),
        "runtimeOS": runtime_os,
    }
    if checksum is not None:
        values["checksum"] = checksum.to_json()
    return JavaRuntime(values)


def mojang_version(name):
    base, separator, buildstr = name.partition("-")
    if "u" in base:
        major_text, security_text = base.split("u", 1)
        security_match = re.match(r"\d+", security_text)
        if not major_text.isdigit() or security_match is None:
            raise ValueError(f"Unrecognized Mojang Java version: {name}")
        major = int(major_text)
        security = int(security_match.group(0))
        minor = 0
        build = None
    else:
        numbers = [int(value) for value in re.findall(r"\d+", base)]
        if not numbers:
            raise ValueError(f"Unrecognized Mojang Java version: {name}")
        major = numbers[0]
        minor = numbers[1] if len(numbers) > 1 else 0
        security = numbers[2] if len(numbers) > 2 else 0
        build = numbers[3] if len(numbers) > 3 else None

    return runtime_version(
        major,
        minor,
        security,
        build=build,
        buildstr=buildstr if separator else None,
        name=name,
    )


def adoptx_runtime(release, binary, runtime_os):
    package = binary["package"]
    version_data = release["version_data"]
    vendor = release["vendor"]
    distributions = {"eclipse": "temurin", "ibm": "semeru-open"}
    distribution = distributions.get(vendor)
    if distribution is None:
        raise ValueError(f"Unsupported Adoptx vendor: {vendor}")

    version = runtime_version(
        version_data.get("major") or 0,
        version_data.get("minor") or 0,
        version_data.get("security") or 0,
        build=version_data.get("build"),
    )
    checksum = None
    if package.get("checksum"):
        checksum = JavaChecksum({"type": "sha256", "hash": package["checksum"]})

    return make_runtime(
        f"{vendor}_{distribution}_{binary['image_type']}{version}",
        vendor,
        package["link"],
        iso8601.parse_date(release["timestamp"]),
        "archive",
        binary["image_type"],
        version,
        runtime_os,
        checksum,
    )


def azul_runtime(package, runtime_os):
    version_parts = list(package["java_version"])
    while len(version_parts) < 3:
        version_parts.append(0)
    version = runtime_version(
        version_parts[0],
        version_parts[1],
        version_parts[2],
        build=version_parts[3] if len(version_parts) > 3 else None,
    )
    checksum = None
    if package.get("sha256_hash"):
        checksum = JavaChecksum({"type": "sha256", "hash": package["sha256_hash"]})

    return make_runtime(
        f"azul_{package['product']}_{package['java_package_type']}{version}",
        "azul",
        package["download_url"],
        iso8601.parse_date(package["build_date"]),
        "archive",
        package["java_package_type"],
        version,
        runtime_os,
        checksum,
    )


def mojang_runtime(runtime, component, runtime_os):
    name = runtime["version"]["name"]
    version = mojang_version(name)
    checksum = JavaChecksum(
        {"type": "sha1", "hash": runtime["manifest"]["sha1"]}
    )
    return make_runtime(
        component,
        "mojang",
        runtime["manifest"]["url"],
        iso8601.parse_date(runtime["version"]["released"]),
        "manifest",
        "jre",
        version,
        runtime_os,
        checksum,
    )


def add_runtime(runtimes_by_major, extra_runtimes, runtime, major):
    runtimes_by_major.setdefault(major, []).append(runtime)
    if runtime.runtimeOS in EXTRA_RUNTIME_PLATFORMS.get(major, set()):
        extra_runtimes.setdefault(major, []).append(runtime)


def process_adoptx(directory, component, runtimes_by_major, extra_runtimes):
    provider_dir = os.path.join(UPSTREAM_DIR, JAVA_RUNTIME_BASE_DIR, directory)
    available_path = os.path.join(provider_dir, "available_releases.json")
    if not os.path.isfile(available_path):
        return

    available = read_json(available_path)
    for major in available["available_releases"]:
        release_path = os.path.join(
            provider_dir, "versions", f"java{major}.json"
        )
        if not os.path.isfile(release_path):
            continue
        for release in read_json(release_path):
            for binary in release["binaries"]:
                package = binary.get("package")
                if package is None or binary.get("image_type") != "jre":
                    continue
                runtime_arch = translate_arch(binary["architecture"])
                runtime_system = translate_os(binary["os"])
                if runtime_arch is None or runtime_system is None:
                    print(
                        f"Ignoring {component} release for "
                        f"{binary['os']} {binary['architecture']}"
                    )
                    continue
                runtime_os = f"{runtime_system}-{runtime_arch}"
                runtime = adoptx_runtime(release, binary, runtime_os)
                add_runtime(runtimes_by_major, extra_runtimes, runtime, major)


def process_azul(runtimes_by_major, extra_runtimes):
    azul_dir = os.path.join(UPSTREAM_DIR, JAVA_RUNTIME_BASE_DIR, JAVA_AZUL_DIR)
    packages_path = os.path.join(azul_dir, "packages.json")
    if not os.path.isfile(packages_path):
        return

    for package in read_json(packages_path):
        detail_path = os.path.join(
            azul_dir, "versions", f"{package['package_uuid']}.json"
        )
        detail = read_json(detail_path)
        major = detail["java_version"][0]
        if major < 8 or detail["java_package_type"] != "jre":
            continue

        runtime_system = translate_os(detail["os"])
        if detail["arch"] == "arm":
            runtime_arch = translate_arch(f"arm{detail['hw_bitness']}")
        elif detail["arch"] == "x86":
            runtime_arch = translate_arch(int(detail["hw_bitness"]))
        else:
            runtime_arch = None
        if runtime_arch is None or runtime_system is None:
            print(
                f"Ignoring Azul release for "
                f"{detail['os']} {detail['arch']}_{detail['hw_bitness']}"
            )
            continue

        runtime = azul_runtime(detail, f"{runtime_system}-{runtime_arch}")
        add_runtime(runtimes_by_major, extra_runtimes, runtime, major)


def write_javas(runtimes_by_major, uid):
    os.makedirs(os.path.join(LAUNCHER_DIR, uid), exist_ok=True)
    sorted_runtimes = dict(sorted(runtimes_by_major.items()))
    timestamps = {}
    previous_timestamp = None
    for major, runtimes in sorted_runtimes.items():
        release_time = min(runtime.releaseTime for runtime in runtimes)
        if previous_timestamp is not None and release_time < previous_timestamp:
            release_time = previous_timestamp + datetime.timedelta(seconds=1)
        previous_timestamp = release_time
        timestamps[major] = release_time

    for major, runtimes in sorted_runtimes.items():
        version = MultiMCVersionFile(
            {
                "name": f"Java {major}",
                "uid": uid,
                "version": f"java{major}",
            }
        )
        version.releaseTime = timestamps[major]
        version.runtimes = runtimes
        path = os.path.join(LAUNCHER_DIR, uid, f"java{major}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(version.to_json(), f, sort_keys=True, indent=4)

    package = MultiMCSharedPackageData(
        {"uid": uid, "name": "Java Runtimes", "recommended": []}
    )
    package.write()


def build_provider_components():
    extra_runtimes = {}
    for directory, component in (
        (JAVA_ADOPTIUM_DIR, JAVA_ADOPTIUM_COMPONENT),
        (JAVA_OPENJ9_DIR, JAVA_OPENJ9_COMPONENT),
        (JAVA_AZUL_DIR, JAVA_AZUL_COMPONENT),
    ):
        runtimes_by_major = {}
        if directory == JAVA_AZUL_DIR:
            process_azul(runtimes_by_major, extra_runtimes)
        else:
            process_adoptx(directory, component, runtimes_by_major, extra_runtimes)
        write_javas(runtimes_by_major, component)

    return extra_runtimes


def get_mojang_fallback(extra_runtimes, component, runtime_os):
    major = MOJANG_MAJOR_MAP.get(component)
    if major not in extra_runtimes:
        return None
    possible = [
        runtime
        for runtime in extra_runtimes[major]
        if runtime.runtimeOS == runtime_os
    ]
    if not possible:
        return None

    preferred = [runtime for runtime in possible if runtime.vendor != "azul"]
    if not preferred:
        preferred = possible
    preferred.sort(
        key=lambda runtime: (
            runtime.version.major,
            runtime.version.minor,
            runtime.version.security,
            runtime.version.build or 0,
            runtime.version.buildstr or "",
        ),
        reverse=True,
    )
    fallback = JavaRuntime(preferred[0].to_json())
    fallback.name = component
    return fallback


def process_mojang(extra_runtimes):
    mojang_manifest = read_json(MOJANG_JAVA_FILE)
    runtimes_by_major = {}

    for os_name, components in mojang_manifest.items():
        if os_name == "gamecore":
            continue
        runtime_os = MOJANG_OS_MAP.get(os_name)
        if runtime_os is None:
            print(f"Ignoring unsupported Mojang Java platform: {os_name}")
            continue

        for component, runtimes in components.items():
            if component == "minecraft-java-exe":
                continue
            component_major = MOJANG_MAJOR_MAP.get(component)
            if component_major is None:
                print(f"Ignoring unsupported Mojang Java component: {component}")
                continue

            if not runtimes:
                if os_name in ("windows-arm64", "mac-os-arm64"):
                    if component in ("java-runtime-alpha", "java-runtime-beta"):
                        runtimes = components.get("java-runtime-gamma", [])
                    elif component == "jre-legacy":
                        fallback = get_mojang_fallback(
                            extra_runtimes, component, runtime_os
                        )
                        if fallback is not None:
                            add_runtime(
                                runtimes_by_major, {}, fallback, component_major
                            )
                if os_name == "linux-i386" and component != "jre-legacy":
                    fallback = get_mojang_fallback(
                        extra_runtimes, component, runtime_os
                    )
                    if fallback is not None:
                        add_runtime(
                            runtimes_by_major, {}, fallback, component_major
                        )

            for runtime_data in runtimes:
                runtime = mojang_runtime(runtime_data, component, runtime_os)
                if component == "jre-legacy":
                    runtime_major = 8
                else:
                    runtime_major = int(
                        runtime_data["version"]["name"].partition(".")[0]
                    )
                add_runtime(runtimes_by_major, {}, runtime, runtime_major)

    for runtime_os in (
        "windows-arm32",
        "linux-arm32",
        "linux-arm64",
        "linux-riscv64",
    ):
        for component in MOJANG_MAJOR_MAP:
            fallback = get_mojang_fallback(extra_runtimes, component, runtime_os)
            if fallback is not None:
                add_runtime(
                    runtimes_by_major,
                    {},
                    fallback,
                    MOJANG_MAJOR_MAP[component],
                )

    write_javas(runtimes_by_major, JAVA_MINECRAFT_COMPONENT)


def main():
    extra_runtimes = build_provider_components()
    process_mojang(extra_runtimes)


if __name__ == "__main__":
    main()
