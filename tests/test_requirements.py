def test_requirements_pinned():
    import pathlib

    txt = pathlib.Path("requirements.txt").read_text()
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        assert "==" in line, f"Unpinned requirement: {line}"
