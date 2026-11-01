from organizador.cli import main


def test_organize_moves_files_and_prints_summary(tmp_path, capsys):
    (tmp_path / "foto.png").write_text("x", encoding="utf-8")
    (tmp_path / "doc.pdf").write_text("x", encoding="utf-8")

    exit_code = main(["organizar", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "Imagens" / "foto.png").is_file()
    assert "2 arquivo(s) movidos" in capsys.readouterr().out


def test_simulate_does_not_move_anything(tmp_path, capsys):
    (tmp_path / "foto.png").write_text("x", encoding="utf-8")

    exit_code = main(["organizar", str(tmp_path), "--simular"])

    assert exit_code == 0
    assert (tmp_path / "foto.png").is_file()
    assert "[simulação] foto.png" in capsys.readouterr().out


def test_undo_command_restores_files(tmp_path):
    (tmp_path / "foto.png").write_text("x", encoding="utf-8")
    main(["organizar", str(tmp_path)])

    exit_code = main(["desfazer", str(tmp_path)])

    assert exit_code == 0
    assert (tmp_path / "foto.png").is_file()


def test_missing_folder_returns_error(tmp_path):
    assert main(["organizar", str(tmp_path / "nao-existe")]) == 1


def test_invalid_config_returns_error(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text("[outra]\n", encoding="utf-8")
    folder = tmp_path / "pasta"
    folder.mkdir()

    assert main(["organizar", str(folder), "--config", str(config)]) == 1


def test_simulate_and_watch_cannot_be_combined(tmp_path):
    assert main(["organizar", str(tmp_path), "--simular", "--monitorar"]) == 1
