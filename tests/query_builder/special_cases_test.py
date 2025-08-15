from src.query_builder import QueryBuilder


def test_group_only_or_conditions_and_unadjusted_placeholder():
    """Covers:
    - Line 124: return " OR ".join(adjusted_or_where) for groups with only OR conditions
    - Line 140: return match.group(0) when a placeholder exceeds the group's param count
    """

    def group_only_or(q: QueryBuilder) -> QueryBuilder:
        # Add a normal OR condition so the group has at least one param to adjust
        qb = q.or_where("status", "draft")
        # Inject a raw condition containing a placeholder that exceeds total_group_params
        # This forces _adjust_parameter_indices to hit the fallback branch and keep it unchanged
        qb.or_where_conditions.append("bogus = $99")
        return qb

    builder = QueryBuilder("posts")
    query, params = builder.where("user_id", "123").where_group(group_only_or).build()

    assert query == "SELECT * FROM posts WHERE user_id = $1 AND (status = $2 OR bogus = $99)"
    assert params == ["123", "draft"]