# sha512sum can be obtained using
# wget -O - -q  https://github.com/ankurdev/embedresource/archive/b6429f8b92947273a5e66d5f10210b960616a89d.tar.gz | sha512sum 
set(commitId 3cfb818d85b7b84dbe0b700101efe9888f8e2c81)
set(sha512 9aebaec800199f2ff3f08a2e31f283ba8077a5adc800698c103400dd6ae33a87e41e308ef5c777b4c58e5f3cc05b16d24bfe504d068037237cc24516ef6ac890)
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

