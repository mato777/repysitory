# Schema vs Domain Entities

## Overview

The repository pattern now supports separation between **storage entities** (schema) and **domain entities** (business logic). This allows you to keep database-specific fields (like `created_at`, `updated_at`) separate from your domain model.

## Key Concepts

### EntitySchema (Storage Layer)
- Maps directly to database tables
- Includes all database fields (timestamps, foreign keys, etc.)
- Used internally by the repository
- Example: `PostSchema` with `created_at`, `updated_at`, `deleted_at`

### EntityDomain (Business Layer)
- Clean business logic representation
- Can include computed properties
- No database noise
- Example: `Post` with `word_count`, `excerpt` properties

## Repository Type Signature

```python
Repository[T_schema, T_domain, S, U]
```

Where:
- `T_schema`: Database schema entity type
- `T_domain`: Domain/business entity type
- `S`: Search model type
- `U`: Update model type

## Usage Pattern

### 1. Define Schema and Domain Entities

```python
# Storage entity (database)
class PostSchema(BaseEntity):
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

# Domain entity (business logic)
class Post(BaseModel):
    id: uuid4
    title: str
    content: str

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    @property
    def excerpt(self) -> str:
        return self.content[:100]
```

### 2. Create Repository with Domain Mapping

```python
class PostRepository(Repository[PostSchema, Post, PostSearch, PostUpdate]):
    def __init__(self):
        super().__init__(
            entity_schema_class=PostSchema,
            entity_domain_class=Post,
            search_class=PostSearch,
            update_class=PostUpdate,
            table_name="posts",
        )

    def to_domain_entity(self, schema_entity: PostSchema) -> Post:
        """Convert schema to domain entity"""
        return Post(
            id=schema_entity.id,
            title=schema_entity.title,
            content=schema_entity.content,
        )
```

### 3. Use Repository

```python
# Create a domain entity
post = Post(
    id=uuid4(),
    title="My Post",
    content="Content here"
)

# Repository returns domain entities (no DB fields visible)
created_post = await repo.create(post)
print(created_post.word_count)  # Computed property
print(created_post.excerpt)    # Computed property

# Find returns domain entities
found = await repo.find_by_id(post.id)
# No access to created_at, updated_at, etc.
```

## Benefits

1. **Clean Separation**: Database fields don't leak into business logic
2. **Computed Properties**: Add business logic properties to domain entities
3. **Type Safety**: Full type checking for both schema and domain
4. **Backward Compatible**: If schema == domain, works exactly as before
5. **Flexibility**: Customize mapping per repository

## Default Behavior

If you don't specify `entity_domain_class`, it defaults to `entity_schema_class`:

```python
# This works exactly as before (no schema/domain separation)
repo = Repository(
    entity_schema_class=Post,
    search_class=PostSearch,
    update_class=PostUpdate,
    table_name="posts"
)
```

## Override Mapping

Override `to_domain_entity()` method to customize the conversion:

```python
def to_domain_entity(self, schema_entity: PostSchema) -> Post:
    """Custom mapping with computed fields"""
    return Post(
        id=schema_entity.id,
        title=schema_entity.title,
        content=schema_entity.content,
        tags=self._parse_tags(schema_entity.metadata),  # Custom logic
    )
```

## Example

See `examples/schema_vs_domain_example.py` for a complete working example.
