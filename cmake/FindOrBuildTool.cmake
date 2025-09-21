# cppforge-sync
include_guard()

function(BuildTool toolname)
    if (PROJECT_NAME STREQUAL ${toolname} OR ${toolname}_INSTALL)
        message(WARNING "Ignore this message if you're crosscompiling ${toolname}"
        "\n${toolname}_SOURCE_DIR}=${${toolname}_SOURCE_DIR}"
        "\nPROJECT_NAME=${PROJECT_NAME}"
        "\nCMAKE_CROSSCOMPILING=${CMAKE_CROSSCOMPILING}")
    endif()

    if (NOT EXISTS "${${toolname}_SOURCE_DIR}")
        FetchContent_MakeAvailable(${toolname})
    endif()
    set(${toolname}_INSTALL OFF CACHE BOOL "Do not install ${toolname} bits")
    file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-build")
    set(CMD "${CMAKE_COMMAND}"
        "-DBUILD_TESTING=OFF"
        "-DCMAKE_BUILD_TYPE=RelWithDebInfo"
        "-DCMAKE_INSTALL_PREFIX:PATH=${CMAKE_CURRENT_BINARY_DIR}/${toolname}-install")
    if (CMAKE_GENERATOR)
        list(APPEND CMD "-G" "${CMAKE_GENERATOR}")
    endif()

    if (CMAKE_CROSSCOMPILING)
        unset(ENV{CMAKE_CXX_COMPILER})
        unset(ENV{CMAKE_C_COMPILER})
        unset(ENV{CC})
        unset(ENV{CXX})
    endif()


    list(APPEND CMD "${${toolname}_SOURCE_DIR}")

    execute_process(COMMAND_ERROR_IS_FATAL ANY COMMAND ${CMD} WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-build")
    execute_process(COMMAND_ERROR_IS_FATAL ANY COMMAND "${CMAKE_COMMAND}" --build  "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-build")
    execute_process(COMMAND_ERROR_IS_FATAL ANY COMMAND "${CMAKE_COMMAND}" --install "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-build" --prefix "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-install")
endfunction()

function(FindOrBuildTool toolname)
    if (NOT EXISTS "${${toolname}_EXECUTABLE}")
        if ((TARGET ${toolname}) AND (NOT CMAKE_CROSSCOMPILING))
            set(${toolname}_EXECUTABLE ${toolname} CACHE STRING "${toolname} executable target")
        elseif((NOT TARGET ${toolname}) AND (NOT CMAKE_CROSSCOMPILING))
            if ((DEFINED VCPKG_ROOT) OR (DEFINED VCPKG_TOOLCHAIN))
                message(FATAL_ERROR "Cannot find_program(${toolname}). Please install ${toolname} via : vcpkg install ${toolname}")
            endif()
            add_subdirectory("${${toolname}_SOURCE_DIR}" ${toolname})
        else()
            BuildTool(${toolname})
            find_program(${toolname}_EXECUTABLE REQUIRED NAMES ${toolname} PATHS "${CMAKE_CURRENT_BINARY_DIR}/${toolname}-install/bin")
        endif()
    endif()
endfunction()
