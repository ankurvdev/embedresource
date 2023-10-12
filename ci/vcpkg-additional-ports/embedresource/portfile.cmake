# sha512sum can be obtained using
# wget -O - -q  https://github.com/ankurdev/embedresource/archive/b6429f8b92947273a5e66d5f10210b960616a89d.tar.gz | sha512sum 
set(commitId 5c657de499afb0d806a7bc1cc32001bc34547869)
set(sha512 263faf8b8f2616fe8688aa9c511a9ace7055aa66fb855424faa91907b60e16e41f3a667895b673565da37f695b26e630be20d2ea94a395676ef11991a0f5cf69)
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

file(READ "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake" config_contents)
file(WRITE "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake"
"find_program(EMBEDRESOURCE_EXECUTABLE embedresource PATHS \"\${CMAKE_CURRENT_LIST_DIR}/../../../${HOST_TRIPLET}/tools/embedresource\" REQUIRED)
\${config_contents}")