# sha512sum can be obtained using
# wget -O - -q  https://github.com/ankurdev/embedresource/archive/b6429f8b92947273a5e66d5f10210b960616a89d.tar.gz | sha512sum 
set(commitId ffbfbff32fca57ce19eca7a6c9a0baca0cfc7081)
set(sha512 b7b68bbe147b21bad323845205652ca3b58945ce00a703d001f46abee903a065687c48ecf2913d6e274e051e9844570815d47f2014842f93a20bfc8dc319ee49)
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ankurvdev/embedresource
    REF ${commitId}
    SHA512 ${sha512}
    HEAD_REF master)

if(NOT TARGET_TRIPLET STREQUAL HOST_TRIPLET)
    vcpkg_add_to_path(PREPEND "${CURRENT_HOST_INSTALLED_DIR}/tools")
endif()

vcpkg_configure_cmake(
    SOURCE_PATH ${SOURCE_PATH}
    PREFER_NINJA
)

vcpkg_install_cmake()
vcpkg_copy_pdbs()

# Handle copyright
file(INSTALL ${SOURCE_PATH}/LICENSE DESTINATION ${CURRENT_PACKAGES_DIR}/share/${PORT} RENAME copyright)
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug")
file(RENAME "${CURRENT_PACKAGES_DIR}/bin" "${CURRENT_PACKAGES_DIR}/tools")

