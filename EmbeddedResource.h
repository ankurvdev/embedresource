#pragma once
#if defined _MSC_VER
#pragma warning(push, 3)
#pragma warning(disable : 5262) /*xlocale(2010,13): implicit fall-through occurs here*/
#elif defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Weverything"

#elif defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmaybe-uninitialized"
#endif

#include <cassert>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <optional>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <version>

#ifdef __cpp_lib_span
#include <span>
#endif

#ifdef __cpp_lib_string_view
#include <string_view>
#endif

#if defined _MSC_VER
#pragma warning(pop)
#elif defined(__clang__)
#pragma clang diagnostic pop
#elif defined(__GNUC__)
#pragma GCC diagnostic pop
#endif

#if defined(_MSC_VER)    // compiling with VisualStudio
#if defined(EMBEDDED_RESOURCE_EXPORTED_API_IMPL)
#define EMBEDDED_RESOURCE_EXPORTED_API extern "C" __declspec(dllexport)
#else
#define EMBEDDED_RESOURCE_EXPORTED_API extern "C" __declspec(dllimport)
#endif
#elif defined(__GNUC__)    // compiling with GCC
#define EMBEDDED_RESOURCE_EXPORTED_API extern "C" __attribute__((visibility("protected")))
#else
#error "Unknown Compiler. Dont know how to export symbol"
#endif

#define EMBEDDEDRESOURCE_ABI_RESOURCE_FUNCNAME(collection, symbol, func) EmbeddedResource_ABI_##collection##_Resource_##symbol##_##func
#define EMBEDDEDRESOURCE_ABI_COLLECTION_FUNCNAME(collection, func) EmbeddedResource_ABI_##collection##_##func

#undef MY_CONCAT
#undef MY_CONCAT2

namespace EmbeddedResource::ABI
{
template <typename T> struct Data
{
    T const* data;
    size_t   len;
#ifdef __cpp_lib_string_view
    operator std::string_view() const { return std::string_view(reinterpret_cast<const char*>(data), len); }
#endif
    operator std::string() const { return std::string(reinterpret_cast<const char*>(data), len); }
#ifdef __cpp_lib_span
    template <typename T1> auto as_span() const
    {
        auto const   ptr  = reinterpret_cast<const T1*>(data);
        size_t const size = len / sizeof(T1);
        assert(len % sizeof(T1) == 0);
        return std::span<T1 const>{ptr, ptr + size};
    }
    template <typename T1> operator std::span<T1 const>() const { return this->template as_span<T1>(); }
#endif
};

struct ResourceInfo
{
#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
    Data<char> name;
#else
    Data<wchar_t> name;
#endif
    Data<uint8_t> data;
};

typedef ResourceInfo GetCollectionResourceInfo();

typedef Data<GetCollectionResourceInfo> GetCollectionResourceInfoTable();

}    // namespace EmbeddedResource::ABI

struct ResourceLoader
{
    ResourceLoader(EmbeddedResource::ABI::ResourceInfo infoIn) : info(infoIn) {}
    ~ResourceLoader()                                = default;
    ResourceLoader()                                 = delete;
    ResourceLoader(ResourceLoader const&)            = delete;
    ResourceLoader(ResourceLoader&&)                 = delete;
    ResourceLoader& operator=(ResourceLoader const&) = delete;
    ResourceLoader& operator=(ResourceLoader&&)      = delete;

#ifdef __cpp_lib_string_view
#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)
    auto name() const { return std::string_view(info.name.data, info.name.len); }
#else
    auto name() const { return std::wstring_view(info.name.data, info.name.len / sizeof(wchar_t)); }
#endif
    std::string_view string() const { return std::string_view(reinterpret_cast<const char*>(info.data.data), info.data.len); }
#endif

#ifdef __cpp_lib_span
    template <typename T> auto data() const { return info.data.as_span<T>(); }
#endif

    EmbeddedResource::ABI::ResourceInfo const info;
};

struct CollectionLoader
{
    struct Iterator
    {
        CollectionLoader* _ptr;
        size_t            _index;

        bool      operator!=(Iterator const& it) const { return _ptr != it._ptr || _index != it._index; }
        Iterator& operator++()
        {
            _index++;
            return *this;
        }
#if defined(__clang__)
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunsafe-buffer-usage"
#endif
        ResourceLoader operator*() const { return ResourceLoader((*(_ptr->_collection.data + _index))()); }
#if defined(__clang__)
#pragma clang diagnostic pop
#endif
    };

    CollectionLoader(EmbeddedResource::ABI::Data<EmbeddedResource::ABI::GetCollectionResourceInfo*> collection) : _collection(collection) {}
    ~CollectionLoader()                                  = default;
    CollectionLoader()                                   = delete;
    CollectionLoader(CollectionLoader const&)            = delete;
    CollectionLoader(CollectionLoader&&)                 = delete;
    CollectionLoader& operator=(CollectionLoader const&) = delete;
    CollectionLoader& operator=(CollectionLoader&&)      = delete;

    Iterator begin() { return Iterator{this, 0}; }
    Iterator end() { return Iterator{this, _collection.len}; }

    EmbeddedResource::ABI::Data<EmbeddedResource::ABI::GetCollectionResourceInfo*> const _collection;
};

#define DECLARE_IMPORTED_RESOURCE_COLLECTION(collection)                                                          \
    EMBEDDED_RESOURCE_EXPORTED_API EmbeddedResource::ABI::Data<EmbeddedResource::ABI::GetCollectionResourceInfo*> \
                                   EmbeddedResource_ABI_##collection##_##GetCollectionResourceInfoTable()

#define DECLARE_IMPORTED_RESOURCE(collection, resource)                \
    EMBEDDED_RESOURCE_EXPORTED_API EmbeddedResource::ABI::ResourceInfo \
                                   EmbeddedResource_ABI_##collection##_Resource_##resource##_##GetCollectionResourceInfo()

#define DECLARE_RESOURCE_COLLECTION(collection)                                    \
    EmbeddedResource::ABI::Data<EmbeddedResource::ABI::GetCollectionResourceInfo*> \
    EmbeddedResource_ABI_##collection##_##GetCollectionResourceInfoTable()

#define DECLARE_RESOURCE(collection, resource) \
    EmbeddedResource::ABI::ResourceInfo EmbeddedResource_ABI_##collection##_Resource_##resource##_##GetCollectionResourceInfo()

#define LOAD_RESOURCE_COLLECTION(collection) CollectionLoader(EmbeddedResource_ABI_##collection##_##GetCollectionResourceInfoTable())
#define LOAD_RESOURCE(collection, resource) EmbeddedResource_ABI_##collection##_Resource_##resource##_##GetCollectionResourceInfo()
