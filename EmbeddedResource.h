#pragma once
#pragma warning(push, 3)
#pragma clang diagnostic push
#pragma GCC diagnostic   push

#pragma clang diagnostic ignored "-Weverything"
#pragma GCC diagnostic   ignored "-Wmaybe-uninitialized"
#pragma warning(disable : 5262) /*xlocale(2010,13): implicit fall-through occurs here*/

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

#pragma GCC diagnostic   pop
#pragma clang diagnostic pop
#pragma warning(pop)

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
    operator std::span<T const>() const
    {
        auto const   ptr  = reinterpret_cast<const T*>(data);
        size_t const size = len / sizeof(T);
        assert(len % sizeof(T) == 0);
        return std::span<T const>{ptr, ptr + size};
    }
#endif
};

struct ResourceInfo
{
    Data<wchar_t> name;
    Data<uint8_t> data;
};

typedef ResourceInfo GetCollectionResourceInfo();

typedef Data<GetCollectionResourceInfo> GetCollectionResourceInfoTable();

}    // namespace EmbeddedResource::ABI

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

struct ResourceLoader
{
    ResourceLoader(EmbeddedResource::ABI::ResourceInfo info) : _info(info) {}
    ~ResourceLoader()                                = default;
    ResourceLoader()                                 = delete;
    ResourceLoader(ResourceLoader const&)            = delete;
    ResourceLoader(ResourceLoader&&)                 = delete;
    ResourceLoader& operator=(ResourceLoader const&) = delete;
    ResourceLoader& operator=(ResourceLoader&&)      = delete;

    std::wstring_view name() const { return std::wstring_view(_info.name.data, _info.name.len); }

#ifdef __cpp_lib_span
    template <typename T> auto data() const { return static_cast<std::span<T const>>(_info.data); }
#endif

    std::string_view string() const { return std::string_view(reinterpret_cast<const char*>(_info.data.data), _info.data.len); }

    EmbeddedResource::ABI::ResourceInfo const _info;
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
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunsafe-buffer-usage"
        ResourceLoader operator*() const { return ResourceLoader((*(_ptr->_collection.data + _index))()); }
#pragma clang diagnostic pop
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

#define LOAD_RESOURCE_COLLECTION(collection) CollectionLoader(EmbeddedResource_ABI_##collection##_##GetCollectionResourceInfoTable())
#define LOAD_RESOURCE(collection, resource) EmbeddedResource_ABI_##collection##_Resource_##resource##_##GetCollectionResourceInfo()
