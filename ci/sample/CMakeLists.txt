cmake_minimum_required(VERSION 3.12)

if(DEFINED VCPKG_ROOT)
    include(${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake)
endif()

project(embedresource-test VERSION 0.0.1)

set(CMAKE_CXX_STANDARD 17)

if(DEFINED VCPKG_ROOT)
    find_package(EmbedResource REQUIRED)
else()
    add_subdirectory(../.. embedresource)
endif()

file(SIZE "${CMAKE_CURRENT_LIST_DIR}/main.cpp" MAIN_CPP_FILE_SIZE)
file(SIZE "${CMAKE_CURRENT_LIST_DIR}/CMakeLists.txt" CMAKELISTS_TXT_FILE_SIZE)

add_resource_library(sample_test_resources OBJECT RESOURCE_COLLECTION_NAME testdata1 RESOURCES main.cpp GENERATOR_COMMAND echo "CMakeLists.txt" GENERATOR_DEPEND CMakeLists.txt)
add_resource_library(testdata3 OBJECT RESOURCES main.cpp)

add_executable(sample_test_exe main.cpp)
target_add_resource(sample_test_exe RESOURCE_COLLECTION_NAME testdata2 RESOURCES main.cpp)
target_link_libraries(sample_test_exe PRIVATE sample_test_resources testdata3)
target_compile_definitions(sample_test_exe PRIVATE MAIN_CPP_FILE_SIZE=${MAIN_CPP_FILE_SIZE})
target_compile_definitions(sample_test_exe PRIVATE CMAKELISTS_TXT_FILE_SIZE=${CMAKELISTS_TXT_FILE_SIZE})

add_library(sample_test_shlib SHARED main.cpp)
target_compile_features(sample_test_shlib PRIVATE cxx_std_20)

target_add_resource(sample_test_shlib RESOURCE_COLLECTION_NAME testdata2 RESOURCES main.cpp)
target_link_libraries(sample_test_shlib PRIVATE sample_test_resources testdata3)
target_compile_definitions(sample_test_shlib PRIVATE MAIN_CPP_FILE_SIZE=${MAIN_CPP_FILE_SIZE})
target_compile_definitions(sample_test_shlib PRIVATE CMAKELISTS_TXT_FILE_SIZE=${CMAKELISTS_TXT_FILE_SIZE})

install(TARGETS sample_test_shlib EXPORT sample_test_shlib)
install(EXPORT sample_test_shlib  FILE sampleTargets.cmake DESTINATION cmake)

enable_testing()
add_test(NAME sample_test_exe COMMAND sample_test_exe)


