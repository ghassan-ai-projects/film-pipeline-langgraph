# Claims and Evidence Ledger

Evidence cutoff: 2026-08-25  
Purpose: prevent facts, vendor claims, inferences, and proposals from collapsing into one
product-readiness story.

Confidence refers to the narrow claim as written, not to the whole idea. Repository evidence
comes from the dirty snapshot disclosed in `05-repository-adaptation.md` and must be refreshed
after those source changes settle.

| ID | Material claim | Class | Evidence | Confidence | Counterevidence / limitation | Validation still needed | Decision effect |
|---|---|---|---|---|---|---|---|
| C-001 | Interactive audiovisual stories have shipped at global scale. | Fact | Netflix launch and production evidence in `02-landscape-and-evidence.md` | High | Shipped branching is not generation or proof of durable demand. | None for historical fact; demand study for product inference. | Interactivity is not the speculative component. |
| C-002 | Netflix retired its dedicated interactive-special catalog, but public evidence does not establish why. | Fact | Netflix spokesperson and removal reporting in `02-landscape-and-evidence.md` | High | No title-level cost, retention, or postmortem. | Internal data unavailable; use as warning, not causal proof. | Product must beat simpler substitutes and measure authoring burden. |
| C-003 | Prefetching multiple future segments can hide branch-switch latency. | Fact | Bandersnatch delivery accounts; linked in `02-landscape-and-evidence.md` | Medium-high | Client buffer and branch count bound the technique; generated candidates add cost/failure. | Prototype p95 buffer, cache, and fallback receipts. | Supports rolling-horizon architecture. |
| C-004 | Deterministic simulation, character planning, cloud rendering, audience input, and video delivery can operate together. | Fact | Rival Peak technical/operator/AWS accounts in `02-landscape-and-evidence.md` | Medium-high | One shared world amortized compute; not per-viewer film; figures are operator/vendor supplied. | Per-viewer load/cost and individual-agency tests. | Supports game-engine/hybrid alternative. |
| C-005 | Current world models demonstrate real-time action-conditioned video for minute-scale horizons. | Fact, first-party/research scope | Genie 3, GameNGen, LongLive and related sources in `02-landscape-and-evidence.md` | Medium-high | Curated demonstrations, specialized hardware, limited agents/actions/duration; not an entertainment SLA. | Independent live benchmark with full pipeline latency. | Fully neural media is credible research, not product proof. |
| C-006 | Current production video APIs are primarily short-clip, asynchronous systems whose documented job latency can be much longer than the anchor consequence budget. | Fact | Runway, Veo, Sora, Nova official docs in `02` and `08` | High for documented interfaces | Providers evolve quickly; enterprise/custom paths may differ. | Live p50/p95/p99 by model, region, concurrency, cache, quality, and moderation. | Request-after-choice/render-next cannot be the only path. |
| C-007 | No public system found satisfies the anchor's story, multi-character media, latency, safety, replay, creator, and economic requirements jointly. | Evidence-bounded fact | Anchor-normalized survey in `02-landscape-and-evidence.md` | Medium-high | Absence from public evidence is not proof no private system exists. | Vendor discussions and hands-on benchmark if authorized. | Caps conclusion at bounded prototype. |
| C-008 | Fully unique 12-minute generation has an illustrative video/TTS/delivery floor of about $45–$1,620 per completed session under the stated scenarios. | Inference from public prices | Formula and low/base/high assumptions in `08-economics-distribution-and-operations.md` | Medium | Excludes many costs; accepted-output rate unknown; prices will change; not a quote. | Real job ledger including rejected, cancelled, speculative, storage, support, and fixed cost. | Reject fully unique consumer baseline today. |
| C-009 | A 70–95% reuse hybrid has an illustrative quantified floor of about $2.46–$486 per session; only the low case approaches consumer entertainment economics. | Inference from public prices | Formula and assumptions in `08-economics-distribution-and-operations.md` | Medium | 95% reuse may weaken agency; excluded costs remain; price is not willingness to pay. | Measure reuse versus agency, candidate multiplier, cache hits, full contribution margin. | Makes hybrid conditional, not automatically viable. |
| C-010 | The repository has useful authoring-plane contracts but no behavior-proven interactive viewer runtime. | Fact about inspected snapshot | Code/test matrix and 159 focused passing tests in `05-repository-adaptation.md` | High for inspected snapshot | Dirty tree; full CI/live/playback/load/security not run. | Refresh audit and run targeted integration/load/provider evidence after changes settle. | Preserve current pipeline; add an isolated seam. |
| C-011 | Current film constitution, bibles, artifacts, validators, provider jobs, MCP boundary, and checkpoints are reusable inputs/patterns. | Fact + inference | Symbols/tests in `05-repository-adaptation.md` | High for existence; medium for reuse design | Prose invariants are not machine-enforced; Git/artifact files are wrong for hot session state. | Story compiler and compatibility tests. | Reduces prototype scope but does not prove live behavior. |
| C-012 | The current phase graph, project state, filesystem artifacts, and Git branches should not be used per viewer. | Architecture inference | Granularity/concurrency audit in `05-repository-adaptation.md` | High | A very small single-user demo could technically reuse them, creating future coupling. | Isolated spike comparison and regression suite. | Add event-sourced/CAS session runtime. |
| C-013 | Typed story state and consequence contracts can preserve causality better than unconstrained continuation. | Hypothesis | Narrative model in `03-narrative-and-creator-systems.md`; Façade precedent | Medium-low until tested | Constraints may cause high rejection, rigidity, or false choice. | Text simulation plus blinded comparison to free-form and branch controls. | First prototype question. |
| C-014 | Exact replay across provider regeneration is not a defensible guarantee; exact delivered replay is possible by retaining immutable artifacts and manifests. | Inference/proposal | Provider stochasticity/deprecation plus repository artifact design | High | Retention cost, takedown, deletion, and rights expiry complicate availability. | Hash/redelivery, deletion-policy, provider-retirement, and incident-hold tests. | Define replay as retained-media replay. |
| C-015 | A rights-clean fictional-adult private anchor is materially safer than likeness/upload/minor/public-sharing variants. | Inference | `07-safety-rights-and-governance.md` authoritative baseline and threat model | High | “Safer” is not “safe”; fictional assets still need chain of title and output review. | Rights ledger, red team, counsel, provider contract, incident exercises. | Keep exclusions as hard prototype boundary. |
| C-016 | Provider output terms cannot grant rights the project does not have in people, performances, characters, music, or references. | Legal/rights inference | Copyright Office, statutes, SAG-AFTRA and contract-risk analysis in `07` | High as risk principle | Exact legal outcome is jurisdiction- and contract-specific. | Qualified counsel and complete chain of title. | Rights gate before generation/publication. |
| C-017 | C2PA provenance and visible disclosure improve traceability but do not prove truth, consent, safety, or non-infringement. | Fact + inference | C2PA 2.4 principles and harms analysis; EU AI Act Article 50 in `07` | High | Adoption and preservation across platforms vary. | Signed-manifest implementation and platform export test. | Use provenance alongside, not instead of, rights/safety receipts. |
| C-018 | Accessibility/localization tracks must be version-matched to each playable segment. | Systems inference | Branch semantics and requirements in `09-accessibility-localization-and-measurement.md` | High | Implementation and user parity are unproven. | Disabled-user and bilingual/cultural evaluation; fallback scenarios. | Missing/stale access track blocks dynamic segment. |
| C-019 | Meaningful agency, story quality, and demand cannot be established by model-as-judge or engagement metrics alone. | Fact-supported methodology inference | TACL story-evaluation limits and measurement design in `09`; landscape evidence gaps | High | Models can still help screen structural defects. | Preregistered, blinded human comparison with inter-rater agreement. | Human evidence is a product gate. |
| C-020 | A rolling-horizon hybrid is the strongest current architecture candidate for the anchor. | Proposal | Synthesis of C-003 through C-019 | Medium | Could lose to pre-rendered branching on value, complexity, or cost; game engine may outperform. | Staged controls and kill criteria in `06-prototype-and-validation-roadmap.md`. | Recommend bounded experiment only. |
| C-021 | The first implementation should be story compiler + deterministic text session loop, not live media. | Proposal | Cheapest falsification path in `03`–`06` | High | Text experience may underpredict audiovisual value or defects. | Stage 0/1 tests, then storyboard and media gates separately. | Minimizes sunk cost and repository risk. |
| C-022 | Desk research supports position 3 only as a bounded, gated prototype; it cannot support product investment. | Decision inference | Plan rubric plus all workstreams | Medium-high | Viewer value and creator burden remain completely unmeasured; position 2 remains defensible. | Independent reviews; then story-state prototype authorization. | Final recommendation. |

