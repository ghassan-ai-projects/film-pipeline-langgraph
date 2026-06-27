"""Asset manifolds for generated media, references, frames, and delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AssetEntry:
    asset_id: str
    path: str
    kind: str  # reference_sheet, generated_clip, last_frame, mid_frame, audio_stem
    scene_id: str = ""
    shot_id: str = ""
    take: int = 1
    active: bool = True


@dataclass
class AssetManifest:
    """Flat manifest of all assets in a project."""

    project_id: str
    entries: list[AssetEntry] = field(default_factory=list)

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
    import json

    data = json.loads(manifest_path.read_text())
    return AssetManifest(
        project_id=project_id,
        entries=[AssetEntry(**e) for e in data.get("entries", [])],
    )


def write_manifest(manifest: AssetManifest, root: Path = Path("projects")) -> None:
    import json

    manifest_path = root / manifest.project_id / "asset-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {"project_id": manifest.project_id, "entries": [vars(e) for e in manifest.entries]},
            indent=2,
        )
    )
