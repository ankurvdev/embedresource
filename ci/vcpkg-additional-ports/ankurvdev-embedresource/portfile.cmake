vcpkg_from_github(
    OUT_SOURCE_PATH SOURCE_PATH
    REPO ankurvdev/embedresource
    REF "1029bce4d2cd3d2b2a899a1951cf8aab0a096b58"
    SHA512 8f0a86c85fd2e9a6ab86d2e0072a9d1cfb670118e9af454098a4be929467e10f7212bff484f830997cf14a409fa0c905ef43204db16b0d6df79b818126319c7c
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
