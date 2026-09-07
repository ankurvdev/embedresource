#include "CommonMacros.h"
#include "EmbeddedResource.h"

SUPPRESS_WARNINGS_START
SUPPRESS_STL_WARNINGS

#include <algorithm>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

SUPPRESS_WARNINGS_END

static std::string FilePathToSym(std::filesystem::path const& filepath)
{
    auto sym = filepath.filename().string();
    replace(sym.begin(), sym.end(), '.', '_');    // NOLINT
    replace(sym.begin(), sym.end(), '-', '_');    // NOLINT
    if (std::isdigit(sym[0]) != 0) { return "_" + sym; }
    SUPPRESS_WARNINGS_START
    SUPPRESS_CLANG_WARNING("-Wnrvo")
    return sym;
    SUPPRESS_WARNINGS_END
}
namespace
{
struct Content
{
    std::filesystem::path fpath;
    std::string           resname;
    std::string           symname;

    explicit Content(std::string_view const& spec)
    {
        // If name is resname!filepath use resname or else convert filename into a symbol
        auto idx = static_cast<size_t>(spec.find('!'));
        if (idx == std::string::npos)
        {
            fpath   = spec;
            resname = fpath.filename().string();
            symname = FilePathToSym(fpath);
        }
        else
        {
            if (idx == 0) { throw std::invalid_argument("Invalid name for resource: " + std::string(spec)); }
            fpath   = std::filesystem::path(std::string(spec.substr(idx + 1)));
            resname =  spec.substr(0, idx); 
            symname = FilePathToSym(fpath);
        }
    }
};
}    // namespace
  SUPPRESS_WARNINGS_START
    SUPPRESS_CLANG_WARNING("-Wlifetime-safety-invalidation")
static void HandleArg(std::vector<Content>& contents, std::string_view const& arg)
{
    if (arg.empty()) return;
    if (arg[0] == '@')
    {
        auto          src = std::filesystem::path(arg.substr(1));
        std::ifstream ifs(src);
        if (!ifs.is_open()) { throw std::invalid_argument("Cannot find file: " + src.string()); }
        if (ifs.fail()) { throw std::logic_error("file corrupt: " + src.string()); }

        std::string line;
        while (std::getline(ifs, line)) { contents.emplace_back(line); }
    }
    else
    {
        contents.emplace_back(arg);
    }
}
SUPPRESS_WARNINGS_END
SUPPRESS_WARNINGS_START
SUPPRESS_CLANG_WARNING("-Wunsafe-buffer-usage")

