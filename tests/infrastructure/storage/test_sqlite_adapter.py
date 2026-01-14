from gyrus.infrastructure.adapters.storage.sqlite_storage import SQLiteNodeRepository


def test_sqlite_repository_instantiation():
    repo = SQLiteNodeRepository(db_path=":memory:")
    assert repo is not None
