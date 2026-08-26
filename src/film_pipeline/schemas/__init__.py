"""Typed Pydantic schemas — the contract layer for the studio.

Every data structure that crosses a boundary (LangGraph state, MCP
responses, agent I/O, ledger rows) is defined here. Re-export everything
so callers can ``from film_pipeline.schemas import ProjectProfile``.
"""

from __future__ import annotations

from film_pipeline.schemas._base import (
    AgentFamily,
    AgentRole,
    ArtifactStatus,
    ArtifactType,
    FailureClass,
    FilmPhase,
    FilmType,
    GenerationMode,
    GenerationStatus,
    IssueSeverity,
    KbAuthority,
    ProviderStatus,
    QualityLevel,
    ReviewStrategy,
    SchemaBase,
    ValidationModality,
    ValidationScope,
    ValidationStatus,
    json_safe,
    to_camel,
)
from film_pipeline.schemas.approval import (
    ApprovalRecord,
    ReviewPackage,
    RevisionRequest,
)
from film_pipeline.schemas.artifact import (
    ArtifactMetadata,
    ArtifactRef,
    ArtifactVersion,
)
from film_pipeline.schemas.assembly import (
    AssemblyManifest,
    AssemblyPlanArtifact,
    AudioPlan,
    ClipOrderEntry,
    ColorPlan,
    TransitionPlan,
)
from film_pipeline.schemas.audit import AuditLogEntry
from film_pipeline.schemas.budget import BudgetState, CostEstimate, SpendRecord
from film_pipeline.schemas.camera import CameraLanguageBible, CameraProfile
from film_pipeline.schemas.character import (
    CharacterBible,
    CharacterIdentity,
    EmotionalArc,
    RelationshipMap,
    VoiceRules,
    WardrobeRules,
)
from film_pipeline.schemas.checkpoint import (
    BranchMetadata,
    CheckpointMetadata,
    InvalidationReport,
    RollbackOutcome,
    RollbackRecord,
)
from film_pipeline.schemas.continuity import (
    ContinuityLedger,
    ContinuityLedgerEntry,
    StateRecord,
)
from film_pipeline.schemas.delivery import DeliveryManifest, DeliveryPackage
from film_pipeline.schemas.environment import (
    EnvironmentBible,
    EnvironmentFingerprint,
    EnvironmentZone,
    LightingState,
    Viewpoint,
)
from film_pipeline.schemas.failure import FailureDecision, FailureRecoveryRecord
from film_pipeline.schemas.film_constitution import CharacterTruth, FilmConstitution
from film_pipeline.schemas.generation import (
    GenerationLedger,
    GenerationLedgerRow,
    GenerationPlan,
    GenerationRequest,
    ResumeToken,
    ShotPlan,
)
from film_pipeline.schemas.handoff import (
    AgentHandoff,
    AgentRegistration,
    RoutingDecision,
)
from film_pipeline.schemas.issue import IssueRecord
from film_pipeline.schemas.kb import (
    KBConflictRecord,
    KBContextPacket,
    KBExcludedRef,
    KBItemMetadata,
)
from film_pipeline.schemas.matrix import (
    ChainingConfig,
    CoverageGroup,
    MasterFilmMatrix,
    MasterFilmMatrixRow,
)
from film_pipeline.schemas.project import ProjectConfig, ProjectIdentity, ProjectProfile
from film_pipeline.schemas.prompt import PromptRegistry, PromptRegistryEntry, RCTCOPrompt
from film_pipeline.schemas.provider_health import ProviderHealthState
from film_pipeline.schemas.reference import (
    CompositeSheetManifest,
    ReferenceAIUsability,
    ReferenceFrame,
    ReferenceIndex,
    ReferenceIndexEntry,
    ReferenceStrategy,
    ReferenceValidationSummary,
    TileEntry,
)
from film_pipeline.schemas.registries import (
    AgentRegistryEntry,
    CostProfile,
    ModelRegistry,
    ModelRegistryEntry,
    ProviderCapabilities,
    ProviderRegistry,
    ProviderRegistryEntry,
    ValidatorRegistry,
    ValidatorRegistryEntry,
    ValidatorThresholds,
)
from film_pipeline.schemas.story_bible import (
    ActMap,
    Logline,
    Premise,
    SceneIntent,
    SceneList,
    SetupPayoffEntry,
    StoryBible,
    Treatment,
)
from film_pipeline.schemas.style import StyleBible
from film_pipeline.schemas.subtitle import SubtitleArtifact, SubtitleCue
from film_pipeline.schemas.validation import (
    ConsensusReport,
    ReviewerScore,
    ValidationIssue,
    ValidationLedgerEntry,
    ValidationReport,
)

