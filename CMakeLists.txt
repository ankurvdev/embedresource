cmake_minimum_required(VERSION 3.12)
include(CMakePackageConfigHelpers)

project(embedresource VERSION 0.0.1)

option(EMBEDRESOURCE_INSTALL "Install EmbedResource Binaries and Files" ON)
set(CMAKE_CXX_STANDARD 20)
add_executable(embedresource embedresource.cpp)
set_target_properties(embedresource PROPERTIES PUBLIC_HEADER "EmbeddedResource.h")

configure_package_config_file(cmake/EmbedResourceConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/generated/EmbedResourceConfig.cmake
    INSTALL_DESTINATION share/embedresource
)

include(cmake/EmbedResourceTargets.cmake) # For add_subdirectory mode

if (EMBEDRESOURCE_INSTALL)
install(
    TARGETS embedresource
    EXPORT EmbedResourceTargets
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
    PUBLIC_HEADER DESTINATION include/embedresource
)

install(FILES
    cmake/EmbedResourceTargets.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/generated/EmbedResourceConfig.cmake
    DESTINATION share/embedresource
)

# install(EXPORT EmbedResourceTargets
#     NAMESPACE embedresource
#     DESTINATION share/embedresource
# )
endif()

#
# CPACK
#
set (CPACK_GENERATOR ZIP)
set (CPACK_PACKAGE_NAME                 ${PROJECT_NAME})
set (CPACK_PACKAGE_VENDOR               "Ankur Verma")
set (CPACK_PACKAGE_DESCRIPTION_SUMMARY  "EmbedResource")
set (CPACK_PACKAGE_VERSION              ${PROJECT_VERSION})

include(CPack)
