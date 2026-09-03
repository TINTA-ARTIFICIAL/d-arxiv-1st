"""Tests de cli.main — entry point del CLI d-arxiv.

Ticket: CLI-01
"""

from __future__ import annotations

import pytest

from cli import main as cli_main


# --- main: subcomando wizard ---


def test_main_wizard_exito_devuelve_0(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_main, "run_wizard", lambda: {})

    code = cli_main.main(["wizard"])

    assert code == 0


def test_main_wizard_runtimeerror_devuelve_1_y_escribe_stderr_sin_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _raise_runtime_error() -> None:
        raise RuntimeError("x")

    monkeypatch.setattr(cli_main, "run_wizard", _raise_runtime_error)

    code = cli_main.main(["wizard"])

    captured = capsys.readouterr()
    assert code == 1
    assert "x" in captured.err
    assert "Traceback" not in captured.err


def test_main_wizard_keyboardinterrupt_propaga(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_keyboard_interrupt() -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_main, "run_wizard", _raise_keyboard_interrupt)

    with pytest.raises(KeyboardInterrupt):
        cli_main.main(["wizard"])


# --- main: argv sin subcomando conocido ---


def test_main_subcomando_desconocido_devuelve_2_sin_matar_proceso() -> None:
    code = cli_main.main(["no-existe"])

    assert code == 2


def test_main_sin_subcomando_devuelve_2_con_mensaje_de_uso(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli_main.main([])

    captured = capsys.readouterr()
    assert code == 2
    assert "usage" in captured.err.lower()
