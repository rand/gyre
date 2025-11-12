from gyre import programs


def test_compile_programs_runs_with_empty_datasets():
    programs.compile_programs({
        "rank_train": [],
        "sum_train": [],
        "ev_train": [],
        "red_train": [],
        "blue_train": [],
    })
