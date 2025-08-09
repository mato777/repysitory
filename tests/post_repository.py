from src.entities import SortOrder
from src.repository import Repository
from tests.post_entities import Post, PostSearch, PostSort, PostUpdate


class PostRepository(Repository[Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(Post, PostSearch, PostUpdate, "posts")

    # Override to add proper PostSort typing
    async def find_many_post_by(
        self, search: PostSearch | None = None, sort: PostSort | None = None
    ) -> list[Post]:
        return await super().find_many_by(search, sort)

    # Custom finders for testing
    async def find_by_title(self, title: str) -> Post | None:
        search = PostSearch(title=title)
        return await self.find_one_by(search)

    async def find_by_content_containing(self, content_part: str) -> list[Post]:
        search = PostSearch(content=content_part)
        return await self.find_many_post_by(search)

    # Convenience methods with sorting
    async def find_all_sorted_by_title(self) -> list[Post]:
        sort = PostSort(title=SortOrder.ASC)
        return await self.find_many_post_by(sort=sort)

    async def find_latest_posts(self) -> list[Post]:
        sort = PostSort(id=SortOrder.DESC)
        return await self.find_many_post_by(sort=sort)
