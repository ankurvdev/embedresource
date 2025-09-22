# On Android cross compilation systems avoid the crosscompiled exe
include(FetchContent)
include(${CMAKE_CURRENT_LIST_DIR}/FindOrBuildTool.cmake)

# On Android cross compilation systems cmake will exclusively search for sysroot-ed paths
if (EXISTS ${CMAKE_CURRENT_LIST_DIR}/../EmbeddedResource.h)
    set(EMBEDRESOURCE_INCLUDE_DIR "${CMAKE_CURRENT_LIST_DIR}/.." CACHE PATH "Embedded Resource header")
else()
    find_path(EMBEDRESOURCE_INCLUDE_DIR EmbeddedResource.h HINTS
        "${CMAKE_CURRENT_LIST_DIR}/../../../"
        "${CMAKE_CURRENT_LIST_DIR}/../../"
        "${CMAKE_CURRENT_LIST_DIR}/../"
        PATH_SUFFIXES include embedresource include/embedresource
        REQUIRED
    )
endif()

if (EXISTS "${CMAKE_CURRENT_LIST_DIR}/../embedresource.cpp")
    set(embedresource_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/..")
endif()

FetchContent_Declare(
    embedresource
    GIT_REPOSITORY https://github.com/ankurvdev/embedresource.git
    GIT_TAG        main
)

macro(target_add_resource target)
    FindOrBuildTool(embedresource)
    _target_add_resource(${target} out_f ${ARGN})
    target_sources(${target} PRIVATE ${out_f})
    target_include_directories(${target} PRIVATE "${EMBEDRESOURCE_INCLUDE_DIR}")
endmacro()

function(_target_add_resource target outvarname)
    cmake_parse_arguments("" "" "NAME_ENCODING;RESOURCE_COLLECTION_NAME" "RESOURCES;GENERATOR_COMMAND;GENERATOR_DEPEND;GENERATOR_SPECFILE" ${ARGN})
    if (NOT DEFINED _RESOURCE_COLLECTION_NAME)
        set(_RESOURCE_COLLECTION_NAME "${target}")
    endif()
    string(TOUPPER "${_NAME_ENCODING}" _NAME_ENCODING)
    if ("${_NAME_ENCODING}" STREQUAL "")
        set(_NAME_ENCODING "UTF8")
    endif()
    if ((NOT "${_NAME_ENCODING}" STREQUAL "UTF8") AND (NOT "${_NAME_ENCODING}" STREQUAL "UTF16"))
        message(FATAL_ERROR "NAME_ENCODING must be UTF8 or UTF16")
    endif()
    target_compile_definitions(${target} PRIVATE "EMBEDRESOURCE_NAME_ENCODING_${_NAME_ENCODING}=1")
    foreach (f ${_RESOURCES})
        get_filename_component(tmp ${f} ABSOLUTE)
        list(APPEND depends ${tmp})
    endforeach()

    if (_GENERATOR_SPECFILE AND _GENERATOR_COMMAND)
        message(FATAL_ERROR "GENERATOR_SPECFILE and GENERATOR_COMMAND are mutually exclusive")
    endif()
    if (_GENERATOR_COMMAND)
        set(_GENERATOR_SPECFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${target}.txt")
        set(GENERATED_CMAKEFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${target}.cmake")
        file(CONFIGURE OUTPUT "${GENERATED_CMAKEFILE}"
            CONTENT "execute_process(COMMAND ${_GENERATOR_COMMAND} OUTPUT_FILE \"${_GENERATOR_SPECFILE}\")"
        )
        add_custom_command(
            OUTPUT "${_GENERATOR_SPECFILE}"
            COMMAND ${CMAKE_COMMAND} -P "${GENERATED_CMAKEFILE}"
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            DEPENDS ${_GENERATOR_DEPEND} "${GENERATED_CMAKEFILE}"
        )
        list(APPEND depends ${_GENERATOR_DEPEND} "${GENERATED_CMAKEFILE}")
    endif()
    if (_GENERATOR_SPECFILE)
        list(APPEND depends "${_GENERATOR_SPECFILE}")
        list(APPEND _RESOURCES "@${_GENERATOR_SPECFILE}")
    endif()

    set(outdir "${CMAKE_CURRENT_BINARY_DIR}/resource_${target}")
    set(out_f "${outdir}/${_RESOURCE_COLLECTION_NAME}.cpp")
    file(MAKE_DIRECTORY "${outdir}")

    if ("${_RESOURCES}" STREQUAL "")
        message(FATAL_ERROR "No args supplied to embed_Resource")
    endif()


    # For supporting cross-compination mode we dont want to rely on TARGET EmbedResource
    add_custom_command(OUTPUT "${out_f}"
        COMMAND "${embedresource_EXECUTABLE}" "${out_f}" ${_RESOURCES}
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        DEPENDS "${embedresource_EXECUTABLE}" ${depends}
        COMMENT "Building binary file for embedding ${out_f}")
    set(${outvarname} "${out_f}" PARENT_SCOPE)
endfunction()

function(add_resource_library target libkind)
    FindOrBuildTool(embedresource)
    add_library(${target} ${libkind})
    _target_add_resource(${target} out_f ${ARGN})
    target_sources(${target} PRIVATE ${out_f})
    set_property(TARGET ${target} PROPERTY POSITION_INDEPENDENT_CODE ON)
    target_include_directories(${target} PUBLIC "${EMBEDRESOURCE_INCLUDE_DIR}")
endfunction()
