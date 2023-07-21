# README

## Overview
[![Build Status](https://dev.azure.com/ankurv/embedresource/_apis/build/status/ankurvdev.embedresource?branchName=main)](https://dev.azure.com/ankurv/embedresource/_build/latest?definitionId=9&branchName=main)

Cross platform tool for embedding resources into the binaries

## CMake Initialization
Supports either git-submodule or vcpkg / cmake-package based initialization
```cmake
    # Git Submodule https://github.com/ankurvdev/embedresource
    add_subdirectory(embedresource)
```
OR 
```cmake
    # CMake pre-installed location
    find_package(EmbedResource REQUIRED)
```

## CMake Integration
```cmake
    find_package(EmbedResource REQUIRED)
    add_resource_library(TARGET foo RESOURCE_COLLECTION_NAME bar RESOURCES "bar1.bin;bar2.bin")
    target_link_libraries(main PRIVATE foo)
```

## Code

```
#include <EmbeddedResource.h>
#include <iostream>

DECLARE_RESOURCE_COLLECTION(foo);

int main(int argc, char* argv[])
{
    auto resourceCollection = LOAD_RESOURCE_COLLECTION(foo);
    for (auto const r : resourceCollection) { std::cout << r.string(); }
    return 0;
}
```
