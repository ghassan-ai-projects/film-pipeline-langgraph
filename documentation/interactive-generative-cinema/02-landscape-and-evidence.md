# Interactive Generative Cinema — Landscape and Evidence

Status: desk-research evidence review  
Evidence cutoff and access date for every web source: **2026-08-25**

## Scope and method

This report asks what the external landscape establishes about the fixed anchor in
`00-research-plan.md`: a single viewer, a 10–12 minute stylized dramatic mystery, three
stable adult characters, two locations, four governed intervention windows, a material
consequence within two 20–60 second segments, three authored ending classes, and an
inspectable, exactly replayable delivered manifest.

It does not treat the following as equivalent:

- selecting among finished clips;
- steering a story-state or dialogue generator;
- controlling a character inside a rendered simulation;
- steering the pixels of an autoregressive video stream;
- generating and editing an episode asynchronously.

Product availability was checked from first-party product pages or documentation. Research
claims come from papers, project pages, or official model documentation. Credible reporting
is used to establish removals, independent observation, and facts that vendors do not
publish. Vendor-supplied audience numbers and demonstrations remain vendor evidence. No
system was exercised, no provider was benchmarked, and no creator or viewer was interviewed
for this report.

Claim labels are explicit:

- **Fact** means the cited source directly supports the statement in its stated scope.
- **Inference** means the conclusion is drawn from named facts but has not itself been tested.
- **Unknown** means public evidence was not found; it does not imply failure.

## Executive findings

1. **Fact — interactive screen stories have repeatedly shipped.** `Kinoautomat` used nine
   audience votes in 1967. Netflix shipped interactive branching titles from 2017 and made
   *Bandersnatch* in 2018. Game and livestream formats continue the same family of ideas.
   Interactivity itself is not the speculative part.

2. **Fact — the largest dedicated streaming-film deployment was discontinued.** Netflix
   removed most interactive specials in December 2024 and the final two in May 2025. Its
   spokesperson said the technology had served its purpose but had become limiting while
   Netflix focused elsewhere. Netflix did not publish the retention, cost, or causal demand
   data needed to say precisely why the format did not persist.

3. **Fact — free-form generative narrative is a shipped text experience, and bounded
   generative characters are entering games.** AI Dungeon accepts open text inside persistent
   scenarios. Inworld/NVIDIA-style character stacks and KRAFTON's Smart Zois connect language
   models to authored game state and actions. Ubisoft has shown playable but explicitly
   experimental NPC systems. These products establish useful control-plane patterns, not
   cinematic audiovisual generation.

4. **Fact — generative episode making exists, but it is an asynchronous creation workflow.**
   Fable's Showrunner lets users make animated scenes or episodes in a constrained simulated
   world. The public product and its own research describe prompts, simulations, scene
   generation, and user evaluation after generation—not uninterrupted playback whose future
   is regenerated inside a 30-second consequence SLO.

5. **Fact — real-time generative pixels are now credible research, not yet proof of a
   movie.** Google Genie 3 reports 720p at 24 fps with consistency for a few minutes;
   Odyssey-2 reports 20 fps and multi-minute streams; NVIDIA/MIT LongLive reports 20.7 fps
   for up to 240 seconds on one H100, and LongLive 2.0 reports higher throughput. Public
   examples are short or minute-scale, mostly navigational or prompt-transition demonstrations.
   Google labels Project Genie an experimental prototype, limits a user run to 60 seconds,
   and reports imperfect prompt adherence, physics, character control, and latency.

6. **Fact — production clip generators remain clip-oriented.** Current Veo 3 Vertex AI
   documentation limits outputs to 4, 6, or 8 seconds, and provisioned-throughput guidance
   says a four-second job can complete in “a few minutes.” Runway Gen-4 produces 5- or
   10-second clips. These systems can supply precomputed assets and transitions, but their
   documented interfaces do not meet live playback timing.

7. **Inference — a bounded hybrid is supported; a fully generative film is not.** The
   evidence supports an authored story-state/drama manager, deterministic artifact and game
   state, cached or pre-rendered dramatic beats, generated dialogue or transitions, and a
   controlled renderer. It does not support entrusting the whole 10–12 minute dramatic and
   audiovisual state to one autoregressive media model.

8. **Unknown — market demand for one private movie per viewer.** Public sources show novelty,
   investment, user participation, and some large vendor-reported engagement. They do not
   publish a controlled comparison against a linear film, a pre-rendered branching film, and
   a game-like alternative on completion, satisfaction, repeat use, willingness to pay, or
   creator economics.

## 1. Interactive-film precedents and the persistence question

### 1.1 Kinoautomat: interaction was also a performance

