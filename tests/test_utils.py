from datetime import date

from modules.utils import date_range, format_date, load_config, today


def test_today():
    assert isinstance(today(), date)


def test_format_date_default():
    assert format_date(date(2026, 4, 22)) == "2026/04/22"


def test_format_date_custom():
    assert format_date(date(2026, 4, 22), "%Y-%m-%d") == "2026-04-22"


def test_format_date_japanese():
    assert format_date(date(2026, 4, 22), "%Y年%m月%d日") == "2026年04月22日"


def test_date_range():
    result = list(date_range(date(2026, 4, 1), date(2026, 4, 3)))
    assert result == [date(2026, 4, 1), date(2026, 4, 2), date(2026, 4, 3)]


def test_date_range_single_day():
    result = list(date_range(date(2026, 4, 1), date(2026, 4, 1)))
    assert result == [date(2026, 4, 1)]


def test_load_config(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("key: value\nnested:\n  a: 1\n")
    result = load_config(config_file)
    assert result == {"key": "value", "nested": {"a": 1}}
