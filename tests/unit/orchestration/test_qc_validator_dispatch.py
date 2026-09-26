"""Pin QC validator-runner dispatch table membership per phase.

A typo in ``_VALIDATOR_RUNNERS`` membership (e.g. adding the delivery runner
to the ``qc`` phase's set) would ship green because every runner still runs
successfully wherever it fires. These tests make membership observable.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

import film_pipeline.orchestration.nodes.qc as qc_module

_RUNNER_NAMES: tuple[str, ...] = (
    "_run_script_validators",
    "_run_reference_validators",
    "_run_prompt_validators",
    "_run_continuity_validators",
    "_run_assembly_validators",
    "_run_delivery_validators",
)

_Sentinel = Callable[[dict[str, Any], list[Any], dict[str, Any], Any], None]


def _short_name(function_name: str) -> str:
    return function_name.removeprefix("_run_").removesuffix("_validators")


def _install_sentinels(monkeypatch: pytest.MonkeyPatch) -> set[str]:
    """Replace each runner in ``_VALIDATOR_RUNNERS`` with a recording sentinel.

    The table holds direct references to the runner functions, so patching
    the module attributes alone would not intercept dispatch; rebuild the
    table around sentinels while keeping the production phase sets intact.
    """
    fired: set[str] = set()

    def _make(name: str) -> _Sentinel:
        def _sentinel(
            artifact_data: dict[str, Any],
            issues: list[Any],
            state: dict[str, Any],
            services: Any,
        ) -> None:
            fired.add(_short_name(name))

        return _sentinel

    sentinels = {name: _make(name) for name in _RUNNER_NAMES}
    name_by_runner = {getattr(qc_module, name): name for name in _RUNNER_NAMES}
    rebuilt = tuple(
        (phases, sentinels[name_by_runner[runner]])
        for phases, runner in qc_module._VALIDATOR_RUNNERS
    )
    for name, sentinel in sentinels.items():
        monkeypatch.setattr(qc_module, name, sentinel)
    monkeypatch.setattr(qc_module, "_VALIDATOR_RUNNERS", rebuilt)
    return fired


def test_dispatch_table_registers_each_runner_exactly_once() -> None:
    registered: list[str] = []
    for phases, runner in qc_module._VALIDATOR_RUNNERS:
        matches = [name for name in _RUNNER_NAMES if getattr(qc_module, name) is runner]
        assert len(matches) == 1
        assert isinstance(phases, set)
        registered.append(matches[0])
    assert sorted(registered) == sorted(_RUNNER_NAMES)


@pytest.mark.parametrize(
    ("phase", "expected_runners"),
    [
        pytest.param("", set(), id="unknown-phase-runs-nothing"),
        pytest.param("script", {"script"}),
        pytest.param("visual_dev", {"reference"}),
        pytest.param("gen_planning", {"prompt"}),
        pytest.param("shot_bible", {"continuity"}),
        pytest.param("post", {"assembly"}),
        pytest.param("assembly", {"assembly"}),
        pytest.param(
            "qc",
            {"script", "reference", "prompt", "continuity", "assembly"},
            id="qc-covers-upstream-but-not-delivery",
        ),
        pytest.param("delivery", {"delivery"}, id="delivery-runs-only-delivery"),
    ],
)
def test_validator_dispatch_fires_exactly_expected_runners(
    phase: str,
    expected_runners: set[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fired = _install_sentinels(monkeypatch)

    qc_module._execute_phase_validators(
        state={"current_phase": phase},
        artifacts={"some_artifact": {}},  # non-empty: an empty map short-circuits dispatch
        issues=[],
        services=None,
    )

    assert fired == expected_runners
