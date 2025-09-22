#include <EmbeddedResource.h>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <string_view>

DECLARE_RESOURCE_COLLECTION(testdata1);
DECLARE_RESOURCE_COLLECTION(testdata2);
#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
DECLARE_RESOURCE_COLLECTION(testdata3);
DECLARE_RESOURCE(testdata3, main_cpp);
#else
DECLARE_RESOURCE_COLLECTION(testdata3_wide);
DECLARE_RESOURCE(testdata3_wide, main_cpp);
#endif

#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
std::string_view MainCppName = "main.cpp";
#else
std::wstring_view MainCppName = L"main.cpp";
#endif

#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
std::string_view CMakeListName = "CMakeLists.txt";
#else
std::wstring_view CMakeListName = L"CMakeLists.txt";
#endif

void verify_resource(ResourceLoader const& r)
{
    if (r.name() == MainCppName)
    {
#ifdef __cpp_lib_span
        if (r.template data<uint8_t>().size() != MAIN_CPP_FILE_SIZE) { throw std::runtime_error("r.data.len() != MAIN_CPP_FILE_SIZE"); }
#endif
#ifdef __cpp_lib_string_view
        if (r.string().size() != MAIN_CPP_FILE_SIZE) { throw std::runtime_error("r.string().size() != MAIN_CPP_FILE_SIZE"); }
#endif
    }
    else if (r.name() == CMakeListName)
    {
#ifdef __cpp_lib_span
        if (r.template data<uint8_t>().size() != CMAKELISTS_TXT_FILE_SIZE)
        {
            throw std::runtime_error("r.data.len() != CMAKELISTS_TXT_FILE_SIZE");
        }
#endif
#ifdef __cpp_lib_string_view
        if (r.string().size() != CMAKELISTS_TXT_FILE_SIZE) { throw std::runtime_error("r.string().size() != CMAKELISTS_TXT_FILE_SIZE"); }
#endif
    }
    else
    {
        throw std::runtime_error("Unknown resource name");
    }
}

int main(int argc, char* argv[])
try
{
#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
    std::string_view res = LOAD_RESOURCE(testdata3, main_cpp).data;
    if (res.size() != MAIN_CPP_FILE_SIZE) { throw std::runtime_error("r.data.len() != MAIN_CPP_FILE_SIZE"); }
#else
    std::string_view res = LOAD_RESOURCE(testdata3_wide, main_cpp).data;
    if (res.size() != MAIN_CPP_FILE_SIZE) { throw std::runtime_error("r.data.len() != MAIN_CPP_FILE_SIZE"); }
#endif

    auto resourceCollection1 = LOAD_RESOURCE_COLLECTION(testdata1);
    for (auto const r : resourceCollection1) { verify_resource(r); }

    auto resourceCollection2 = LOAD_RESOURCE_COLLECTION(testdata2);
    for (auto const r : resourceCollection2) { verify_resource(r); }

#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
    auto resourceCollection3 = LOAD_RESOURCE_COLLECTION(testdata3);
    for (auto const r : resourceCollection2) { verify_resource(r); }
#else
    auto resourceCollection3 = LOAD_RESOURCE_COLLECTION(testdata3_wide);
    for (auto const r : resourceCollection2) { verify_resource(r); }
#endif
    return 0;
} catch (const std::exception& ex)
{
    std::cerr << "Failed: " << ex.what() << std::endl;
    return -1;
}