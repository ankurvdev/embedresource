cmake_minimum_required(VERSION 3.12)
option(USE_SUBDIRECTORY "Build Test" OFF)
if (NOT USE_SUBDIRECTORY)
    if(NOT EXISTS "${VCPKG_ROOT}")
        message(FATAL_ERROR "Please run with -DVCPKG_ROOT=<vcpkg-root> ${VCPKG_ROOT} not found")
    endif()
    include(${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake)
endif()

project(embedresource-test VERSION 0.0.1)

set(CMAKE_CXX_STANDARD 20)

if (USE_SUBDIRECTORY)
    add_subdirectory(../.. embedresource)
else()
    find_package(EmbedResource REQUIRED)
endif()

add_executable(sample_test main.cpp)
add_resource_library(TARGET testdata RESOURCES main.cpp GENERATOR_COMMAND echo "CMakeLists.txt")
target_link_libraries(sample_test PRIVATE testdata)

enable_testing()
add_test(NAME sample_test COMMAND sample_test)