__all__ = [
    "ActMap",
    "AgentFamily",
    "AgentHandoff",
    "AgentRegistration",
    "AgentRegistryEntry",
    "AgentRole",
    "ApprovalRecord",
    "ArtifactMetadata",
    "ArtifactRef",
    "ArtifactStatus",
    "ArtifactType",
    "ArtifactVersion",
    "AssemblyManifest",
    "AssemblyPlanArtifact",
    "AudioPlan",
    "AuditLogEntry",
    "BranchMetadata",
    "BudgetState",
    "CameraLanguageBible",
    "CameraProfile",
    "ChainingConfig",
    "CharacterBible",
    "CharacterIdentity",
    "CharacterTruth",
    "CheckpointMetadata",
    "ClipOrderEntry",
    "ColorPlan",
    "CompositeSheetManifest",
    "ConsensusReport",
    "ContinuityLedger",
    "ContinuityLedgerEntry",
    "CostEstimate",
    "CostProfile",
    "CoverageGroup",
    "DeliveryManifest",
    "DeliveryPackage",
    "EmotionalArc",
    "EnvironmentBible",
    "EnvironmentFingerprint",
    "EnvironmentZone",
    "FailureClass",
    "FailureDecision",
    "FailureRecoveryRecord",
    "FilmConstitution",
    "FilmPhase",
    "FilmType",
    "GenerationLedger",
    "GenerationLedgerRow",
    "GenerationMode",
    "GenerationPlan",
    "GenerationRequest",
    "GenerationStatus",
    "InvalidationReport",
    "IssueRecord",
    "IssueSeverity",
    "KBConflictRecord",
    "KBContextPacket",
    "KBExcludedRef",
    "KBItemMetadata",
    "KbAuthority",
    "LightingState",
    "Logline",
    "MasterFilmMatrix",
    "MasterFilmMatrixRow",
    "ModelRegistry",
    "ModelRegistryEntry",
    "Premise",
    "ProjectConfig",
    "ProjectIdentity",
    "ProjectProfile",
    "PromptRegistry",
    "PromptRegistryEntry",
    "ProviderCapabilities",
    "ProviderHealthState",
    "ProviderRegistry",
    "ProviderRegistryEntry",
    "ProviderStatus",
    "QualityLevel",
    "RCTCOPrompt",
    "ReferenceAIUsability",
    "ReferenceFrame",
    "ReferenceIndex",
    "ReferenceIndexEntry",
    "ReferenceStrategy",
    "ReferenceValidationSummary",
    "RelationshipMap",
    "ResumeToken",
    "ReviewPackage",
    "ReviewStrategy",
    "ReviewerScore",
    "RevisionRequest",
    "RollbackOutcome",
    "RollbackRecord",
    "RoutingDecision",
    "SceneIntent",
    "SceneList",
    "SchemaBase",
    "SetupPayoffEntry",
    "ShotPlan",
    "SpendRecord",
    "StateRecord",
    "StoryBible",
    "StyleBible",
    "SubtitleArtifact",
    "SubtitleCue",
    "TileEntry",
    "TransitionPlan",
    "Treatment",
    "ValidationIssue",
    "ValidationLedgerEntry",
    "ValidationModality",
    "ValidationReport",
    "ValidationScope",
    "ValidationStatus",
    "ValidatorRegistry",
    "ValidatorRegistryEntry",
    "ValidatorThresholds",
    "Viewpoint",
    "VoiceRules",
    "WardrobeRules",
    "json_safe",
    "to_camel",
]
