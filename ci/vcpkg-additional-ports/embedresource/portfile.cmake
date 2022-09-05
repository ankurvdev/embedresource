if (DEFINED ENV{VCPKG_USE_SRC_DIR} AND EXISTS "$ENV{VCPKG_USE_SRC_DIR}")
    get_filename_component(srcpath "$ENV{VCPKG_USE_SRC_DIR}" ABSOLUTE)
    set(SOURCE_PATH "${srcpath}")
elseif (DEFINED ENV{VCPKG_USE_GIT_REPO} AND NOT "$ENV{VCPKG_USE_GIT_REPO}" STREQUAL "")
    set(gitinfo "$ENV{VCPKG_USE_GIT_REPO}")
    list(GET gitinfo 0 giturl)
    list(GET gitinfo 1 commitId)
    vcpkg_from_git(
        OUT_SOURCE_PATH SOURCE_PATH
        URL ${giturl}
        REF ${commitId}
    )
else()
    # sha512sum can be obtained using
    # wget -O - -q  https://github.com/ankurdev/embedresource/archive/b6429f8b92947273a5e66d5f10210b960616a89d.tar.gz | sha512sum 
    set(commitId 58e2f40455a613546b374b6f5c02c8c986bacfd5)
    set(sha512 a52a0c443fb3e096f7e28924dccb6cd4290aeef2b660cddc3f284646e8bbc8bfd2384c7a54406a83c18591b8b33b8465c09fe6d4769438a217f127c6bb652218)
    vcpkg_from_github(
        OUT_SOURCE_PATH SOURCE_PATH
        REPO ankurvdev/embedresource
        REF ${commitId}
        SHA512 ${sha512}
        HEAD_REF master)
endif()
# Dont use these these are older version
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

