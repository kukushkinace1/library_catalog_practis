import asyncio

from library_catalog.external.openlibrary.client import OpenLibraryClient


async def test():
    client = OpenLibraryClient()

    try:
        data = await client.search_by_isbn("9780132350884")
        print(f"ISBN result: {data}")

        data = await client.search_by_title_author(
            "Clean Code",
            "Robert Martin",
        )
        print(f"title+author result: {data}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test())

# ISBN result: {'cover_url': 'https://covers.openlibrary.org/b/id/8065615-L.jpg', 'language': 'fre'}
# title+author result: {'cover_url': 'https://covers.openlibrary.org/b/id/8065615-L.jpg', 'language': 'hun'}

