find_program(EMBEDRESOURCE_EXECUTABLE embedresource)
find_path(EMBEDRESOURCE_INCLUDE_DIR EmbeddedResource.h HINTS
    "${CMAKE_CURRENT_LIST_DIR}/../../../include"
    "${CMAKE_CURRENT_LIST_DIR}/../../include"
    "${CMAKE_CURRENT_LIST_DIR}/../../include/embedresource"
    "${CMAKE_CURRENT_LIST_DIR}/.."
    REQUIRED
)

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
    cmake_parse_arguments("" "" "TARGET" "RESOURCES;GENERATOR_COMMAND" ${ARGN})

    add_library(${_TARGET} OBJECT)

    foreach (f ${_RESOURCES})
        get_filename_component(tmp ${f} ABSOLUTE)
        list(APPEND depends ${tmp})
    endforeach()

    if (_GENERATOR_COMMAND)
        set(GENERATED_SPECFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${_TARGET}.txt")
        set(GENERATED_CMAKEFILE "${CMAKE_CURRENT_BINARY_DIR}/generated_${_TARGET}.cmake")
        file(CONFIGURE OUTPUT "${GENERATED_CMAKEFILE}"
            CONTENT "execute_process(COMMAND ${_GENERATOR_COMMAND} OUTPUT_FILE \"${GENERATED_SPECFILE}\")"
        )
        add_custom_command(
            OUTPUT "${GENERATED_SPECFILE}"
            COMMAND ${CMAKE_COMMAND} -P "${GENERATED_CMAKEFILE}"
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        )
        list(APPEND depends "${GENERATED_SPECFILE}")
        list(APPEND _RESOURCES "@${GENERATED_SPECFILE}")
    endif()

    set(outdir "${CMAKE_CURRENT_BINARY_DIR}/ressource_${_TARGET}")
    set(out_f "${outdir}/${_TARGET}.cpp")
    file(MAKE_DIRECTORY "${outdir}")

    if ("${_RESOURCES}" STREQUAL "")
        message(FATAL_ERROR "No args supplied to embed_Resource")
    endif()
    

    # For supporting cross-compination mode we dont want to rely on TARGET EmbedResource
    if (NOT EXISTS "${EMBEDRESOURCE_EXECUTABLE}")
        add_custom_command(OUTPUT ${out_f}
            COMMAND embedresource ${out_f} ${_RESOURCES}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            DEPENDS embedresource ${depends}
            COMMENT "Building binary file for embedding ${out_f}")
    else()
        add_custom_command(OUTPUT ${out_f}
            COMMAND ${EMBEDRESOURCE_EXECUTABLE} ${out_f} ${_RESOURCES}
            WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
            DEPENDS ${EMBEDRESOURCE_EXECUTABLE} ${depends}
            COMMENT "Building binary file for embedding ${out_f}")
    endif()

    target_sources(${_TARGET} PRIVATE ${out_f})
    target_include_directories(${_TARGET} PUBLIC "${EMBEDRESOURCE_INCLUDE_DIR}")
    target_compile_definitions(${_TARGET} PUBLIC HAVE_EMBEDRESOURCE=1)
endfunction()