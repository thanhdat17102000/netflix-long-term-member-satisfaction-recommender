from src.web.data_provider import get_payload, get_recommendations, get_user, get_users, search_movies


def test_web_payload_resolves_to_smoke_without_full_artifacts():
    payload = get_payload()
    assert payload["profile"] in {"smoke", "full"}
    assert isinstance(payload["is_full"], bool)
    assert payload["source"] in {"fixture", "full_artifacts"}
    assert "Netflix" in payload["disclaimer"]


def test_user_contract_and_long_term_profile():
    payload = get_payload()
    users = get_users(payload)
    assert users
    user = get_user(payload, int(users[0]["userId"]))
    assert user is not None
    assert "rating_count" in user
    assert "activity_span_days" in user
    assert "is_long_term" in user
    history = user.get("history")
    assert history is None or isinstance(history, list)
    if isinstance(history, list) and history:
        assert {"movieId", "rating", "split"} <= set(history[0])


def test_recommendations_are_unique_and_exclude_seen_items_when_fixture_provides_them():
    payload = get_payload()
    user_id = int(get_users(payload)[0]["userId"])
    rows = get_recommendations(payload, user_id, "hybrid", 10)
    movie_ids = [row["movieId"] for row in rows]
    assert len(movie_ids) == len(set(movie_ids))
    assert all(row.get("userId") == user_id for row in rows)
    assert all("reasons" in row for row in rows)


def test_unknown_model_is_normalised_without_crashing():
    payload = get_payload()
    user_id = int(get_users(payload)[0]["userId"])
    assert get_recommendations(payload, user_id, "not-a-model", 10) == get_recommendations(payload, user_id, "hybrid", 10)


def test_movie_search_contract():
    payload = get_payload()
    result = search_movies(payload, query="Toy")
    assert isinstance(result, list)
    assert all("title" in row and "movieId" in row for row in result)
