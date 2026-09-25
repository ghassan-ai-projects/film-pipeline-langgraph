"""Tests for the QC fan-out subgraph helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from film_pipeline.orchestration.services import SERVICES_KEY
from film_pipeline.orchestration.subgraphs import qc
from film_pipeline.schemas._base import FilmPhase


@dataclass
class FakeReport:
    score: float = 91.0
    status: str = "pass"
    blocking_issues: list[str] | None = None
    warnings: list[str] | None = None

    def model_dump(self) -> dict[str, Any]:
        return {"score": self.score, "status": self.status}


class FakeValidator:
    def __init__(self, report: FakeReport | None = None, *, raises: bool = False) -> None:
        self.report = report or FakeReport(blocking_issues=[], warnings=["minor"])
        self.raises = raises

    def run(self, artifact: dict[str, Any]) -> FakeReport:
        if self.raises:
            raise RuntimeError("validator failed")
        assert artifact["project_id"] == "p1"
        return self.report


class _FakeMeta:
    def __init__(self, artifact_id: str, phase: FilmPhase, version: int) -> None:
        self.artifact_id = artifact_id
        self.phase = phase
        self.version = version


class FakeArtifactStore:
    def __init__(self) -> None:
        self.calls: list[tuple[str, FilmPhase, str, int]] = []

    def list_artifacts(self, project_id: str) -> list[_FakeMeta]:
        _ = project_id
        return [_FakeMeta("script", FilmPhase.SCRIPT, 2)]

    def load(
        self,
        project_id: str,
        phase: FilmPhase,
        artifact_id: str,
        version: int,
    ) -> dict[str, Any]:
        self.calls.append((project_id, phase, artifact_id, version))
        if artifact_id == "script" and phase == FilmPhase.SCRIPT and version == 2:
            return {"project_id": project_id, "title": "Loaded"}
        raise FileNotFoundError(artifact_id)


def test_fan_out_validators_sends_all_validator_workers() -> None:
    sends = qc.fan_out_validators({"project_id": "p1"})

    assert [send.node for send in sends] == [
        "script_structure",
        "dialogue_voice",
        "reference_usability",
        "prompt_readiness",
        "scene_continuity",
        "assembly",
    ]
    assert all(send.arg["project_id"] == "p1" for send in sends)


def test_reduce_qc_reports_normalizes_missing_lists() -> None:
    state: Any = {"_qc_raw_reports": "bad", "_qc_reports": None}
    reduced = qc.reduce_qc_reports(state)

    assert reduced.get("_qc_reports") == []
    assert reduced["_validation_reports"] == []
    assert reduced["current_phase"] == "qc"
    assert reduced["human_approval_phase"] == "qc"
    assert reduced["human_approval_required"] is True
    assert reduced["approved"] is False
    assert "issues" not in reduced


def test_reduce_qc_reports_translates_findings_into_issues() -> None:
    state: Any = {
        "_qc_raw_reports": [
            {
                "validator_id": "script-structure",
                "blocking_issues": [{"code": "no_conflict", "message": "flat scenes"}],
                "warnings": [{"code": "dense_dialogue", "message": "wordy"}],
            }
        ],
        "_qc_reports": [{"validator_id": "script-structure"}],
    }
    reduced = qc.reduce_qc_reports(state)

    issues = reduced["issues"]
    assert isinstance(issues, list)
    severities = {(issue["code"], issue["severity"]) for issue in issues}
    assert severities == {("no_conflict", "blocking"), ("dense_dialogue", "warning")}
    # Reducer channels must not be re-emitted (they would duplicate).
    assert "_qc_raw_reports" not in reduced
    assert "_qc_reports" not in reduced


def test_run_validator_skips_without_services() -> None:
    result = qc._run_validator("script-structure", "ScriptStructureValidator", {})

    assert result == {
        "_qc_reports": [{"validator_id": "script-structure", "status": "skipped"}],
        "_qc_raw_reports": [{"validator_id": "script-structure", "status": "skipped"}],
    }


def test_run_validator_skips_when_validator_missing(monkeypatch: Any) -> None:
    monkeypatch.setattr(qc, "_resolve_validator_instance", lambda _srv, _validator_id: None)
    state: Any = {"project_id": "p1", SERVICES_KEY: object()}

    result = qc._run_validator(
        "script-structure",
        "ScriptStructureValidator",
        state,
    )

    assert result == {
        "_qc_reports": [{"validator_id": "script-structure", "status": "skipped"}],
        "_qc_raw_reports": [{"validator_id": "script-structure", "status": "skipped"}],
    }


def test_run_validator_skips_without_artifact(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        qc, "_resolve_validator_instance", lambda _srv, _validator_id: FakeValidator()
    )
    monkeypatch.setattr(qc, "_load_artifact_for_validator", lambda _state, _validator_id: None)
    state: Any = {"project_id": "p1", SERVICES_KEY: object()}

    result = qc._run_validator(
        "script-structure",
        "ScriptStructureValidator",
        state,
    )

    assert result == {
        "_qc_reports": [
            {
                "validator_id": "script-structure",
                "status": "skipped",
                "reason": "no artifact",
            }
        ],
        "_qc_raw_reports": [
            {
                "validator_id": "script-structure",
                "status": "skipped",
                "reason": "no artifact",
            }
        ],
    }


def test_run_validator_reports_failure(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        qc,
        "_resolve_validator_instance",
        lambda _srv, _validator_id: FakeValidator(raises=True),
    )
    monkeypatch.setattr(
        qc, "_load_artifact_for_validator", lambda _state, _validator_id: {"project_id": "p1"}
    )
    state: Any = {"project_id": "p1", SERVICES_KEY: object()}

    result = qc._run_validator(
        "dialogue-voice",
        "DialogueVoiceValidator",
        state,
    )

    assert result == {
        "_qc_reports": [{"validator_id": "dialogue-voice", "status": "failed"}],
        "_qc_raw_reports": [{"validator_id": "dialogue-voice", "status": "failed"}],
    }


def test_run_validator_returns_summary_and_raw_report(monkeypatch: Any) -> None:
    report = FakeReport(
        score=88.5,
        status="needs_revision",
        blocking_issues=["bad continuity"],
        warnings=["thin subtext"],
    )
    monkeypatch.setattr(
        qc,
        "_resolve_validator_instance",
        lambda _srv, _validator_id: FakeValidator(report),
    )
    monkeypatch.setattr(
        qc, "_load_artifact_for_validator", lambda _state, _validator_id: {"project_id": "p1"}
    )
    state: Any = {"project_id": "p1", SERVICES_KEY: object()}

    result = qc._run_validator(
        "scene-continuity",
        "SceneContinuityValidator",
        state,
    )

    assert result["_qc_reports"] == [
        {
            "validator_id": "scene-continuity",
            "score": 88.5,
            "status": "needs_revision",
            "blocking_count": 1,
            "warning_count": 1,
        }
    ]
    assert result["_qc_raw_reports"] == [{"score": 88.5, "status": "needs_revision"}]


def test_load_artifact_for_validator_loads_latest_and_returns_copy() -> None:
    store = FakeArtifactStore()
    services = type("Services", (), {"artifact_store": store})()
    state: Any = {"project_id": "p1", SERVICES_KEY: services}

    loaded = qc._load_artifact_for_validator(state, "script-structure")

    assert loaded == {"project_id": "p1", "title": "Loaded"}
    assert loaded is not None
    loaded["title"] = "Mutated"
    loaded_again = qc._load_artifact_for_validator(state, "script-structure")
    assert loaded_again == {"project_id": "p1", "title": "Loaded"}
    assert ("p1", FilmPhase.SCRIPT, "script", 2) in store.calls


def test_load_artifact_for_validator_skips_when_artifact_absent() -> None:
    store = FakeArtifactStore()
    services = type("Services", (), {"artifact_store": store})()
    state: Any = {"project_id": "p1", SERVICES_KEY: services}

    assert qc._load_artifact_for_validator(state, "assembly") is None


def test_load_artifact_for_validator_returns_none_without_services() -> None:
    assert qc._load_artifact_for_validator({"project_id": "p1"}, "script-structure") is None


def test_validator_worker_functions_delegate_to_run_validator(monkeypatch: Any) -> None:
    calls: list[tuple[str, str]] = []

    def fake_run(validator_id: str, class_name: str, _state: Any) -> dict[str, object]:
        calls.append((validator_id, class_name))
        return {"_qc_reports": [{"validator_id": validator_id}]}

    monkeypatch.setattr(qc, "_run_validator", fake_run)

    assert qc.script_structure({})["_qc_reports"] == [{"validator_id": "script-structure"}]
    assert qc.dialogue_voice({})["_qc_reports"] == [{"validator_id": "dialogue-voice"}]
    assert qc.reference_usability({})["_qc_reports"] == [{"validator_id": "reference-usability"}]
    assert qc.prompt_readiness({})["_qc_reports"] == [{"validator_id": "prompt-readiness"}]
    assert qc.scene_continuity({})["_qc_reports"] == [{"validator_id": "scene-continuity"}]
    assert qc.assembly({})["_qc_reports"] == [{"validator_id": "assembly"}]
    assert calls == [
        ("script-structure", "ScriptStructureValidator"),
        ("dialogue-voice", "DialogueVoiceValidator"),
        ("reference-usability", "ReferenceUsabilityValidator"),
        ("prompt-readiness", "PromptReadinessValidator"),
        ("scene-continuity", "SceneContinuityValidator"),
        ("assembly", "AssemblyValidator"),
    ]


def test_build_qc_subgraph_compiles() -> None:
    assert qc.build_qc_subgraph() is not None
