"""Run the full film pipeline for an old Chinese story via MCP stdio.

Usage: FILM_PIPELINE_MCP_MODE=mock uv run python test-full-pipeline.py
"""

import json
import os
import select
import subprocess
import sys
import time

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")

proc = subprocess.Popen(
    ["uv", "run", "python", "-m", "film_pipeline.mcp.server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=0,
)

_id = 1


def send(method, params=None):
    global _id
    req = {"jsonrpc": "2.0", "id": _id, "method": method}
    if params:
        req["params"] = params
    _id += 1
    body = json.dumps(req)
    msg = f"Content-Length: {len(body)}\r\n\r\n{body}"
    proc.stdin.write(msg)
    proc.stdin.flush()


def recv(timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        r, _, _ = select.select([proc.stdout], [], [], 0.5)
        if r:
            line = proc.stdout.readline()
            content_length = None
            while line and line.strip():
                if line.lower().startswith("content-length:"):
                    content_length = int(line.split(":", 1)[1].strip())
                line = proc.stdout.readline()
            if not line or content_length is None:
                return None
            body = proc.stdout.read(content_length)
            return json.loads(body)
    return None


def call(method, params=None, label=""):
    print(f"\n{'=' * 60}")
    print(f"{label or method}")
    print(f"{'=' * 60}")
    send(method, params)
    resp = recv()
    if resp:
        result = resp.get("result", resp.get("error", resp))
        ok = None
        if isinstance(result, dict) and "content" in result:
            for c in result["content"]:
                if c.get("type") == "text":
                    try:
                        parsed = json.loads(c["text"])
                        print(json.dumps(parsed, indent=2, ensure_ascii=False)[:3000])
                        ok = parsed.get("ok")
                    except json.JSONDecodeError:
                        print(c["text"][:500])
            ok = result.get("isError") is not True if ok is None else ok
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
        return result, ok
    print("(no response)")
    return None, False


# ===== STEP 1: Initialize =====
call(
    "initialize",
    {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "pipeline-test", "version": "1.0"},
    },
    "INITIALIZE",
)

# ===== STEP 2: Create project =====
project_id = "old-chinese-story-003"

# Note: create_film_project has mutates_state=True but doesn't accept project_ref.
# We pass project_id directly. The MCP server's call() won't resolve project_ref
# since none is provided in the envelope — it only appears in the arguments dict
# as a plain string, not as the envelope's project_ref.
r, ok = call(
    "tools/call",
    {
        "name": "create_film_project",
        "arguments": {
            "project_id": project_id,
            "title": "The Last Dragon Vein",
            "slug": "old-chinese-story",
        },
    },
    "CREATE PROJECT",
)
if not ok:
    print("❌ Project creation failed")
    proc.stdin.close()
    proc.wait(timeout=2)
    sys.exit(1)

# The MCPServer sets self.active_project_id on successfully resolved project_ref.
# create_film_project bypasses envelope resolution (no project_ref in args).
# But submit_idea reads from rt.get_active() which checks the runtime's active_project_id.
# Let's try submitting the idea directly (without set_active_project) since create_film_project
# runs through the same runtime singleton.

# ===== STEP 3: Submit idea =====
story = """A short film about an old Chinese ink wash painter living alone in a remote mountain village.
He has spent 70 years perfecting a single brushstroke — the 'dragon vein' stroke that brings
his paintings to life. When a young city photographer arrives documenting vanishing traditions,
the painter reluctantly teaches her his technique over one transformative autumn. Their unlikely
friendship bridges two worlds: analog vs digital, ancient vs modern, stillness vs speed.
The climax comes when the painter, facing his final stroke, must decide whether to complete
his masterpiece or leave it unfinished — a choice that will define whether his art lives
beyond him. The story is told with minimal dialogue, relying on visual poetry, the textures
of brush on rice paper, mountain mist, morning light through paper windows, and the contrast
between the chaotic energy of the city girl's photography and the patient stillness of the
old man's world."""

call("tools/call", {"name": "submit_idea", "arguments": {"idea": story}}, "SUBMIT IDEA")

# ===== STEP 4: Check project state after intake =====
call(
    "tools/call", {"name": "get_project_summary", "arguments": {}}, "PROJECT SUMMARY (after intake)"
)

# ===== STEP 5: Approve intake =====
call("tools/call", {"name": "approve_intake", "arguments": {}}, "APPROVE INTAKE")

# ===== STEP 6: Approve constitution =====
call("tools/call", {"name": "approve_phase", "arguments": {}}, "APPROVE CONSTITUTION")

# ===== STEP 7: Approve development (treatment) =====
call("tools/call", {"name": "approve_phase", "arguments": {}}, "APPROVE DEVELOPMENT (treatment)")

# ===== STEP 8: Approve script =====
call("tools/call", {"name": "approve_phase", "arguments": {}}, "APPROVE SCRIPT")

# ===== STEP 9: Get full state =====
call(
    "tools/call", {"name": "get_project_summary", "arguments": {}}, "PROJECT SUMMARY (after script)"
)

# ===== STEP 10: Generate bibles =====
call(
    "tools/call", {"name": "generate_character_bible", "arguments": {}}, "GENERATE CHARACTER BIBLE"
)

call(
    "tools/call",
    {"name": "generate_environment_bible", "arguments": {}},
    "GENERATE ENVIRONMENT BIBLE",
)

call("tools/call", {"name": "generate_camera_bible", "arguments": {}}, "GENERATE CAMERA BIBLE")

call("tools/call", {"name": "generate_style_bible", "arguments": {}}, "GENERATE STYLE BIBLE")

# ===== STEP 11: Approve visual_dev =====
call("tools/call", {"name": "approve_phase", "arguments": {}}, "APPROVE VISUAL DEV")

# ===== STEP 12: Generate reference images =====
call(
    "tools/call",
    {"name": "generate_reference_images", "arguments": {}},
    "GENERATE REFERENCE IMAGES",
)

# ===== STEP 13: Approve post-refs =====
call("tools/call", {"name": "approve_phase", "arguments": {}}, "APPROVE POST-REFS")

# ===== STEP 14: Generate shot bible =====
call("tools/call", {"name": "generate_shot_bible", "arguments": {}}, "GENERATE SHOT BIBLE")

# ===== STEP 15: Budget + Plan =====
call(
    "tools/call", {"name": "initialize_budget", "arguments": {"cap_usd": 50.0}}, "INITIALIZE BUDGET"
)

call("tools/call", {"name": "generate_plan", "arguments": {}}, "GENERATE PLAN")

# ===== STEP 16: Check orchestrator =====
call("tools/call", {"name": "get_orchestrator_summary", "arguments": {}}, "ORCHESTRATOR SUMMARY")

# ===== STEP 17: Final state =====
call("tools/call", {"name": "get_project_summary", "arguments": {}}, "FINAL PROJECT SUMMARY")

# ===== STEP 18: Check artifact store =====
import os as _os

projects_dir = "projects"
if _os.path.isdir(projects_dir):
    for root, _dirs, files in _os.walk(projects_dir):
        depth = root.replace(projects_dir, "").count(os.sep)
        if depth > 4 or not files:
            continue
        indent = "  " * depth
        for f in files[:5]:
            print(f"{indent}{root.split('/')[-1]}/{f}")
        if len(files) > 5:
            print(f"{indent}... ({len(files)} files)")

# Cleanup
proc.stdin.close()
proc.wait(timeout=3)
stderr = proc.stderr.read()
if stderr:
    lines = stderr.strip().split("\n")
    print(f"\n=== STDERR ({len(lines)} lines) ===")
    for l in lines[-5:]:
        print(l)
