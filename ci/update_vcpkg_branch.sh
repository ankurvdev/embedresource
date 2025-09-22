#!/bin/bash
# cppforge-sync
set -e
set -o pipefail

scriptdir=$(dirname $(readlink -f $0))

git -C ${scriptdir} fetch --all --prune
git -C ${scriptdir} checkout origin/vcpkg
commitId=$(git -C ${scriptdir} rev-parse HEAD)
shortCommitId=$(git -C ${scriptdir} rev-parse --short HEAD)
project=$(git -C ${scriptdir} config remote.origin.url | grep -oE 'patches/[^.]*' | cut - -d '/' -f2)

echo "${scriptdir} ${project} ${commitId} ${shortCommitId}"

portfile=${scriptdir}/vcpkg-additional-ports/${project}/portfile.cmake
portjson=${scriptdir}/vcpkg-additional-ports/${project}/vcpkg.json

vcpkgurl=$(git -C ${scriptdir} config remote.origin.url | grep -oE '.*ankurvdev')/vcpkg
vcpkgdir=${scriptdir}/vcpkg.tmp
echo "${vcpkgurl} ${vcpkgdir}"
git clone ${vcpkgurl} ${vcpkgdir} --depth 1 -b ankurv/${project}
cp ${portfile} ${vcpkgdir}/ports/${project}/portfile.cmake
cp ${portjson} ${vcpkgdir}/ports/${project}/vcpkg.json
git -C ${vcpkgdir} diff
git -c user.email="ankur.verma@outlook.com" -c  user.name="Ankur Verma" -C ${vcpkgdir} commit -a -m "Update VCPKG Port to ${commitId}"
git -C ${vcpkgdir} log

if [[ "$1" == "push" ]]; then
    git -C ${vcpkgdir} push
fi
