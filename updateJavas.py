#!/usr/bin/python3
import json
import os
from urllib.parse import urlencode

from cachecontrol.caches import FileCache
from metautil import cachedSession
from javasutil import (
    JAVA_RUNTIME_BASE_DIR,
    JAVA_ADOPTIUM_DIR,
    JAVA_OPENJ9_DIR,
    JAVA_AZUL_DIR,
)


MOJANG_JAVA_URL = (
    "https://piston-meta.mojang.com/v1/products/java-runtime/"
    "2ec0cc96c44e5a76b9c8b7c39df7210883d12871/all.json"
)
ADOPTIUM_API_BASE = "https://api.adoptium.net"
OPENJ9_API_BASE = "https://api.adoptopenjdk.net"
AZUL_API_BASE = "https://api.azul.com/metadata/v1"
PAGE_SIZE = 10
AZUL_PAGE_SIZE = 100

forever_cache = FileCache("http_cache", forever=True)
sess = cachedSession(forever_cache)


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, sort_keys=True, indent=4)


def get_json(url, allow_404=False):
    response = sess.get(url)
    if allow_404 and response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def fetch_adoptx_provider(base_url, directory, jvm_impl, vendor):
    available = get_json(base_url + "/v3/info/available_releases")
    write_json(
        os.path.join("upstream", JAVA_RUNTIME_BASE_DIR, directory, "available_releases.json"),
        available,
    )

    for major in available["available_releases"]:
        releases = []
        page = 0
        while True:
            query = urlencode(
                {
                    "image_type": "jre",
                    "heap_size": "normal",
                    "page_size": PAGE_SIZE,
                    "page": page,
                    "project": "jdk",
                    "sort_method": "DEFAULT",
                    "sort_order": "DESC",
                    "jvm_impl": jvm_impl,
                    "vendor": vendor,
                }
            )
            url = (
                f"{base_url}/v3/assets/feature_releases/{major}/ga?{query}"
            )
            page_releases = get_json(url, allow_404=True)
            if page_releases is None:
                break

            releases.extend(page_releases)
            if len(page_releases) < PAGE_SIZE:
                break
            page += 1

        print(f"{directory}: Java {major}: {len(releases)} releases")
        if releases:
            write_json(
                os.path.join(
                    "upstream",
                    JAVA_RUNTIME_BASE_DIR,
                    directory,
                    "versions",
                    f"java{major}.json",
                ),
                releases,
            )


def update_azul():
    packages = []
    page = 1
    while True:
        query = urlencode(
            [
                ("archive_type", "zip"),
                ("release_status", "ga"),
                ("availability_types", "CA"),
                ("java_package_type", "jre"),
                ("javafx_bundled", "false"),
                ("latest", "true"),
                ("page", page),
                ("page_size", AZUL_PAGE_SIZE),
            ]
        )
        response = get_json(f"{AZUL_API_BASE}/zulu/packages/?{query}", allow_404=True)
        if response is None:
            break
        packages.extend(response)
        if len(response) < AZUL_PAGE_SIZE:
            break
        page += 1

    azul_dir = os.path.join("upstream", JAVA_RUNTIME_BASE_DIR, JAVA_AZUL_DIR)
    write_json(os.path.join(azul_dir, "packages.json"), packages)
    print(f"azul: {len(packages)} packages")

    for package in packages:
        package_uuid = package["package_uuid"]
        details = get_json(
            f"{AZUL_API_BASE}/zulu/packages/{package_uuid}"
        )
        write_json(
            os.path.join(azul_dir, "versions", f"{package_uuid}.json"),
            details,
        )


def main():
    # Keep the existing Mojang manifest location used by this repository.
    mojang_java = get_json(MOJANG_JAVA_URL)
    write_json(os.path.join("upstream", "jres", "all.json"), mojang_java)

    fetch_adoptx_provider(
        ADOPTIUM_API_BASE, JAVA_ADOPTIUM_DIR, "hotspot", "eclipse"
    )
    fetch_adoptx_provider(
        OPENJ9_API_BASE, JAVA_OPENJ9_DIR, "openj9", "ibm"
    )
    update_azul()


if __name__ == "__main__":
    main()
