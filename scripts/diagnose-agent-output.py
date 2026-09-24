"""Diagnose real LLM agent output — print raw model response + validation result.

Usage: python scripts/diagnose-agent-output.py [constitution|development|script|all]

Calls each agent's prompt template through the real model adapter, prints:
1. Raw model output (JSON dict)
2. Execute result keys
3. Validate result
4. Pydantic ValidationError details if construction fails
"""

import json
import os
import sys
from pathlib import Path

os.chdir("/Users/ghassan/my-projects/film-pipeline-langgraph")

# Load API keys
env_file = Path(".env")
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

os.environ["FILM_PIPELINE_MCP_MODE"] = "real"

from _scratch_bootstrap import use_scratch_roots

use_scratch_roots()

from film_pipeline.agents.impl.constitution_agent import ConstitutionAgent
from film_pipeline.agents.impl.development_agent import DevelopmentAgent
from film_pipeline.agents.impl.screenwriter_agent import ScreenwriterAgent
from film_pipeline.agents.model_adapter import ModelAdapter
from film_pipeline.agents.model_routing import ModelRouter
from film_pipeline.agents.prompt_templates.registry import get_registry
from film_pipeline.schemas.handoff import AgentFamily, AgentRegistration, AgentRole

# ── Setup ────────────────────────────────────────────────────────────────
reg = get_registry()
adapter = ModelAdapter()
router = ModelRouter()

PROJECT_ID = "diagnose-001"
IDEA = (
    "A silent four-minute pilgrimage short follows a young walker crossing five "
    "changing fields while birds, rain, blossoms, and insects pass a single "
    "message between sky and earth."
)


# Fake contract for agent instantiation
def _fake_contract(agent_id: str):
    return AgentRegistration(
        agent_id=agent_id,
        role=AgentRole.CREATOR,
        family=AgentFamily.DEVELOPMENT,
        allowed_kb_domains=[],
        blocked_kb_domains=[],
        capabilities=["text_generation"],
        output_artifacts=[],
        reviewed_by=[],
        failure_modes=[],
    )


def diagnose_agent(
    agent_id: str, agent_cls, model_profile: str, task: str, context_vars: dict[str, str]
):
    print(f"\n{'=' * 70}")
    print(f"🔍 {agent_cls.__name__} (profile={model_profile})")
    print(f"{'=' * 70}")

    # 1. Get template and render
    template = reg.get_required(agent_id)
    rendered = template.render(**context_vars)
    print(f"\n📝 Template: {template.template_id} v{template.version}")
    print(f"   Prompt length: {len(rendered)} chars")

    # 2. Call model
    model_id, max_tokens, temperature, top_p, freq_pen = router.resolve_model_params(model_profile)
    print(f"   Model: {model_id} (temp={temperature}, max_tokens={max_tokens})")

    from pydantic import ValidationError as PydanticValidationError

    try:
        raw = adapter.chat_json(
            rendered,
            model=model_id,
            system=template.role,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            frequency_penalty=freq_pen,
        )
    except ValueError as e:
        print(f"\n❌ chat_json failed (JSON parse): {e}")
        return

    print(f"\n📤 Raw model output keys: {sorted(raw.keys())}")
    print(
        f"   Top-level structure: {json.dumps({k: type(v).__name__ for k, v in raw.items()}, indent=2)}"
    )

    # 3. Execute
    agent = agent_cls(_fake_contract(agent_id))
    state = {
        "project_id": PROJECT_ID,
        "idea": IDEA,
    }
    kb = None  # Not needed for diagnose

    try:
        result = agent.run(state, kb, task, raw)
        print("\n✅ execute() succeeded")
        print(f"   Result keys: {sorted(result.keys())}")
        for key, val in result.items():
            if hasattr(val, "__class__"):
                print(f"   {key}: {val.__class__.__name__}")
                # Print first few fields
                if hasattr(val, "model_dump"):
                    dumped = val.model_dump()
                    for fk, fv in list(dumped.items())[:3]:
                        fv_str = str(fv)[:100]
                        print(f"     .{fk}: {fv_str}")
        print("   validate(): ✅ True")
    except ValueError as e:
        msg = str(e)
        print(f"\n❌ Agent raised ValueError: {msg[:500]}")
    except PydanticValidationError as e:
        print(f"\n❌ Pydantic ValidationError ({len(e.errors())} errors):")
        for err in e.errors()[:10]:
            loc = ".".join(str(x) for x in err["loc"])
            print(f"   - {loc}: {err['msg']} (type={err.get('type')})")
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}: {e}")


