cmake_minimum_required(VERSION 3.12)

if(DEFINED VCPKG_ROOT)
    include(${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake)
endif()

project(embedresource-test VERSION 0.0.1)

set(CMAKE_CXX_STANDARD 17)

if(DEFINED VCPKG_ROOT)
    find_package(EmbedResource REQUIRED)
else()
    if (NOT TARGET embedresource)
        add_subdirectory(../.. embedresource)
    endif()
endif()

file(SIZE "${CMAKE_CURRENT_LIST_DIR}/main.cpp" MAIN_CPP_FILE_SIZE)
file(SIZE "${CMAKE_CURRENT_LIST_DIR}/CMakeLists.txt" CMAKELISTS_TXT_FILE_SIZE)

add_resource_library(sample_test_resources OBJECT RESOURCE_COLLECTION_NAME testdata1 RESOURCES main.cpp GENERATOR_COMMAND echo "CMakeLists.txt" GENERATOR_DEPEND CMakeLists.txt)
add_resource_library(testdata3 OBJECT RESOURCES main.cpp)

macro(setup_target target)
    target_add_resource(${target} RESOURCE_COLLECTION_NAME testdata2 RESOURCES main.cpp ${ARGN})
    get_target_property(type ${target} TYPE)
    if ("${type}" STREQUAL "STATIC_LIBRARY")
        target_link_libraries(${target} PRIVATE $<BUILD_INTERFACE:sample_test_resources> $<BUILD_INTERFACE:testdata3>)
    else()
        target_link_libraries(${target} PRIVATE sample_test_resources testdata3)
    endif()

    target_compile_definitions(${target} PRIVATE MAIN_CPP_FILE_SIZE=${MAIN_CPP_FILE_SIZE})
    target_compile_definitions(${target} PRIVATE CMAKELISTS_TXT_FILE_SIZE=${CMAKELISTS_TXT_FILE_SIZE})
endmacro()

add_executable(sample_test_exe main.cpp)
setup_target(sample_test_exe)

add_library(sample_test_shlib SHARED main.cpp)
target_compile_features(sample_test_shlib PRIVATE cxx_std_20)
setup_target(sample_test_shlib)

add_library(sample_test_lib STATIC main.cpp)
setup_target(sample_test_lib)

add_executable(sample_test_exe_wide main.cpp)
setup_target(sample_test_exe_wide NAME_ENCODING UTF16)

add_library(sample_test_shlib_wide SHARED main.cpp)
target_compile_features(sample_test_shlib_wide PRIVATE cxx_std_20)
setup_target(sample_test_shlib_wide NAME_ENCODING UTF16)

install(TARGETS sample_test_shlib EXPORT sample_test_shlib)
install(EXPORT sample_test_shlib  FILE sampleTargets.cmake DESTINATION cmake)

install(TARGETS sample_test_lib EXPORT sample_test_lib)
install(EXPORT sample_test_lib  FILE sampleTargets.cmake DESTINATION cmake)

enable_testing()
add_test(NAME sample_test_exe COMMAND sample_test_exe)
add_test(NAME sample_test_exe_wide COMMAND sample_test_exe_wide)


