# On Android cross compilation systems avoid the crosscompiled exe
include(FetchContent)

find_program(EMBEDRESOURCE_EXECUTABLE embedresource NO_CMAKE_PATH)
if (NOT EXISTS "${EMBEDRESOURCE_EXECUTABLE}")
    find_program(EMBEDRESOURCE_EXECUTABLE embedresource NO_CACHE)
endif()
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
    set(EMBEDRESOURCE_SOURCE_DIR "${CMAKE_CURRENT_LIST_DIR}/..")
endif()

FetchContent_Declare(
    EMBEDRESOURCE
    GIT_REPOSITORY https://github.com/ankurvdev/embedresource.git
    GIT_TAG        6617a80578bf159996447abf09fceb0de61c662b
)

function(build_embedresource)
    if (PROJECT_NAME STREQUAL embedresource OR EMBEDRESOURCE_INSTALL)
        message(FATAL_ERROR "Something is wrong:${EMBEDRESOURCE_SOURCE_DIR}::${PROJECT_NAME}")
    endif()

    if (NOT EXISTS "${EMBEDRESOURCE_SOURCE_DIR}")
        FetchContent_MakeAvailable(EMBEDRESOURCE)
    endif()
    set(EMBEDRESOURCE_INSTALL OFF CACHE BOOL "Do not install embedresource bits")
    file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/embedresource-build")
    set(CMD "${CMAKE_COMMAND}" "-DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/embedresource-install")
    if (CMAKE_GENERATOR)
        list(APPEND CMD "-G" "${CMAKE_GENERATOR}")
    endif()

    if (CMAKE_CROSSCOMPILING)
        unset(ENV{CMAKE_CXX_COMPILER})
        unset(ENV{CMAKE_C_COMPILER})
        unset(ENV{CC})
        unset(ENV{CXX})
    endif()


    list(APPEND CMD "${EMBEDRESOURCE_SOURCE_DIR}")

    execute_process(COMMAND ${CMD} WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/embedresource-build")
    execute_process(COMMAND "${CMAKE_COMMAND}" --build  "${CMAKE_CURRENT_BINARY_DIR}/embedresource-build")
    execute_process(COMMAND "${CMAKE_COMMAND}" --install "${CMAKE_CURRENT_BINARY_DIR}/embedresource-build" --prefix "${CMAKE_CURRENT_BINARY_DIR}/embedresource-install")
endfunction()

if (NOT EXISTS "${EMBEDRESOURCE_EXECUTABLE}")
    if (NOT TARGET embedresource)
        if (NOT CMAKE_CROSSCOMPILING)
            add_subdirectory("${EMBEDRESOURCE_SOURCE_DIR}" embedresource)
        else()
            build_embedresource()
            find_program(EMBEDRESOURCE_EXECUTABLE REQUIRED NAMES embedresource PATHS "${CMAKE_CURRENT_BINARY_DIR}/embedresource-install/bin")
        endif()
    else()
        set(EMBEDRESOURCE_EXECUTABLE embedresource)
    endif()
endif()

macro(target_add_resource target name)
    _target_add_resource(${target} ${name} ${ARGN})
endmacro()

function(_target_add_resource target name)
    set(outdir "${CMAKE_CURRENT_BINARY_DIR}/ressource_${target}")
    set(out_f "${outdir}/${name}.cpp")
    file(MAKE_DIRECTORY "${outdir}")
    if ("${ARGN}" STREQUAL "")
        message(FATAL_ERROR "No args supplied to embed_Resource")
    endif()

    foreach (f ${ARGN})
        get_filename_component(tmp ${f} ABSOLUTE)
        list(APPEND inputs ${tmp})
    endforeach()
    list(REMOVE_DUPLICATES inputs)

    # For supporting cross-compination mode we dont want to rely on TARGET EmbedResource
    if (NOT EXISTS "${EMBEDRESOURCE_EXECUTABLE}")
        add_custom_command(OUTPUT ${out_f}
            COMMAND embedresource ${out_f} ${inputs}
            DEPENDS embedresource ${inputs}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            COMMENT "Building binary file for embedding ${out_f}")
    else()
        add_custom_command(OUTPUT ${out_f}
            COMMAND ${EMBEDRESOURCE_EXECUTABLE} ${out_f} ${inputs}
            DEPENDS ${EMBEDRESOURCE_EXECUTABLE} ${inputs}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            COMMENT "Building binary file for embedding ${out_f}")
    endif()

    target_sources(${target} PRIVATE ${out_f})
    target_include_directories(${target} PUBLIC "${EMBEDRESOURCE_INCLUDE_DIR}")
    target_compile_definitions(${target} PUBLIC HAVE_EMBEDRESOURCE=1)
endfunction()

function(add_resource_library)
    cmake_parse_arguments("" "" "TARGET" "RESOURCES;GENERATOR_COMMAND;GENERATOR_DEPEND;GENERATOR_SPECFILE" ${ARGN})

    add_library(${_TARGET} OBJECT)

    foreach (f ${_RESOURCES})
        get_filename_component(tmp ${f} ABSOLUTE)
        list(APPEND depends ${tmp})
    endforeach()

    if (_GENERATOR_SPECFILE AND _GENERATOR_COMMAND)
        message(FATAL_ERROR "GENERATOR_SPECFILE and GENERATOR_COMMAND are mutually exclusive")
    endif()
    if (_GENERATOR_COMMAND)
        set(_GENERATOR_SPECFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${_TARGET}.txt")
        set(GENERATED_CMAKEFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${_TARGET}.cmake")
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

    set(outdir "${CMAKE_CURRENT_BINARY_DIR}/ressource_${_TARGET}")
    set(out_f "${outdir}/${_TARGET}.cpp")
    file(MAKE_DIRECTORY "${outdir}")

    if ("${_RESOURCES}" STREQUAL "")
        message(FATAL_ERROR "No args supplied to embed_Resource")
    endif()
    

    # For supporting cross-compination mode we dont want to rely on TARGET EmbedResource
    if (NOT EXISTS "${EMBEDRESOURCE_EXECUTABLE}")
        if (NOT TARGET embedresource)
            message(FATAL_ERROR "embedresource target not found")
        endif()
        add_custom_command(OUTPUT "${out_f}"
            COMMAND embedresource "${out_f}" ${_RESOURCES}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            DEPENDS embedresource ${depends}
            COMMENT "Building binary file for embedding ${out_f}")
    else()
        add_custom_command(OUTPUT "${out_f}"
            COMMAND "${EMBEDRESOURCE_EXECUTABLE}" "${out_f}" ${_RESOURCES}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            DEPENDS "${EMBEDRESOURCE_EXECUTABLE}" ${depends}
            COMMENT "Building binary file for embedding ${out_f}")
    endif()

    target_sources(${_TARGET} PRIVATE "${out_f}")
    target_include_directories(${_TARGET} PUBLIC "${EMBEDRESOURCE_INCLUDE_DIR}")
    target_compile_definitions(${_TARGET} PUBLIC HAVE_EMBEDRESOURCE=1)
endfunction()