**Shipped event, not generative.** *Kinoautomat: One Man and His House* premiered at Expo 67.
At nine points, a moderator asked the theater audience to vote between two filmed options.
Two projectors ran in parallel so the selected scene could be revealed without stopping film.
The paths reconverged on the same burning-building ending. A historical analysis describes
the design as quasi-looping rather than a continuously expanding branch and emphasizes that
the live moderator and group deliberation were part of the work, not incidental plumbing
([Screening the Past](https://www.screeningthepast.com/issue-37-first-release/interactive-cinema-from-vending-machine-to-database-narrative-the-case-of-kinoautomat/)).

**What it proves against the anchor.** Discrete decisions can create anticipation and social
meaning even when the filmed material is fixed and paths reconverge. It also demonstrates a
durable technique for containing branch growth.

**What it does not prove.** Individual agency, natural-language direction, audiovisual
generation, persistent per-viewer state, or materially different endings. Its shared vote
and live host are a different interaction grammar from the single-viewer anchor.

### 1.2 Netflix: globally shipped branching, bespoke production, then removal

**Shipped product, not generative.** Netflix announced its first branching children's
episodes in 2017 and explicitly described viewers choosing how the story proceeds
([Netflix announcement](https://about.netflix.com/en/news/interactive-storytelling-on-netflix-choose-what-happens-next)).
For *Black Mirror: Bandersnatch*, production created about 150 minutes of unique footage split
into roughly 250 segments for a typical experience of about 90 minutes. Reporting from the
production describes a bespoke Branch Manager and a complex Twine-like graph
([Wired production account](https://www.wired.com/story/bandersnatch-black-mirror-episode-explained/),
[Wired tool account](https://www.wired.com/story/black-mirror-bandersnatch-interactive-episode/)).

The delivery design is directly relevant. Multiple future video segments were buffered to
make a chosen transition feel seamless; client buffer capacity limited how much could be
prefetched ([Streaming Media engineering interview](https://www.streamingmedia.com/Articles/Editorial/Featured-Articles/Streaming-Sites-Crunch-the-Numbers-on-Interactive-Video-132556.aspx)).
That is a production precedent for the anchor's rolling-horizon and safe-fallback options.

**Discontinuation evidence.** Netflix removed most of its interactive catalog in December
2024. A spokesperson said: “The technology served its purpose, but is now limiting as we
focus on technological efforts in other areas”
([The Verge report republished by Yahoo](https://www.yahoo.com/entertainment/netflix-pulling-interactive-titles-platform-105138599.html)).
The final two titles, *Bandersnatch* and *Unbreakable Kimmy Schmidt: Kimmy vs. the Reverend*,
were removed on May 12, 2025
([Variety report republished by Yahoo](https://www.yahoo.com/entertainment/articles/black-mirror-bandersnatch-getting-pulled-125444046.html)).

**Fact.** A major streaming platform proved choice-aware authoring, playback, buffering, and
global delivery, then retired that specific interactive-special stack.

**Inference.** The bespoke authoring graph, unused filmed material, multi-path QA, client
compatibility, and prefetch requirements create production and platform carrying cost that a
linear title does not. This is consistent with the removal but is not a demonstrated causal
explanation for it.

**Unknown.** Netflix did not publish title-level completion, retention, incremental subscriber
value, marginal cost, creator-hours per delivered minute, or a postmortem. “The audience did
not want interactive stories” would therefore be an unsupported conclusion. Netflix also
continued investing in narrative games, which suggests category migration is at least as
plausible as category rejection
([Netflix Q2 2024 shareholder letter](https://ir.netflix.net/files/doc_financials/2024/q2/FINAL-Q2-24-Shareholder-Letter.pdf)).

### 1.3 Rival Peak: a shared live simulation can be watched as television

**Shipped limited season, game-engine rendered, collectively interactive.** In 2020–2021,
*Rival Peak* ran thirteen 24/7 livestreams for twelve weeks. Twelve planner-driven characters
lived in a Unity simulation; viewers influenced goals, tasks, weather, scoring, and weekly
elimination. The planner was deterministic, while a separate simulation handled game and
animation logic
([Genvid/Pipeworks announcement](https://genvid.com/2020/12/01/genvid-technologies-and-pipeworks-studios-introduce-rival-peak/),
[technical account by its lead AI engineer](https://www.gamedeveloper.com/programming/the-a-i-behind-unique-interactive-reality-tv-game-i-rival-peak-i-)).

AWS's customer study says one authoritative simulation fed many viewers, the streams were
archived to object storage, and weekly scripts were adjusted after aggregated interactions.
Only fourteen connected GPU units ran the live experience, though development, QA, staging,
and production required hundreds of GPUs
([AWS customer story](https://aws.amazon.com/blogs/gametech/genvid-rival-peak-customer-story/)).

The operator's retrospective reports that communal vote results could take up to 90 seconds,
so mini-games were added to occupy the wait. It also reports UI confusion, demand for recaps,
and the need to add maps and tutorials
([Game Developer retrospective](https://www.gamedeveloper.com/business/the-real-time-evolution-of-i-rival-peak-i-)).
The same retrospective gives vendor-reported engagement—more than 100 million viewer-minutes
and millions of views per companion episode—but supplies no independent denominator or
retention cohort.

**What it proves against the anchor.** A deterministic world simulation, AI character planner,
cloud rendering, video delivery, collective input, archives, and human editorial layer can be
operated together for weeks. Interaction latency can be masked with an intentional secondary
experience. Human writers remained inside the loop.

**What it does not prove.** Per-viewer branches, cinematic rendering, free-form language,
private replayable manifests, individual causal agency, or economical one-GPU-per-viewer
delivery. One shared state amortizes compute in a way the anchor cannot silently assume.

### 1.4 What the historical record actually says about persistence

**Supported reasons or pressures:**

- content amplification and graph QA are observable in *Bandersnatch*'s 250 segments;
- smooth playback requires multiple possible futures to be buffered;
- choice UI, recaps, and “what changed?” feedback are product features, not incidental polish;
- branch convergence contains cost but can create false-choice risk;
- the live-simulation precedent amortized one world across an audience rather than generating
  a unique audiovisual branch per viewer;
- Netflix's dedicated interactive-special technology was removed as its platform priorities
  shifted.

**Not established:** that users intrinsically dislike agency, that branching cannot retain
viewers, that generation fixes authoring cost, or that interactivity belongs in cinema rather
than games. Public evidence is insufficient to choose among those explanations.

## 2. AI-native entertainment and generative narrative products

### 2.1 AI Dungeon: shipped open-ended narrative, text-only

**Shipped product.** AI Dungeon asks a player to select a setting and character and then
generates story responses from the player's text. Creators can configure AI instructions,
plot essentials, story cards, author notes, and scripts
([product basics](https://help.aidungeon.com/faq/the-basics),
[scenario documentation](https://help.aidungeon.com/faq/what-are-scenarios)). It supports
multiplayer under the host's selected model settings
([multiplayer documentation](https://help.aidungeon.com/faq/do-you-support-multiplayer)).

**Anchor relevance.** The split between stable scenario context and open user action is a
direct precedent for mapping a sentence into governed world state. It also demonstrates that
creative freedom, moderation, privacy, and inference economics are coupled product concerns;
the current moderation documentation says decrypted story elements must reach the model for
generation
([moderation documentation](https://help.aidungeon.com/faq/how-does-content-moderation-work)).

**Limit.** Text tolerates revision, latency, and representational ambiguity that finished
cinematic video does not. A language model can narrate around a contradiction; a changed face,
prop, voice, eyeline, or room layout is immediately visible. No public evidence transfers AI
Dungeon's engagement or coherence to audiovisual film.

### 2.2 Showrunner: generative animated episodes as creation, not live playback

**Available early product.** Fable's public Showrunner site offers episode creation through
Discord and says thousands of users have created episodes in its `Exit Valley` world
([Showrunner product page](https://www.showrunner.xyz/)). Its current studio page describes a
cast library, reusable characters, serialized worlds, remixing, and an iOS app as “coming
soon”
([Showrunner Studio](https://www.showrunnerstudio.com/)). These are first-party adoption and
roadmap claims; no independently audited usage or retention is public.

The preceding SHOW-1 paper describes a pipeline of large language models, custom diffusion,
multi-agent simulation, scene/dialogue generation, and user judgment. Its sample episode was
planned as fourteen dialogue scenes; the paper acknowledges a natural tension between
simulation-driven events and plot and says the team was still working on blending them
([SHOW-1 project paper](https://fablestudio.github.io/showrunner-agents/)).
The paper is a company research artifact, not peer-reviewed product evidence. It also labels
its *South Park* experiment unauthorized and non-commercial.

**Anchor relevance.** Persistent character/world definitions, reusable cast assets, a
simulation-to-scenes pipeline, and user remixing are close to the product thesis. The limited
animation style is a useful demonstration that style constraints make identity reuse more
tractable.

**Limit.** Public material shows “describe, generate, then watch/edit/share.” It does not
show a decision during uninterrupted viewing leading to a validated playable segment within
30 seconds. The site does not publish canon-violation rates, session manifests, exact replay,
generation latency percentiles, failure/fallback behavior, cost per minute, or controlled
viewer outcomes. Treat the strongest marketing formulation—personalized episodes—as evidence
of an adjacent creator product, not evidence that the anchor is solved.

### 2.3 Generative agents: social emergence is not dramatic structure

**Research.** The `Generative Agents` paper placed 25 language-model agents in a sandbox with
memory, reflection, and planning. In an evaluation, a single seed intention propagated into
invitations, acquaintances, dates, and coordinated attendance at a Valentine's party
([Park et al., 2023](https://arxiv.org/abs/2304.03442)). This is useful evidence that stored
experience and reflection can create legible local social behavior.

**Limit.** A believable daily routine is not a mystery arc. The experiment did not test
planted clues, dramatic obligations, three ending classes, audiovisual continuity, adversarial
viewer direction, safety gates, or exact media replay. Emergence can create material for a
story planner; it cannot be presumed to replace one.

### 2.4 Current classification

| Example | Current status | Viewer/creator input | Runtime output | Closest anchor variant | Evidence gap |
|---|---|---|---|---|---|
| AI Dungeon | Shipped service | Open text actions and creator-authored scenario controls | Generated text | Bounded natural-language direction | No audiovisual or cinematic timing proof |
| Showrunner | Early public creator product | Prompts, cast/world configuration, remix | Generated animated scenes/episodes after input | Asynchronous editing/generation | No intervention-during-playback SLO or audited continuity |
| Generative Agents | Research prototype | Seeded agent/world state | Text actions in a sandbox | Story-state simulation | No authored drama or delivered media |
| Rival Peak | Completed commercial season | Collective votes/clicks | One shared game-engine simulation streamed as video | Game-engine rendering | No private per-viewer version or free text |

## 3. AI NPCs, drama managers, and game-engine systems

### 3.1 Façade: the authoring cost of high agency was already visible in 2005

**Released research game.** *Façade* was a real-time one-act interactive drama in which
natural-language player input affected two characters and a deteriorating marriage. Its
architecture decomposed drama into behaviors and story beats and used a drama manager to
sequence them. The creators report that producing the experience required thousands of
joint-dialogue behaviors
([Mateas and Stern, 2005](https://ojs.aaai.org/index.php/AIIDE/article/view/18722)).

**Anchor relevance.** It is the clearest historical precedent for separating moment-to-moment
character reaction from a higher-level dramatic controller. It also shows why “the model can
talk” does not remove procedural authorship.

### 3.2 PaSSAGE and the bounded personalization result

**Research prototype with user study.** PaSSAGE learned player-style preferences and selected
pre-authored events accordingly. Its study found improved enjoyment, influence, and replay
appeal for certain subsets of 101 players compared with two fixed stories
([Thue thesis](https://rise.csit.carleton.ca/pubs/Thue_MSc_2007.pdf),
[AAAI paper](https://cs.uky.edu/~sgware/reading/papers/thue2007interactive.pdf)).

**Anchor relevance.** This is evidence for bounded adaptation using authored events, and
evidence against assuming one adaptive policy benefits every viewer.

**Limit.** It does not establish passive profiling as necessary or desirable; the anchor
excludes it. The result was a short RPG research experience, not film, and only some player
types benefited.

### 3.3 Versu: autonomous characters need explicit social semantics

**Released text system/research.** Versu represented recurring social situations as “social
practices” coordinating autonomous agents. Its design explicitly marked consequential
relationship changes and required active choice from affected characters
([Evans and Short paper](https://cs.uky.edu/~sgware/reading/papers/evans2014versu.pdf)).

**Anchor relevance.** Stable relationship transitions should be typed, inspectable state—not
inferred later from dialogue transcripts. This supports an explicit artifact/state contract
for promises, allegiances, suspicion, and revealed facts.

### 3.4 Current generative NPC deployments

**Shipped bounded feature.** KRAFTON's *inZOI* shipped an optional Smart Zoi feature in March
2025. A compact on-device language model turns a prompted life goal into actions and revises
the character's schedule from daily experience
([NVIDIA technical announcement](https://developer.nvidia.com/blog/nvidia-rtx-advances-with-neural-rendering-and-digital-human-technologies-at-gdc-2025/)).
NVIDIA ACE exposes speech, language, perception, and animation components for game
integration and lists assistants, teammates, enemies, and citizens as distinct patterns
([ACE developer page](https://developer.nvidia.com/ace)).

**Prototype/closed tests.** Ubisoft's NEO NPC was explicitly a research prototype, combining
Inworld language generation and NVIDIA facial animation with creator-authored personality,
backstory, agenda, and emotion. Ubisoft said every character detail still had to be crafted
and that the system had a long way to go before game implementation
([Ubisoft account](https://news.ubisoft.com/en-us/article/5qXdxhshJBXoanFZApdG3L/how-ubisofts-new-generative-ai-prototype-changes-the-narrative-for-npcs)).
Its later `Teammates` experiment added real-time voice commands and gameplay-aware companions
but remained a playable research project/closed test
([Ubisoft Teammates](https://news.ubisoft.com/en-us/article/3mWlITIuWuu0MoVuR6o8ps/ubisoft-reveals-teammates-an-ai-experiment-to-change-the-game)).

**Inference.** The production trend is to constrain a language model with authored character
state and expose only typed game actions, while retaining a deterministic engine as world
authority. That is a much closer fit to the anchor than allowing generated pixels or dialogue
to become authoritative state.

**What these systems do not prove.** They do not publish critical canon-violation rates,
narrative-arc completion, final-media continuity, exact replay from a model response, or the
authoring/review cost for a dramatic episode. An NPC can be locally responsive while the
overall story becomes flat, repetitive, or causally incoherent.

## 4. Generative video and world models

### 4.1 Production clip generation

**Veo 3 — production API, offline clips.** Current Vertex AI documentation lists 720p/1080p,
24 fps, generated audio, and 4-, 6-, or 8-second outputs, with ten requests per minute per
project on the documented model page
([Veo 3 model documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001)).
Provisioned-throughput documentation gives an example in which a four-second output can take
“a few minutes” and stresses that quota enforcement is not request latency
([Veo throughput documentation](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/veo-models)).

**Runway Gen-4 — shipped creator tool, offline clips.** Runway documents 5- and 10-second
outputs at 24 fps; the current page calls Gen-4 an older generation but its constraints
remain a useful public production baseline
([Runway Gen-4 documentation](https://help.runwayml.com/hc/en-us/articles/37327109429011-Creating-with-Gen-4-Video)).

**Fact.** These services are usable media suppliers. Their documented job interfaces and
durations do not meet the anchor's p95 30-second consequence hypothesis for a finished
20–60 second segment.

**Inference.** They are candidates for ahead-of-time branch assets, backgrounds, inserts,
and selectively generated transitions. They require scheduling, validation, retries, and a
ready fallback; “fast model” is not a playback protocol.

### 4.2 Real-time world models

**Genie 3 — research model and restricted product prototype.** Google DeepMind reports that
Genie 3 generates navigable worlds at 720p and 24 fps, remaining largely consistent for a few
minutes. It supports navigation plus “promptable world events” such as changing weather or
introducing objects and characters
([Genie 3 model report](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/)).
Google also names the limits: only a few minutes of continuous interaction, imperfect
real-location and text rendering, and memory of interaction changes for roughly a minute
([Genie model page](https://deepmind.google/models/genie/)).

Project Genie made a restricted form available to adult Google AI Ultra subscribers as an
experimental prototype. Google capped generations at 60 seconds, reported imperfect prompt
and physics adherence, sometimes-poor character control or higher control latency, and said
promptable world events were not yet in that product
([Project Genie product announcement](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/)).

**Odyssey-2/2 Pro — early product/API with vendor-only performance evidence.** Odyssey reports
that Odyssey-2 produces one frame every 50 ms (20 fps), starts streaming immediately, accepts
text while running, and produces multi-minute streams. Its own page calls world models
nascent and the applications unsolved
([Odyssey-2 announcement](https://odyssey.ml/introducing-odyssey-2)). In January 2026 it
announced Odyssey-2 Pro and API endpoints for interactive streams, shared viewable streams,
and offline simulations
([Odyssey-2 Pro/API announcement](https://odyssey.ml/the-gpt-2-moment-for-world-models)).
The legal terms still call the API a prototype
([Odyssey API terms](https://odyssey.ml/legal/api-terms)). No independent benchmark of its
latency, quality, continuity, capacity, pricing, or replay semantics was found.

**Oasis — public technology demonstration.** Decart labels Oasis a technology demonstration,
not a game or entertainment experience, and describes it as a real-time interactive model
learned from video and keyboard inputs
([Decart Oasis](https://www.decart.ai/)). It is useful existence evidence for action-conditioned
pixels, not product evidence.

### 4.3 Open research on real-time long video

**LongLive — peer-reviewed research/code, not a managed product.** LongLive uses causal
autoregressive generation and accepts streaming text prompts. The ICLR 2026 paper reports
20.7 fps on a single NVIDIA H100 and up to 240-second outputs
([NVIDIA Research](https://research.nvidia.com/labs/eai/publication/longlive/),
[ICLR paper](https://openreview.net/pdf?id=nCAODkpsPJ)). The project reports that LongLive 2.0
reaches 45.7 fps under one lower-quality two-step configuration and adds multi-shot support
([official repository](https://github.com/NVlabs/LongLive)).

**Helios — research preprint/code claim.** Helios reports a 14-billion-parameter diffusion
model producing minute-scale video at 19.5 fps on one H100, with text-, image-, and
video-conditioned modes
([Helios preprint](https://arxiv.org/abs/2603.04379)). It is not evidence of a supported
service or of narrative interaction.

**Important distinction.** Frame rate measures steady-state generation throughput under the
paper's hardware and configuration. It does not establish:

- time from a viewer sentence to an accepted story-state transition;
- semantic response distance;
- validation and moderation time;
- cold start or queue time;
- audio, dialogue, lip synchronization, editing, or caption generation;
- branch cancellation and wasted prefetch;
- concurrent-user capacity or cost;
- exact reproducibility after model or hardware change.

### 4.4 Capability table normalized to the anchor

| System | Evidence/status | What is controlled | Public horizon/throughput | Closest anchor use | Missing anchor proof |
|---|---|---|---|---|---|
| Veo 3 API | Shipped production clip API | Prompt/image depending model | 4/6/8 s; job may take minutes | Prefetched clips and transitions | Live consequence SLO; multi-scene identity; exact narrative state |
| Runway Gen-4 | Shipped creator tool | Image + prompt | 5/10 s, 24 fps output | Offline assets and transition trials | Live latency, long horizon, canon, replay |
| Genie 3 | Research model | Navigation and promptable events | Claimed 720p/24 fps, a few minutes | Game-like explorable environment | Drama, audio, three-character continuity, 10–12 min, API/SLO |
| Project Genie | Experimental subscriber prototype | Navigation/camera | 60 s product cap | Direct test of world feel | Promptable events absent; control/physics/latency limits |
| Odyssey-2 Pro | Prototype API/product | Text/action during a stream | Claimed 20 fps, minutes | Experimental rolling pixels | Independent measurements, audio, canon, cost, replay, load |
| Oasis | Technology demo | Keyboard actions | Real-time vendor demo | Action-conditioned renderer research | Product/API reliability and all film semantics |
| LongLive 1/2 | ICLR research + code | Sequential text prompts | 20.7 fps/240 s on H100; newer infra faster | Research benchmark for rolling video | Narrative causality, final quality, audio, service operations |
| Helios | Research preprint | T2V/I2V/V2V | Claimed 19.5 fps, minute scale on H100 | Local research baseline | Interactive story control and product evidence |

## 5. Long-form consistency and evaluation limits

### 5.1 Clip quality is not film continuity

VBench separates subject consistency, background consistency, flicker, motion smoothness,
dynamic degree, and per-frame visual quality because a model can score well on one while
failing another
([VBench, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Huang_VBench_Comprehensive_Benchmark_Suite_for_Video_Generative_Models_CVPR_2024_paper.pdf)).
VBench 2.0 argues that visually plausible output still may violate physics, commonsense,
anatomy, and compositional relations
([VBench 2.0](https://arxiv.org/abs/2503.21755)).

MovieBench was created because contemporary systems were primarily short, single-scene
generators that struggled with long, multi-scene stories and stable characters
([MovieBench, CVPR 2025](https://mlanthology.org/cvpr/2025/wu2025cvpr-moviebench/)).
The existence of newer minute-scale generators is progress, but these benchmarks remain
mostly visual/semantic evaluation. They do not measure whether a clue planted in minute two
causes the right choice-dependent revelation in minute ten.

**Inference.** The anchor needs at least three independent continuity layers:

1. authoritative symbolic state for facts, relationships, obligations, and branch causality;
2. asset/identity state for faces, voices, wardrobe, props, geography, and access tracks;
3. delivered-media validation for the actual pixels, sound, captions, and edits.

Passing a video benchmark cannot substitute for any of these.

### 5.2 Autoregressive drift and rollback

LongLive, Genie, and the long-video literature explicitly address accumulated error or
memory limits. Once a wrong face, object, or spatial relation becomes part of an
autoregressive context, later frames can preserve the error as if it were canon. A generated
stream is therefore a speculative render, not authoritative story state.

**Inference.** Commit should happen only after a segment passes structural and media checks.
On failure, the system needs an already playable authored/cached branch or must remain in an
intentional interaction state. It cannot rewind a viewer's memory of a visible contradiction.

### 5.3 Replay is a storage property before it is a model property

None of the examined world-model sources promises deterministic regeneration of the same
frames, dialogue, and safety decisions after a session. Model snapshots help attribute a
generation, but diffusion sampling, provider changes, and infrastructure still make exact
regeneration a different claim.

**Inference.** The anchor's 100% replay fidelity for retained artifacts is achievable only by
retaining the delivered segments and their immutable manifests. Storing prompts and random
seeds is useful provenance, not an exact-replay guarantee.

## 6. Cross-example anchor-comparability matrix

Legend: **Yes** = directly demonstrated in public evidence; **Partial** = bounded or materially
different demonstration; **No** = outside the system's design; **Unknown** = no adequate
public evidence.

| Example | Individual intervention during viewing | Free/bounded language | Generated AV after intervention | 10–12 min coherent drama | Stable 3-character identity | Consequence <= 2 segments | Exact delivered replay | Comparable conclusion |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Kinoautomat | No, group vote | No | No | Partial | Yes, filmed | Yes | Partial, fixed reels | Proves social value of authored choice and reconvergence |
| Netflix/Bandersnatch | Yes | No | No | Yes, authored | Yes, filmed | Yes | Partial/Unknown | Proves large-scale branching playback; retired platform warns on carrying cost |
| Rival Peak | No, collective | No | Partial, engine render | No, reality-show simulation | Partial | Partial, votes up to 90 s | Partial, archived shared stream | Proves shared simulation + broadcast, not private versions |
| AI Dungeon | Yes | Yes | No, text | Partial/Unknown | Textual only | Yes | Partial, log-based | Proves open input and scenario controls in text |
| Façade | Yes | Yes | Engine-rendered | Partial, one act | Yes, authored 3D | Yes | Unknown | Proves drama manager + reactive behavior, at high authoring cost |
| Showrunner | Creator action, not live viewing | Yes | Yes, async animation | Claimed episodes | Partial/Unknown | No public SLO | Unknown | Proves adjacent generative episode workflow only |
| inZOI Smart Zoi | Yes, during play | Bounded goal text | Engine-rendered | No | Yes, game assets | Partial | Game save, not media manifest | Proves typed model-to-engine action pattern |
| Genie 3/Project Genie | Yes | Partial | Yes, world stream | No | Unknown | Immediate navigation; event SLO unknown | Downloaded video only | Proves short explorable pixels; product cap is 60 s |
| Odyssey-2 Pro | Yes | Yes | Yes, world stream | No evidence | Unknown | Claimed real-time | Unknown | Early API is closest pixel substrate, not story proof |
| LongLive | Yes, sequential prompts | Yes | Yes | Up to 240 s, not drama | Unknown | Frame throughput only | Locally retainable output | Research basis for prompt-steerable rolling video |

No row satisfies all anchor columns. Combining rows is an architecture proposal, not evidence
that the integration will work.

## 7. Required-variant conclusions

### Variant 1 — discrete choices with mostly pre-rendered branches

**Landscape support: strong, product-proven.** Netflix and decades of interactive narrative
prove this can be authored and delivered. The main risks are distinctive viewer value,
authoring/QA amplification, cross-device support, and long-term platform ownership—not core
feasibility. The anchor can likely meet stall and replay targets using manifests, prefetch,
and fixed assets.

### Variant 2 — bounded natural-language direction with generated dialogue or transitions

**Landscape support: plausible and prototype-worthy.** AI Dungeon, Façade, Versu, current NPC
systems, and clip generators establish each component separately. The unproven integration is
mapping free text to a small intent vocabulary, changing authoritative story state, validating
the response, and delivering an audiovisual consequence without visible discontinuity. This
is the best landscape-supported place to test the project's distinctive thesis.

### Variant 3 — game-engine rendering with generated narrative/performance control

**Landscape support: strongest dynamic-media architecture.** Rival Peak, Smart Zois, ACE, and
Ubisoft's experiments show deterministic simulation/rendering coupled to bounded model
decisions. It trades photographic cinema for lower latency, stable spatial state, explicit
actions, recoverability, and cheaper reuse. It still needs a drama manager, creator tools,
voice/performance governance, and film-language quality; it risks becoming a game or animated
simulation rather than a movie.

### Variant 4 — rolling audiovisual generation with a precomputed horizon

**Landscape support: research-feasible, product-unproven.** Genie, Odyssey, LongLive, and
Helios establish minutes and approximately real-time frame throughput under narrow conditions.
The evidence does not establish final cinematic quality, multi-character dramatic continuity,
audio/access-track synchronization, safe branch generation, load, or bounded economics. A
prototype should isolate this as an optional renderer behind a fallback, not make it the only
playback path.

### Variant 5 — a 30–45 minute episode with persistent viewer history

**Landscape support: insufficient.** Showrunner demonstrates asynchronous episodic creation;
Rival Peak demonstrates persistent shared simulation; text systems demonstrate long-lived
state. No reviewed source demonstrates a single-viewer, continuously playable, choice-reactive
30–45 minute generated audiovisual drama with stable identities and exact replay. Branch
storage, accumulated drift, review amplification, deletion, and cost grow materially. This
variant belongs after the 10–12 minute anchor passes.

## 8. Why the landscape favors a hybrid architecture

The following is an inference from the combined precedents, not a claim that the repository
already implements it:

1. An **authored dramatic constitution and explicit world state** hold facts, invariants,
   unresolved questions, endings, permissions, and accepted viewer intent.
2. A **drama manager** selects or plans a bounded next beat. It can use model proposals, but
   only typed state transitions become authoritative.
3. A **render scheduler** races prefetched authored/cached segments, game-engine output, and
   selective generated dialogue/transitions inside a fixed horizon.
4. **Validators** check both symbolic consequences and delivered media. A model's self-report
   is not evidence of visual or narrative validity.
5. A **playback controller** always has a safe, disclosed future; waiting, repair, and fallback
   are measured rather than hidden.
6. An immutable **session manifest** records the delivered artifacts and decisions. Exact
   replay serves retained bytes, not regenerated guesses.

This composition preserves what each precedent is good at. It does not assume that joining
the parts is easy. The prototype must measure the integration boundary, especially latency,
state-to-media mismatch, cancellation waste, and whether users perceive a generated
transition as meaningfully causal rather than cosmetic.

## 9. Decision impact and evidence still required

### What the landscape supports now

- Position 1 (“reject the idea”) is not justified by technical impossibility. Multiple
  adjacent systems prove interactive narrative, model-steered characters, real-time rendering,
  and increasingly fast generated video.
- Position 4 (“near-term product direction”) is not justified. No source demonstrates the
  complete anchor under representative quality, latency, safety, cost, concurrency, creator,
  and viewer conditions.
- External evidence is compatible with **Position 2 or, if the repository and other
  workstreams satisfy every pre-prototype gate, a tightly bounded Position 3 experiment**.
- The lowest-risk experiment is not frame-by-frame photorealistic generation. It is an authored
  dramatic core with bounded language intent, explicit state, mostly ready media, and one or
  two selectively generated surfaces.

### Evidence required before upgrading confidence

1. A live, retained benchmark of at least two candidate providers and one local/research
   renderer, reporting p50/p95 cold and warm consequence latency, quality, retries, moderation,
   cancellation, and actual cost.
2. A deterministic story-state simulator that completes all anchor paths with zero critical
   canon violations before media generation is introduced.
3. A creator-authored comparison among a linear cut, a pre-rendered branching cut, and the
   bounded-language hybrid.
4. Independent human ratings of causal agency, coherence, ending quality, and identity
   continuity; no model-only judging.
5. A manifest/replay test that redelivers the exact watched artifacts after provider and worker
   failure.
6. A branch-amplification and authoring-time ledger, including discarded prefetched media and
   manual repair.
7. Accessibility-track regeneration and synchronization tests for every dynamic branch.
8. A rights-clean, entirely fictional anchor with documented authority for voice, music,
   character, style, and reference assets.
9. Load and denial-of-wallet tests at predeclared concurrency and spend caps.
10. A repeated-use viewer study. Novelty, waitlist size, views, or one-session enjoyment is not
    retention or willingness-to-pay evidence.

## 10. What this landscape does and does not prove

### It proves

- authored audiovisual branches can be delivered without visible transitions when futures
  are prefetched;
- interaction can be meaningful even when branches reconverge, but product design must make
  consequences legible;
- a deterministic simulation can combine persistent characters, audience input, human
  editorial control, cloud rendering, and video distribution;
- free text can drive continuing narrative and typed game actions inside bounded systems;
- generative animation/episode tools have reached early users;
- research models can generate action- or prompt-conditioned video around real-time frame
  rates for minute-scale horizons on high-end hardware;
- current production clip APIs are appropriate for offline or prefetched assets, not as the
  sole synchronous renderer under the anchor SLO;
- authoring, state control, interaction UX, replay, and fallback remain system problems even
  when generation becomes fast.

### It does not prove

- that viewers prefer changing a movie to watching a strong linear version;
- that a sentence produces *material* dramatic agency rather than a visual novelty;
- that any current system can preserve three characters, two locations, causality, pacing,
  voice, music, captions, and cinematic quality across the full anchor;
- that “real-time fps” includes intent parsing, policy, planning, validation, cold start,
  queueing, audio, delivery, and recovery;
- that per-viewer audiovisual generation is economic at meaningful concurrency;
- that vendor demos or generated episodes are replayable, attributable, rights-safe, or
  independently audited;
- that generative media reduces total creator work after world-building, branch review,
  correction, safety review, localization, and provenance are counted;
- that the Netflix discontinuation demonstrates lack of demand, or that current investment
  demonstrates durable demand;
- that combining a drama manager, NPC model, world model, renderer, and streaming stack will
  preserve their individual strengths without new failure modes.

The defensible conclusion is therefore precise: **the proposed medium is credible as a
bounded research program, and the most credible first form is hybrid. A fully generative,
on-the-fly movie remains an unproven target, not a current product capability.**

## Source inventory and limitations

All URLs below were accessed 2026-08-25. Sources are grouped by evidentiary role; their main
limitations are repeated here so they cannot be mistaken for stronger proof.

### Primary product, engineering, and company sources

- [Netflix: Interactive Storytelling](https://about.netflix.com/en/news/interactive-storytelling-on-netflix-choose-what-happens-next) — launch intent; no outcomes or costs.
- [Netflix Q2 2024 shareholder letter](https://ir.netflix.net/files/doc_financials/2024/q2/FINAL-Q2-24-Shareholder-Letter.pdf) — corporate portfolio evidence; not title-level evaluation.
- [Genvid/Pipeworks: Rival Peak announcement](https://genvid.com/2020/12/01/genvid-technologies-and-pipeworks-studios-introduce-rival-peak/) — shipped scope; promotional.
- [AWS: Rival Peak customer story](https://aws.amazon.com/blogs/gametech/genvid-rival-peak-customer-story/) — architecture and resource account; vendor/customer-authored.
- [AI Dungeon basics](https://help.aidungeon.com/faq/the-basics), [scenarios](https://help.aidungeon.com/faq/what-are-scenarios), [multiplayer](https://help.aidungeon.com/faq/do-you-support-multiplayer), and [moderation](https://help.aidungeon.com/faq/how-does-content-moderation-work) — current product behavior; no independent quality study.
- [Showrunner](https://www.showrunner.xyz/) and [Showrunner Studio](https://www.showrunnerstudio.com/) — current availability and first-party user claims; no audited usage/SLOs.
- [NVIDIA ACE](https://developer.nvidia.com/ace) and [Smart Zoi technical announcement](https://developer.nvidia.com/blog/nvidia-rtx-advances-with-neural-rendering-and-digital-human-technologies-at-gdc-2025/) — component and shipping claims; vendor/partner evidence.
- [Ubisoft NEO NPC](https://news.ubisoft.com/en-us/article/5qXdxhshJBXoanFZApdG3L/how-ubisofts-new-generative-ai-prototype-changes-the-narrative-for-npcs) and [Teammates](https://news.ubisoft.com/en-us/article/3mWlITIuWuu0MoVuR6o8ps/ubisoft-reveals-teammates-an-ai-experiment-to-change-the-game) — unusually clear prototype status; not production outcomes.
- [Veo 3 model docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/models/veo/3-0-generate-001) and [throughput docs](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/veo-models) — current documented limits; not a live measurement in this project.
- [Runway Gen-4 docs](https://help.runwayml.com/hc/en-us/articles/37327109429011-Creating-with-Gen-4-Video) — public product constraints for an older model generation.
- [Google Genie 3](https://deepmind.google/blog/genie-3-a-new-frontier-for-world-models/), [model limits](https://deepmind.google/models/genie/), and [Project Genie](https://blog.google/innovation-and-ai/models-and-research/google-deepmind/project-genie/) — first-party model and prototype evidence; curated examples and no service SLO.
- [Odyssey-2](https://odyssey.ml/introducing-odyssey-2), [Odyssey-2 Pro/API](https://odyssey.ml/the-gpt-2-moment-for-world-models), and [API terms](https://odyssey.ml/legal/api-terms) — first-party performance and availability; no independent validation.
- [Decart Oasis](https://www.decart.ai/) — explicitly a technology demonstration; not a product benchmark.

### Papers and research artifacts

- [Mateas and Stern: Façade architecture](https://ojs.aaai.org/index.php/AIIDE/article/view/18722) — peer-reviewed system account; 2005 technology and one authored work.
- [Thue et al.: PaSSAGE](https://cs.uky.edu/~sgware/reading/papers/thue2007interactive.pdf) and [101-participant thesis study](https://rise.csit.carleton.ca/pubs/Thue_MSc_2007.pdf) — bounded player-model result; not film or current models.
- [Evans and Short: Versu](https://cs.uky.edu/~sgware/reading/papers/evans2014versu.pdf) — explicit social-state design; text simulation.
- [Park et al.: Generative Agents](https://arxiv.org/abs/2304.03442) — research emergence evidence; no authored dramatic evaluation.
- [Fable: SHOW-1](https://fablestudio.github.io/showrunner-agents/) — company research artifact with useful architecture disclosure; not peer reviewed, no controlled product evaluation, and the sample IP was unauthorized.
- [LongLive project/paper](https://research.nvidia.com/labs/eai/publication/longlive/), [ICLR version](https://openreview.net/pdf?id=nCAODkpsPJ), and [official code](https://github.com/NVlabs/LongLive) — paper/code throughput evidence; not a managed entertainment service.
- [Helios](https://arxiv.org/abs/2603.04379) — current preprint; reported result not verified here.
- [VBench](https://openaccess.thecvf.com/content/CVPR2024/papers/Huang_VBench_Comprehensive_Benchmark_Suite_for_Video_Generative_Models_CVPR_2024_paper.pdf), [VBench 2.0](https://arxiv.org/abs/2503.21755), and [MovieBench](https://mlanthology.org/cvpr/2025/wu2025cvpr-moviebench/) — useful diagnostic frameworks; automated/short-video metrics do not establish story quality.

### Independent and historical evidence

- [Kinoautomat historical analysis](https://www.screeningthepast.com/issue-37-first-release/interactive-cinema-from-vending-machine-to-database-narrative-the-case-of-kinoautomat/) — scholarly historical analysis; limited surviving audience data.
- [Wired: Bandersnatch production](https://www.wired.com/story/bandersnatch-black-mirror-episode-explained/) and [Branch Manager](https://www.wired.com/story/black-mirror-bandersnatch-interactive-episode/) — detailed creator/tool reporting; not cost or demand data.
- [Streaming Media: interactive delivery](https://www.streamingmedia.com/Articles/Editorial/Featured-Articles/Streaming-Sites-Crunch-the-Numbers-on-Interactive-Video-132556.aspx) — engineering interviews; 2019 platform conditions.
- [The Verge/Yahoo: Netflix removals](https://www.yahoo.com/entertainment/netflix-pulling-interactive-titles-platform-105138599.html) and [Variety/Yahoo: final removals](https://www.yahoo.com/entertainment/articles/black-mirror-bandersnatch-getting-pulled-125444046.html) — status and company quotation; no internal causal postmortem.
- [Game Developer: Rival Peak AI](https://www.gamedeveloper.com/programming/the-a-i-behind-unique-interactive-reality-tv-game-i-rival-peak-i-) and [operational retrospective](https://www.gamedeveloper.com/business/the-real-time-evolution-of-i-rival-peak-i-) — direct practitioner accounts hosted by a trade publication; engagement remains operator-reported.

### Cross-cutting limitations

- Product pages can change after this access date and often omit failures.
- Many real-time model examples are selected demonstrations, not random samples.
- Frame-rate claims use named high-end hardware but rarely report cold start, concurrency,
  moderation, validation, egress, or end-to-end client latency.
- No provider was called, so price, quotas, regional behavior, and failure modes remain
  unverified for this project.
- No source supplies the anchor's joint outcome. Evidence from separate systems cannot be
  multiplied into a production-readiness claim.
- Public adoption figures lack common definitions and denominators. Waitlists, views,
  viewer-minutes, accounts, generated clips, paying users, and retained viewers are not
  interchangeable.
- Legal and labor questions are deliberately outside this file's conclusion. Unauthorized
  demonstrations are precedents for technical assembly, not evidence of rights-safe use.
