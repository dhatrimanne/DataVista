from backend.utils.dataframe_cache import clear_dataframe_cache, read_csv_cached


def test_cached_csv_reads_return_copies_and_invalidate_on_change(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("value\n1\n", encoding="utf-8")
    clear_dataframe_cache()

    first = read_csv_cached(path)
    first.loc[0, "value"] = 999
    second = read_csv_cached(path)

    path.write_text("value\n2\n", encoding="utf-8")
    updated = read_csv_cached(path)

    assert second.loc[0, "value"] == 1
    assert updated.loc[0, "value"] == 2
