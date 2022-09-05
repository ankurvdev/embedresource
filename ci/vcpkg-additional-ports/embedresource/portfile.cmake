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
    set(commitId fab682fdc383a5a2639323ee7c75d911c98129c1)
    set(sha512 9b07782d3cc842e183857e48bfc77a3437c6a4c7fd18e3a550d72afdb4445863b4f3488edbe1481bebfe94034f79f9fd84c3be9fa1c2c5b3ce3752f936f24ead)
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

