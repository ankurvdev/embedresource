# sha512sum can be obtained using
# wget -O - -q  https://github.com/ankurdev/embedresource/archive/b6429f8b92947273a5e66d5f10210b960616a89d.tar.gz | sha512sum 
set(commitId acbb1736f46da70bb06d33c53da5bd2dcdc2fc85)
set(sha512 06c1692f89ed37db8978afb6d878b1882d0e357bc31f5fbdb6a8b6f07041b152d12379ece617a851483d1582d0c2af5443877117f3da9cc0ca6919dfdcfd81fe)
vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ankurvdev/embedresource
    REF ${commitId}
    SHA512 ${sha512}
    HEAD_REF master)

if(NOT TARGET_TRIPLET STREQUAL HOST_TRIPLET)
    vcpkg_add_to_path(PREPEND "${CURRENT_HOST_INSTALLED_DIR}/tools")
endif()

vcpkg_cmake_configure(
    SOURCE_PATH ${SOURCE_PATH}
)

vcpkg_cmake_install()
vcpkg_copy_pdbs()

# Handle copyright
file(INSTALL ${SOURCE_PATH}/LICENSE DESTINATION ${CURRENT_PACKAGES_DIR}/share/${PORT} RENAME copyright)
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug")
file(RENAME "${CURRENT_PACKAGES_DIR}/bin" "${CURRENT_PACKAGES_DIR}/tools")

file(READ "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake" config_contents)
file(WRITE "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake"
"find_program(
    EMBEDRESOURCE_EXECUTABLE embedresource 
    PATHS 
        \"\${CMAKE_CURRENT_LIST_DIR}/../../../${HOST_TRIPLET}/tools\"
    NO_DEFAULT_PATH
    REQUIRED)
${config_contents}"
)
