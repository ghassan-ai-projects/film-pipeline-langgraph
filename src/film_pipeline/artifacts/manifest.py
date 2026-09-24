"""Asset manifests for generated media, references, frames, and delivery."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AssetEntry(BaseModel):
    """A single generated or reference asset in a project.

    ``path`` is project-relative so a project directory can be moved or
    archived without breaking the manifest; ``sha256`` pins the content.
    """

    asset_id: str
    path: str
    kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem
    scene_id: str = ""
    shot_id: str = ""
    take: int = 1
    active: bool = True
    sha256: str = ""


class AssetManifest(BaseModel):
    """Flat manifest of all assets in a project."""

    project_id: str
    entries: list[AssetEntry] = Field(default_factory=list)

    def add(self, entry: AssetEntry) -> None:
        self.entries.append(entry)

    def add_take(self, entry: AssetEntry) -> None:
        """Add a take and enforce the invariant: one active clip per shot.

        The new clip's take becomes the active one; earlier clips of the
        same shot are deactivated.
        """
        if entry.kind == "generated_clip" and entry.active:
            for existing in self.entries:
                if existing.shot_id == entry.shot_id and existing.kind == "generated_clip":
                    existing.active = False
        self.entries.append(entry)

    def active_take(self, shot_id: str) -> AssetEntry | None:
        for e in self.entries:
            if e.shot_id == shot_id and e.kind == "generated_clip" and e.active:
                return e
        return None

    def list_by_kind(self, kind: str) -> list[AssetEntry]:
        return [e for e in self.entries if e.kind == kind]

    def list_by_scene(self, scene_id: str) -> list[AssetEntry]:
        return [e for e in self.entries if e.scene_id == scene_id]

    def list_by_shot(self, shot_id: str) -> list[AssetEntry]:
        return [e for e in self.entries if e.shot_id == shot_id]


def read_manifest(project_id: str, root: Path) -> AssetManifest | None:
    manifest_path = root / project_id / "asset-manifest.json"
    if not manifest_path.exists():
        return None

    data = manifest_path.read_text()
    manifest = AssetManifest.model_validate_json(data)
    return manifest.model_copy(update={"project_id": project_id})


def write_manifest(manifest: AssetManifest, root: Path) -> None:
    manifest_path = root / manifest.project_id / "asset-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2))