# ── Mock upstream artifacts for context injection ──────────────────────────

constitution_content = json.dumps(
    {
        "project_id": PROJECT_ID,
        "theme": "Hope travels on the smallest wings.",
        "tone": "serene, melancholic, transcendent",
        "emotional_promise": "A quiet realization that nature already holds every message we need.",
        "visual_language": "static camera, natural light, painterly compositions",
        "camera_philosophy": "observational, breath-paced, never intrusive",
        "quality_bar": "Every frame could be a painting.",
        "character_truths": [
            {"character_id": "walker", "truth": "Never speaks, only walks."},
        ],
        "taboo_mistakes": ["No dialogue.", "No modern technology."],
    }
)

treatment_content = json.dumps(
    {
        "text": "A young walker crosses five fields, each carrying a fragment of a message from sky to earth.",
        "themes": ["connection", "stillness", "passage"],
        "act_map": {
            "act1_setup": "Walker enters first field. Birds pass a whisper.",
            "act2_confrontation": "Rain and blossoms obscure the message. Walker hesitates.",
            "act3_resolution": "Insects carry the final fragment. Walker understands without words.",
        },
    }
)

scene_list_content = json.dumps(
    {
        "scenes": [
            {
                "scene_id": "s_001",
                "dramatic_function": "Opening image.",
                "emotional_shift": "peace → anticipation",
                "conflict": "walker vs. silence",
                "outcome": "Walker begins.",
            },
            {
                "scene_id": "s_002",
                "dramatic_function": "First message fragment.",
                "emotional_shift": "anticipation → wonder",
                "conflict": "walker vs. distance",
                "outcome": "Birds deliver fragment.",
            },
            {
                "scene_id": "s_003",
                "dramatic_function": "Climax — final fragment.",
                "emotional_shift": "doubt → clarity",
                "conflict": "walker vs. impermanence",
                "outcome": "Message complete.",
            },
        ],
    }
)

# ── Run diagnostics ────────────────────────────────────────────────────────

target = sys.argv[1] if len(sys.argv) > 1 else "all"

if target in ("constitution", "all"):
    diagnose_agent(
        agent_id="film-constitution-agent",
        agent_cls=ConstitutionAgent,
        model_profile="creative_writer",
        task="Define the film's creative constitution.",
        context_vars={
            "project_id": PROJECT_ID,
            "idea": IDEA,
            "kb_refs": "",
        },
    )

if target in ("development", "all"):
    diagnose_agent(
        agent_id="treatment-agent",
        agent_cls=DevelopmentAgent,
        model_profile="creative_writer",
        task="Develop the film treatment and scene breakdown.",
        context_vars={
            "project_id": PROJECT_ID,
            "constitution_ref": "artifact:film_constitution:v1",
            "constitution_content": constitution_content,
            "target_runtime_seconds": "240",
            "film_type": "visual_poetry",
            "kb_refs": "",
        },
    )

if target in ("script", "all"):
    diagnose_agent(
        agent_id="screenwriter-agent",
        agent_cls=ScreenwriterAgent,
        model_profile="creative_writer",
        task="Write the complete screenplay.",
        context_vars={
            "project_id": PROJECT_ID,
            "treatment_ref": "artifact:treatment:v1",
            "treatment_content": treatment_content,
            "scene_list_ref": "artifact:scene_list:v1",
            "scene_list_content": scene_list_content,
            "constitution_ref": "artifact:film_constitution:v1",
            "constitution_content": constitution_content,
            "kb_refs": "",
        },
    )