int main(int argc, char** argv)
try
{
    if (argc < 3)
    {
        for (int i = 0; i < argc; i++) { std::cerr << " " << argv[i]; }

        std::cerr << "\n" << "\n" << "USAGE: %s {sym} {rsrc}..." << "\n" << "\n" << "  Creates {sym}.c from the contents of each {rsrc}\n"
                  << "  Each resource {rsrc} can be specified in the format [name!]filepath" << argv[0];
        return EXIT_FAILURE;
    }

    std::filesystem::path dst{argv[1]};
    SUPPRESS_WARNINGS_END

    create_directories(dst.parent_path());

    std::ofstream ofs{dst.string()};
    ofs << R"(
#if defined(__clang__) //NOLINT
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wunused-macros"
#define EMBEDDED_RESOURCE_EXPORTED_API_IMPL 1 //NOLINT(cppcoreguidelines-macro-usage,-warnings-as-errors)
#pragma clang diagnostic pop
#endif

#include <EmbeddedResource.h>
//NOLINTBEGIN(bugprone-reserved-identifier)
)";

    auto                     colsym = FilePathToSym(dst.stem());
    std::vector<std::string> symbols;
    std::vector<Content>     args;

    for (int i = 2; i < argc; i++) HandleArg(args, std::string_view(argv[i]));

    for (auto const& arg : args)
    {
        auto [src, resname, sym] = arg;
        std::ifstream ifs{src, std::ios::binary | std::ios::in};
        if (!ifs.is_open()) { throw std::invalid_argument("Cannot find file" + src.string()); }
        if (ifs.fail()) { throw std::logic_error("file corrupt: " + src.string()); }

        uint8_t c{};
        ifs.read(reinterpret_cast<char*>(&c), sizeof(c)); //NOLINT
        if (ifs.fail()) { continue; }
        symbols.push_back(FilePathToSym(src));
        ofs << "namespace EmbeddedResource::Data::" << colsym << "::Resources::" << sym << " {" << "\n";
        ofs << "static constexpr uint8_t ResourceData[] /*NOLINT*/ = {" << "\n";

        for (size_t j = 0; !ifs.eof() && !ifs.fail(); j++, ifs.read(reinterpret_cast<char*>(&c), sizeof(c))) //NOLINT
        {
            ofs << "0x" << std::hex << static_cast<uint32_t>(c) << "u,";
            if ((j + 1) % 10 == 0) { ofs << "\n"; } //NOLINT
        }

        ofs << "};" << "\n";
        ofs << "#if !(defined EMBEDRESOURCE_NAME_ENCODING_UTF16 && EMBEDRESOURCE_NAME_ENCODING_UTF16 == 1)" << "\n";
        ofs << "static constexpr std::string_view ResourceName = \"" << resname << "\";" << "\n";
        ofs << "#else" << "\n";
        ofs << "static constexpr std::wstring_view ResourceName = L\"" << resname << "\";" << "\n";
        ofs << "#endif" << "\n";
        ofs << "}" << "// namespace EmbeddedResource::Data::" << colsym << "::Resources::" << sym << "\n";
    }

    for (auto const& ressym : symbols) { ofs << "DECLARE_RESOURCE(" << colsym << "," << ressym << ");" << "\n"; }

    for (auto const& ressym : symbols)
    {
        ofs << "DECLARE_RESOURCE(" << colsym << "," << ressym << ")" << "\n";
        ofs << "{" << "\n";
        ofs << "  const auto* nameptr = EmbeddedResource::Data::" << colsym << "::Resources::" << ressym << "::ResourceName.data();" << "\n";
        ofs << "  auto namelen = EmbeddedResource::Data::" << colsym << "::Resources::" << ressym << "::ResourceName.size();" << "\n";
        ofs << "  const auto* dataptr /*NOLINT*/ = EmbeddedResource::Data::" << colsym << "::Resources::" << ressym << "::ResourceData;" << "\n";
        ofs << "  auto datalen = std::size(EmbeddedResource::Data::" << colsym << "::Resources::" << ressym << "::ResourceData);" << "\n";
        ofs << "    return EmbeddedResource::ABI::ResourceInfo { { nameptr, namelen }, { dataptr, datalen } };" << "\n";
        ofs << "}" << "\n";
    }

    ofs << "namespace EmbeddedResource::Data::" << colsym << " {" << "\n";
    ofs << "static constexpr EmbeddedResource::ABI::GetCollectionResourceInfo * const ResourceTable[] /*NOLINT*/ = {" << "\n";
    for (auto const& ressym : symbols)
    {
        ofs << "EMBEDDEDRESOURCE_ABI_RESOURCE_FUNCNAME(" << colsym << "," << ressym << ", GetCollectionResourceInfo)," << "\n";
    }
    
    ofs << "};" << "\n";
    ofs << "} // namespace EmbeddedResource::Data::" << colsym << "\n";
    ofs << "DECLARE_RESOURCE_COLLECTION(" << colsym << ");" << "\n";

    ofs << "DECLARE_RESOURCE_COLLECTION(" << colsym << ")" << "\n";
    ofs << "{" << "\n";
    ofs << "    const auto* tableptr /*NOLINT*/ = EmbeddedResource::Data::" << colsym << "::ResourceTable;" << "\n";
    ofs << "    auto tablelen = std::size(EmbeddedResource::Data::" << colsym << "::ResourceTable);" << "\n";
    ofs << "    return EmbeddedResource::ABI::Data<EmbeddedResource::ABI::GetCollectionResourceInfo*> {tableptr, tablelen };" << "\n";
    ofs << "}" << "\n";
    ofs << "//NOLINTEND(bugprone-reserved-identifier)" << "\n";

    ofs.close();
    return EXIT_SUCCESS;
} catch (std::exception const& ex)
{
    std::cerr << ex.what() << "\n";
    return -1;
}
