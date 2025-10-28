from src.repository import Repository
from tests.post_entities import Post, PostUpdate


class PostRepository(Repository[Post, Post, PostUpdate]):
    def __init__(self):
        super().__init__(
            entity_schema_class=Post,
            entity_domain_class=Post,
            update_class=PostUpdate,
            table_name="posts",
        )

    # Custom finders for testing
    async def find_by_title(self, title: str) -> Post | None:
        return await self.where("title", title).first()

    async def find_by_content_containing(self, content_part: str) -> list[Post]:
        return await self.where("content", "LIKE", f"%{content_part}%").get()

    # Convenience methods with sorting
    async def find_all_sorted_by_title(self) -> list[Post]:
        return await self.order_by_asc("title").get()

    async def find_latest_posts(self) -> list[Post]:
        return await self.order_by_desc("id").get()
