"""Asset manifests for generated media, references, frames, and delivery."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AssetEntry(BaseModel):
    """A single generated or reference asset in a project."""

    asset_id: str
    path: str
    kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem
    scene_id: str = ""
    shot_id: str = ""
    take: int = 1
    active: bool = True


class AssetManifest(BaseModel):
    """Flat manifest of all assets in a project."""

    project_id: str
    entries: list[AssetEntry] = Field(default_factory=list)

    def add(self, entry: AssetEntry) -> None:
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


def read_manifest(project_id: str, root: Path = Path("projects")) -> AssetManifest | None:
    manifest_path = root / project_id / "asset-manifest.json"
    if not manifest_path.exists():
        return None

    data = manifest_path.read_text()
    manifest = AssetManifest.model_validate_json(data)
    return manifest.model_copy(update={"project_id": project_id})


def write_manifest(manifest: AssetManifest, root: Path = Path("projects")) -> None:
    manifest_path = root / manifest.project_id / "asset-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2))
