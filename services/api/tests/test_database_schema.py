from app.database.schema import REQUIRED_TABLES
from app.database.store import get_store


def test_required_tables_exist():
    store = get_store()
    assert set(REQUIRED_TABLES).issubset(set(store.table_names()))
    assert store.schema_ready()


def test_seed_course_apps_and_source_refs_exist():
    store = get_store()
    apps = store.list_apps()
    app_types = {app.app_type for app in apps}
    assert "physics.work_energy_demo" in app_types
    assert "math.gradient_descent_demo" in app_types
    assert "custom.html" in app_types
    chunks = store.retrieve_chunks("梯度下降")
    assert chunks
    assert all(chunk["source_ref"]["chunk_id"] for chunk in chunks)
