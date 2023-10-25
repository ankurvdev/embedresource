#!/bin/bash
set -e
set -o pipefail

scriptdir=$(dirname $(readlink -f $0))
commitId=$(git -C ${scriptdir} rev-parse HEAD)
shortCommitId=$(git -C ${scriptdir} rev-parse --short HEAD)
project=$(git -C ${scriptdir} config remote.origin.url | grep -oE 'ankurvdev/[^.]*' | cut - -d '/' -f2)

echo "${scriptdir} ${project} ${commitId} ${shortCommitId}"

portfile=$(ls ${scriptdir}/vcpkg-additional-ports/*${project}*/portfile.cmake)
portjson=$(ls ${scriptdir}/vcpkg-additional-ports/*${project}*/vcpkg.json)
sha512=$(wget -O - -q  https://github.com/ankurvdev/${project}/archive/${commitId}.tar.gz | sha512sum -z | cut - -d' ' -f1)
echo "SHA512:${sha512}"

sed -ri "s/REF \"v\$\{VERSION\}\"/REF \"${commitId}\"/" ${portfile}
sed -ri "s/SHA512 [0-9a-z]+/SHA512 ${sha512}/g" ${portfile}
awk -F'["]' -v OFS='"'  '/"version":/{split($4,a,".");$4=a[1]"."a[2]"."a[3]+1};1'  ${portjson} > ${portjson}.new
mv ${portjson}.new ${portjson}
git -C ${scriptdir} diff
git -C ${scriptdir} checkout ${commitId}
git -C ${scriptdir} rev-parse --short HEAD
git -c user.email="ankur.verma@outlook.com" -c  user.name="Ankur Verma" -C ${scriptdir} commit ${portfile} ${portjson} -m "Update VCPKG Port to ${commitId}"
git -C ${scriptdir} checkout -b vcpkg.${shortCommitId}
git -C ${scriptdir} checkout -b vcpkg
if [[ "$1" == "push" ]]; then
    git -C ${scriptdir} push origin vcpkg.${shortCommitId} --set-upstream
    git -C ${scriptdir} push origin vcpkg --force --set-upstream
fi
