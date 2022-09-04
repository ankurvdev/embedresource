#include <EmbeddedResource.h>
#include <iostream>

DECLARE_RESOURCE_COLLECTION(testdata);

int main(int argc, char* argv[])
{
    auto resourceCollection = LOAD_RESOURCE_COLLECTION(testdata);
    for (auto const r : resourceCollection) { std::cout << r.string(); }
    return 0;
}