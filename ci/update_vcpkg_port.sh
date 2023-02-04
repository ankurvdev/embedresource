#!/bin/bash
set -e
set -o pipefail

commitId=$(git rev-parse HEAD)
shortCommitId=$(git rev-parse --short HEAD)
scriptdir=$(dirname $(readlink -f $0))
portfile=${scriptdir}/vcpkg-additional-ports/embedresource/portfile.cmake
portjson=${scriptdir}/vcpkg-additional-ports/embedresource/vcpkg.json
sha512=$(wget -O - -q  https://github.com/ankurvdev/embedresource/archive/${commitId}.tar.gz | sha512sum -z | cut - -d' ' -f1)

sed -ri "s/set\(commitId [a-f0-9]+\)/set(commitId ${commitId})/g" ${portfile}
sed -ri "s/set\(sha512 [a-f0-9]+\)/set(sha512 ${sha512})/g"       ${portfile}
awk -F'["]' -v OFS='"'  '/"version":/{split($4,a,".");$4=a[1]"."a[2]"."a[3]+1};1'  ${portjson} > ${portjson}.new
mv ${portjson}.new ${portjson}
git diff
git checkout ${commitId}
git rev-parse --short HEAD
git -c user.email="ankur.verma@outlook.com" -c  user.name="Ankur Verma" -C ${scriptdir} commit ${portfile} ${portjson} -m "Update VCPKG Port to ${commitId}"
git checkout -b vcpkg.${shortCommitId}
git push origin vcpkg.${shortCommitId} --set-upstream
git checkout -b vcpkg
git push origin vcpkg --force --set-upstream