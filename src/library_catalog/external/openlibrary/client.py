class OpenLibraryClient:
    """Client for Open Library API interactions."""

    async def enrich(
        self,
        title: str,
        author: str,
        isbn: str | None = None,
    ) -> dict | None:
        """Return enrichment data for a book.

        This is a minimal stub that can be expanded later with real HTTP calls.
        """
        return None
