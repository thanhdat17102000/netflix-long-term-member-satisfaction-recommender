from src.common.config import MOVIELENS_HEADERS
from src.common.logic import schema_is_valid


def test_fixture_files_match_movielens_schema(project_root):
    fixture = project_root / "tests" / "fixtures" / "ml-25m"
    for filename in MOVIELENS_HEADERS:
        header = (fixture / filename).read_text(encoding="utf-8").splitlines()[0]
        assert schema_is_valid(filename, header), filename
