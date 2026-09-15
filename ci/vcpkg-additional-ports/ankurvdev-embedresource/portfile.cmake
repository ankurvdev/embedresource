vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ankurvdev/embedresource
    REF "f7fc60f6b987897aedd75cf7d60058e68938c1a3"
    SHA512 579ad94c79fefa694fc315d3204a73fb3912f4ff34909e3684c9c4a5826b5712777beba4ff8c43436d1a0e81a06bd7af2bf54f9f5d0fd1f58551a5bf7b69e125
    HEAD_REF main)

vcpkg_cmake_configure(
    SOURCE_PATH ${SOURCE_PATH}
    OPTIONS
        -DBUILD_TESTING=OFF
)

vcpkg_cmake_install()
vcpkg_copy_pdbs()

# Handle copyright
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug")
if(HOST_TRIPLET STREQUAL TARGET_TRIPLET) # Otherwise fails on wasm32-emscripten
    vcpkg_copy_tools(TOOL_NAMES embedresource AUTO_CLEAN)
else()
    file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/bin")
endif()

file(READ "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake" config_contents)
file(WRITE "${CURRENT_PACKAGES_DIR}/share/embedresource/EmbedResourceConfig.cmake"
"find_program(
    embedresource_EXECUTABLE embedresource
    PATHS
        \"\${CMAKE_CURRENT_LIST_DIR}/../../../${HOST_TRIPLET}/tools/${PORT}\"
    NO_DEFAULT_PATH
    REQUIRED)
${config_contents}"
)
