from modules.csv_utils import read_csv, read_csv_rows, validate_csv_row


def test_read_csv(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n")
    result = read_csv(csv_file)
    assert len(result) == 2
    assert result[0]["name"] == "Alice"
    assert result[0]["age"] == "30"
    assert result[1]["name"] == "Bob"


def test_read_csv_rows(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age\nAlice,30\nBob,25\n")
    result = read_csv_rows(csv_file)
    assert len(result) == 2
    assert result[0] == ["Alice", "30"]
    assert result[1] == ["Bob", "25"]


def test_read_csv_rows_with_header(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("name,age\nAlice,30\n")
    result = read_csv_rows(csv_file, skip_header=False)
    assert len(result) == 2
    assert result[0] == ["name", "age"]


def test_validate_csv_row_valid():
    assert validate_csv_row(["a", "b", "c"], 3) is True


def test_validate_csv_row_invalid_short():
    assert validate_csv_row(["a", "b"], 3) is False


def test_validate_csv_row_invalid_long():
    assert validate_csv_row(["a", "b", "c", "d"], 3) is False
