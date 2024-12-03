#!/bin/bash

BASEDIR=$(dirname "$0")
cd "${BASEDIR}"
BASEDIR=`pwd`

set -x

source config.sh
if [ -f config/config_local.sh ]; then
    source config/config_local.sh
fi

MODE=${MODE:-develop}

S3_BUCKET_var="S3_$MODE"
S3_BUCKET="${!S3_BUCKET_var}"

BRANCH_var="BRANCH_$MODE"
BRANCH="${!BRANCH_var}"

function fail_in {
    if [ "${DISCORD_NOTIFY}" = true ] ; then
        discord_webhook -u "${DISCORD_NOTIFY_HOOK_ERROR}" -c "Meta failed to update: $1" --username "Meta Error"
    fi
    cd "${BASEDIR}/${UPSTREAM_DIR}"
    git reset --hard HEAD
    exit 1
}

function fail_out {
    if [ "${DISCORD_NOTIFY}" = true ] ; then
        discord_webhook -u "${DISCORD_NOTIFY_HOOK_ERROR}" -c "Meta failed to output: $1" --username "Meta Error"
    fi
    cd "${BASEDIR}/${MMC_DIR}"
    git reset --hard HEAD
    exit 1
}

function fail_generic {
    if [ "${DISCORD_NOTIFY}" = true ] ; then
        discord_webhook -u "${DISCORD_NOTIFY_HOOK_ERROR}" -c "Meta failed to $1" --username "Meta Error"
    fi
    exit 1
}

currentDate=`date --iso-8601`

cd "${BASEDIR}/${UPSTREAM_DIR}"
git reset --hard HEAD || fail_generic "git reset upstream"
git checkout ${BRANCH} || fail_generic "git checkout upstream"
cd "${BASEDIR}"

./updateMojang.py || fail_in "Mojang"
./updateForge.py || fail_in "Forge"
./updateNeoforge.py || fail_in "Neoforge"
./updateFabric.py || fail_in "Fabric"
./updateQuilt.py || fail_in "Quilt"
./updateLiteloader.py || fail_in "Liteloader"

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    cd "${BASEDIR}/${UPSTREAM_DIR}"
    git add mojang/version_manifest_v2.json mojang/versions/* mojang/assets/* || fail_in "git add"
    git add forge/*.json forge/version_manifests/*.json forge/installer_manifests/*.json forge/files_manifests/*.json forge/installer_info/*.json || fail_in "git add"
    git add neoforge/*.json neoforge/version_manifests/*.json neoforge/installer_manifests/*.json neoforge/files_manifests/*.json neoforge/installer_info/*.json || fail_in "git add"
    git add fabric/loader-installer-json/*.json fabric/meta-v2/*.json fabric/jars/*.json || fail_in "git add"
    git add quilt/loader-installer-json/*.json quilt/meta-v3/*.json quilt/jars/*.json || fail_in "git add"
    git add liteloader/*.json || fail_in "git add"
    if ! git diff --cached --exit-code ; then
        git commit -a -m "Update ${currentDate}" || fail_in "git commit"
        GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/meta-upstream.key" git push || fail_generic "git push upstream"
    fi
    cd "${BASEDIR}"
fi

cd "${BASEDIR}/${MMC_DIR}"
git reset --hard HEAD || fail_generic "git reset multimc"
git checkout ${BRANCH} || fail_generic "git checkout multimc"
cd "${BASEDIR}"

./generateMojang.py || fail_out "Mojang"
./generateForge.py || fail_out "Forge"
./generateNeoforge.py || fail_out "Neoforge"
./generateFabric.py || fail_out "Fabric"
./generateQuilt.py || fail_out "Quilt"
./generateLiteloader.py || fail_out "Liteloader"
./index.py || fail_out "Generating Index"

if [ "${DEPLOY_TO_GIT}" = true ] ; then
    cd "${BASEDIR}/${MMC_DIR}"
    git add index.json org.lwjgl/* net.minecraft/* || fail_out "git add"
    git add net.minecraftforge/* || fail_out "git add"
    git add net.neoforged/* || fail_out "git add"
    git add net.fabricmc.fabric-loader/* net.fabricmc.intermediary/* || fail_out "git add"
    git add org.quiltmc.quilt-loader/* || fail_out "git add"
    git add com.mumfrey.liteloader/* || fail_out "git add"
    if [ -d "org.lwjgl3" ]; then
        git add org.lwjgl3/* || fail_out "git add"
    fi

    if ! git diff --cached --exit-code ; then
        git commit -a -m "Update ${currentDate}" || fail_out "git commit"
        GIT_SSH_COMMAND="ssh -i ${BASEDIR}/config/meta-multimc.key" git push || fail_generic "git push multimc"
    fi
fi

if [ "${UPDATE_FORGE_MAVEN}" = true ] ; then
    echo "Updating the copy of Forge maven"
    cd "${BASEDIR}"
    ./enumerateForge.py || fail_generic "Enumerate Forge"
    if [ "${DEPLOY_FORGE_MAVEN}" = true ] ; then
        chown -RL ${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP} ${BASEDIR}/forgemaven/
        if [ "${DEPLOY_FORGE_MAVEN_S3}" = true ] ; then
            s3cmd -c ${BASEDIR}/config/s3cmd.cfg --exclude=".git*" --delete-removed sync ${BASEDIR}/forgemaven/ ${S3_FORGE_MAVEN} || fail_generic "Deploy Forge Maven to S3"
        fi
    fi
fi

cd "${BASEDIR}"
if [ "${DEPLOY_TO_FOLDER}" = true ] ; then
    DEPLOY_FOLDER_var="DEPLOY_FOLDER_$MODE"
    DEPLOY_FOLDER="${!DEPLOY_FOLDER_var}"
    echo "Deploying to ${DEPLOY_FOLDER}"
    rsync -rvog --chown=${DEPLOY_FOLDER_USER}:${DEPLOY_FOLDER_GROUP} --exclude=.git ${BASEDIR}/${MMC_DIR}/ ${DEPLOY_FOLDER}
fi
if [ "${DEPLOY_TO_S3}" = true ] ; then
    s3cmd -c ${BASEDIR}/config/s3cmd.cfg --exclude=".git*" --delete-removed sync ${BASEDIR}/${MMC_DIR}/ ${S3_BUCKET} || fail_generic "Deploy Meta to S3"
fi

if [ "${DISCORD_NOTIFY}" = true ] ; then
    discord_webhook -u "${DISCORD_NOTIFY_HOOK_OK}" -c "Meta update succeeded!" --username "Meta"
fi

exit 0
