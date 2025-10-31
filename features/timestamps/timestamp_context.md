## Timestamp handling context for LLM agents

This project provides first-class, automatic handling of common timestamp fields on entities managed through the `Repository` in `src/repository.py`.

Key concept: schema vs domain separation
- The schema (DB model) defines the database structure and drives automatic timestamp behavior.
- The domain (business model) is what your app code uses; it may or may not declare timestamp fields.
- The repository maps rows to the domain model. If the domain model does not declare the timestamp fields, they are still accessible because domain models inherit from `BaseEntity` with `extra="allow"`.

### What the repository does automatically

- **created_at on create**: If the schema class defines a `created_at` field, the repository will populate it with the current UTC time when creating an entity, unless the user explicitly provided a value.
- **updated_at on create**: If the schema class defines an `updated_at` field, it will also be set to the current UTC time during creation, unless explicitly provided.
- **updated_at on update**: If the schema class defines an `updated_at` field, it will be set to the current UTC time on updates, unless the user explicitly provided an `updated_at` value in the update payload.

These behaviors are implemented in `Repository._apply_automatic_fields` and are triggered based on whether the schema class includes those field names. The detection relies on the schema’s `model_fields` containing `created_at` and/or `updated_at`. If a provided value is `None`, it is treated as missing and auto-filled.

### High-level rules

- **Opt-in by field presence**: The behavior is enabled when the schema model defines the fields. If a field is not present, no automatic handling occurs for that field.
- **Explicit values win**: If the caller supplies `created_at`/`updated_at`, the repository will not overwrite them.
- **Timezone**: Timestamps are generated in UTC using `datetime.now(UTC)`.

### Where this is applied

- `create` and `create_many`: Automatically sets `created_at` and `updated_at` if defined and not provided.
- `update` and `update_many_by_ids`: Automatically sets `updated_at` if defined and not provided.

Note: The repository also supports soft-delete via an optional `deleted_at` field, but that is separate from timestamp creation/update concerns.

### Minimal schema example (Pydantic)

```python
from datetime import datetime
from pydantic import BaseModel

class PostSchema(BaseModel):
    id: str
    title: str
    body: str
    created_at: datetime | None = None  # opt-in to automatic create timestamp
    updated_at: datetime | None = None  # opt-in to automatic update timestamp
```

With a repository like:

```python
from src.repository import Repository

post_repo = Repository(
    entity_schema_class=PostSchema,
    entity_domain_class=PostSchema,  # or a separate domain model
    update_class=PostUpdate,         # typically a dedicated Update model
    table_name="posts",
)
```

### Behavior examples

- **Create without timestamps provided**
  - Input payload omits `created_at`/`updated_at`.
  - Repository sets both to current UTC.

- **Create with explicit timestamps**
  - Input includes `created_at` or `updated_at`.
  - Repository respects provided values and does not override.

- **Update without `updated_at` provided**
  - Repository sets `updated_at` to current UTC.

- **Update with explicit `updated_at`**
  - Repository respects the provided `updated_at`.

### Disabling automatic timestamps

- Simply remove the corresponding field(s) from the schema model:
  - Remove `created_at` to disable automatic creation time handling.
  - Remove `updated_at` to disable automatic update time handling.

### Implementation notes (for reference)

- Field detection occurs in the repository constructor by checking the schema class’ `model_fields` for `created_at` and `updated_at`.
- The method `_apply_automatic_fields(data, is_create)` injects timestamps only when the field exists in the schema and is not already present in `data`.

### Using Field[T] for type-safe schema columns

For more type-safe query building, schema classes can use `Field[T]` from `src/entities.py`:

```python
from datetime import datetime
from src.entities import SchemaBase, Field

class PostSchema(SchemaBase):
    title = Field[str]("title")
    created_at = Field[datetime]("created_at")
    updated_at = Field[datetime]("updated_at")

# Usage in queries:
repo.where(PostSchema.created_at, some_dt).order_by(PostSchema.updated_at)
```

`Field[T]` stringifies to the database column name, making it safe to pass directly into repository query builders.

### Schema vs domain examples

1) Schema and domain both include timestamps
- entity_schema_class: includes `created_at`, `updated_at`
- entity_domain_class: includes `created_at`, `updated_at`
- Behavior: repository injects timestamps; domain instances have typed timestamp attributes.

2) Schema includes timestamps, domain does not
- entity_schema_class: includes `created_at`, `updated_at`
- entity_domain_class: omits timestamp fields
- Behavior: repository injects timestamps; domain instances still expose `created_at` and `updated_at` via extras (untyped), accessible via attribute access.

This context should be sufficient for agents to reason about how and when timestamps are applied during create/update operations without needing to re-implement logic.
