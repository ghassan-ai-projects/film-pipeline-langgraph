"""Tests for audit trail, metrics, and blocker reporter."""

from __future__ import annotations

from film_pipeline.observability.audit import AuditEventType, AuditTrail
from film_pipeline.observability.blockers import BlockerReporter
from film_pipeline.observability.metrics import MetricsCollector


class TestAudit:
    def test_record_event(self) -> None:
        trail = AuditTrail()
        trail.record(
            event_type=AuditEventType.MCP_REQUEST,
            project_id="p1",
            actor="orchestrator",
            action="create_project",
        )
        assert len(trail) == 1
        assert trail.events[0].success is True

    def test_record_failure(self) -> None:
        trail = AuditTrail()
        trail.record(
            event_type=AuditEventType.PROVIDER_ACTION,
            project_id="p1",
            actor="seedance",
            action="submit",
            success=False,
            error_message="quota exhausted",
        )
        assert len(trail.failures()) == 1

    def test_by_project(self) -> None:
        trail = AuditTrail()
        trail.record(AuditEventType.MCP_REQUEST, "p1", "a", "x")
        trail.record(AuditEventType.MCP_REQUEST, "p2", "a", "x")
        assert len(trail.by_project("p1")) == 1

    def test_by_type(self) -> None:
        trail = AuditTrail()
        trail.record(AuditEventType.MCP_REQUEST, "p1", "a", "x")
        trail.record(AuditEventType.GRAPH_NODE, "p1", "a", "x")
        assert len(trail.by_type(AuditEventType.MCP_REQUEST)) == 1

    def test_total_cost(self) -> None:
        trail = AuditTrail()
        trail.record(AuditEventType.PROVIDER_ACTION, "p1", "a", "x", cost_usd=0.50)
        trail.record(AuditEventType.PROVIDER_ACTION, "p1", "a", "x", cost_usd=0.30)
        assert trail.total_cost_usd() == 0.80


class TestMetrics:
    def test_record(self) -> None:
        c = MetricsCollector()
        c.record("test_metric", 42.0, env="test")
        assert len(c.points) == 1
        assert c.points[0].value == 42.0

    def test_phase_duration(self) -> None:
        c = MetricsCollector()
        c.phase_duration("script", 150.0, "p1")
        p = [x for x in c.points if x.name == "phase_duration_ms"]
        assert p[0].value == 150.0

    def test_agent_call(self) -> None:
        c = MetricsCollector()
        c.agent_call("script-agent", success=True, duration_ms=100.0)
        c.agent_call("script-agent", success=False, duration_ms=200.0)
        rate = c.agent_success_rate("script-agent")
        assert rate == 0.5

    def test_agent_success_rate_none(self) -> None:
        c = MetricsCollector()
        assert c.agent_success_rate("nonexistent") is None

    def test_total_provider_cost(self) -> None:
        c = MetricsCollector()
        c.provider_job("seedance", True, 0.18)
        c.provider_job("seedance", True, 0.36)
        assert c.total_provider_cost() == 0.54

    def test_cost_tracking(self) -> None:
        c = MetricsCollector()
        c.cost_tracking("p1", 5.0, 4.8)
        assert len(c.points) == 2

    def test_validation_score(self) -> None:
        c = MetricsCollector()
        c.validation_score("clip-validator", 85.0)
        p = [x for x in c.points if x.name == "validation_score"]
        assert p[0].value == 85.0


class TestBlockers:
    def test_no_issues(self) -> None:
        r = BlockerReporter()
        report = r.report("p1")
        assert report.has_blockers is False
        assert r.can_proceed(report) is True

    def test_with_blockers(self) -> None:
        r = BlockerReporter()
        report = r.report(
            "p1",
            open_issues=[
                {"phase": "script", "reason": "Missing Act 2", "severity": "blocking"},
                {"phase": "script", "reason": "Tone drift", "severity": "warning"},
            ],
        )
        assert report.has_blockers is True
        assert report.total_blockers == 1
        assert "blocker" in report.summary.lower()

    def test_can_proceed_blocked(self) -> None:
        r = BlockerReporter()
        report = r.report("p1", open_issues=[{"reason": "Broken"}])
        assert r.can_proceed(report) is False
