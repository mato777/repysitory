from entities import Post, PostSearch, PostSort
from repository import Repository
from typing import Optional, List
import asyncpg

class PostRepository(Repository[Post, PostSearch]):  # Now explicitly declares search type
    def __init__(self, db_name: str = "default"):
        super().__init__(Post, PostSearch, "posts", db_name)  # Must pass search class

    # Override to add proper PostSort typing
    async def find_many_by(self, search: Optional[PostSearch] = None, sort: Optional[PostSort] = None, *, conn: Optional[asyncpg.Connection] = None) -> List[Post]:
        return await super().find_many_by(search, sort, conn=conn)

    # Custom finders can be added here
    async def find_by_title(self, title: str, *, conn: Optional[asyncpg.Connection] = None) -> Optional[Post]:
        search = PostSearch(title=title)
        return await self.find_one_by(search, conn=conn)

    async def find_by_content_containing(self, content_part: str, *, conn: Optional[asyncpg.Connection] = None) -> List[Post]:
        # This would require a custom implementation for LIKE queries
        # For now, exact match using the search model
        search = PostSearch(content=content_part)
        return await self.find_many_by(search, conn=conn)

    # Convenience methods with sorting
    async def find_all_sorted_by_title(self, *, conn: Optional[asyncpg.Connection] = None) -> List[Post]:
        sort = PostSort(title="ASC")
        return await self.find_many_by(sort=sort, conn=conn)

    async def find_latest_posts(self, *, conn: Optional[asyncpg.Connection] = None) -> List[Post]:
        sort = PostSort(id="DESC")  # Assuming newer posts have higher IDs
        return await self.find_many_by(sort=sort, conn=conn)
