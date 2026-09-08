#!/bin/bash
# cppforge-sync
set -e
set -o pipefail

scriptdir=$(dirname $(readlink -f $0))
vcpkgdir=${1:-${scriptdir}/vcpkg.tmp}

git -C ${scriptdir} fetch --all --prune
git -C ${scriptdir} checkout origin/vcpkg
commitId=$(git -C ${scriptdir} rev-parse HEAD)
shortCommitId=$(git -C ${scriptdir} rev-parse --short HEAD)
project=$(git -C ${scriptdir} config remote.origin.url | grep -oE 'ankurvdev/[^.]*' | cut -d '/' -f2 -)

echo "${scriptdir} ${project} ${commitId} ${shortCommitId}"
if [ -e ${scriptdir}/vcpkg-additional-ports/${project}/portfile.cmake ]; then
	portfile=${scriptdir}/vcpkg-additional-ports/${project}/portfile.cmake
	portjson=${scriptdir}/vcpkg-additional-ports/${project}/vcpkg.json
else
	portfile=${scriptdir}/vcpkg-additional-ports/ankurvdev-${project}/portfile.cmake
	portjson=${scriptdir}/vcpkg-additional-ports/ankurvdev-${project}/vcpkg.json
fi

vcpkgurl=$(git -C ${scriptdir} config remote.origin.url | grep -oE '.*ankurvdev')/vcpkg
echo "${vcpkgurl} ${vcpkgdir}"

if [ ! -e ${vcpkgdir} ]; then
	git clone ${vcpkgurl} ${vcpkgdir} --depth 1 -b lkg_commit
	git -C ${vcpkgdir} config --add remote.origin.fetch +refs/heads/patches/*:refs/remotes/origin/patches/*
	git -C ${vcpkgdir} fetch
fi

git -C ${vcpkgdir} checkout patches/${project} || git -C ${vcpkgdir} checkout patches/ankurvdev-${project}
if [ -e ${vcpkgdir}/ports/${project}/portfile.cmake ]; then
	cp ${portfile} ${vcpkgdir}/ports/${project}/portfile.cmake
	cp ${portjson} ${vcpkgdir}/ports/${project}/vcpkg.json
else
	cp ${portfile} ${vcpkgdir}/ports/ankurvdev-${project}/portfile.cmake
	cp ${portjson} ${vcpkgdir}/ports/ankurvdev-${project}/vcpkg.json
fi
git -C ${vcpkgdir} diff
git -c user.email="ankur.verma@outlook.com" -c  user.name="Ankur Verma" -C ${vcpkgdir} commit -a -m "Update VCPKG Port to ${commitId}"
git -C ${vcpkgdir} log
git -C ${vcpkgdir} diff lkg_commit..HEAD

if [[ "$1" == "push" ]]; then
    git -C ${vcpkgdir} push
fi