## Decision rubric score

The score reflects current evidence, where `1` means plausible/source-backed rationale or mock
proof only. No dimension has representative product evidence.

| Dimension | Score 0–3 | Basis | Blocking next evidence |
|---|---:|---|---|
| Viewer value and agency | 1 | Precedents and clear falsifiable thesis | Controlled comparison with target viewers |
| Narrative quality | 1 | Drama-manager precedent and explicit model | Complete-branch expert/human evaluation |
| Creator value and control | 1 | Existing bibles/review concepts and proposed workflow | Creator task study and authoring-hour ledger |
| Audiovisual continuity | 1 | Short-clip/world-model evidence; existing linear validators | Live multi-character anchor samples and human review |
| Latency and fallback | 1 | Prefetch precedent and candidate design | End-to-end p50/p95/p99 live receipts |
| Safety and rights | 1 | Tractable excluded-risk anchor and proposed controls | Red team, rights ledger, provider terms, qualified review |
| Security and privacy | 1 | Defined trust boundaries and bounded data posture | Threat-model verification, auth/isolation/load tests, DPIA assessment |
| Accessibility/localization | 1 | Explicit equivalent-path design | Participant evaluation and synchronized-track tests |
| Replay/auditability | 1 | Existing artifact patterns and proposed event/manifests | Exact recovery/redelivery and deletion/revocation tests |
| Technical integration | 1 | Audited additive seam and reusable contracts | Stage 0/1 implementation without linear-path regressions |
| Reliability/operations | 1 | Failure semantics and existing job/checkpoint patterns | Concurrency, queue, recovery, incident, and provider tests |
| Unit economics/distribution | 1 | Public price model exposes viable and non-viable envelopes | Full-cost live ledger, willingness to pay, platform review |

No non-compensable gate is known to be impossible. Every gate is also unproven. Under the plan's
rubric this permits, but does not compel, a **position 3 bounded prototype**. A conservative
decision-maker could remain at position 2 until a title owner and prototype cost ceiling exist.

## Revalidation triggers

Revalidate the affected claims when:

- provider model, price, duration, quota, policy, terms, or retention changes;
- repository source changes in graph, MCP, artifacts, providers, validation, or checkpoints
  settle;
- the anchor title, audience, territory, interaction grammar, device, runtime, or sharing model
  changes;
- real people, uploads, minors, public UGC, multiplayer, biometric/passive adaptation, or a new
  locale enters scope;
- a live provider, creator, viewer, safety, accessibility, or load experiment produces receipts.
