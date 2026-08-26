# Economics, Latency, Distribution, and Operations

Status: decision research; estimates are scenarios, not forecasts  
Price and source access date: 2026-08-25  
Currency: public USD list prices, excluding tax and negotiated discounts  
Scope: the 10–12 minute fictional-adult anchor in `00-research-plan.md`

## Reading key

- **Fact** means directly supported by the cited source in its stated scope and date.
- **Inference** means a reasoned consequence of facts and explicit assumptions.
- **Hypothesis** means falsifiable but not demonstrated.
- **Proposal** means an operating or product recommendation.

Prices, quotas, models, regions, and policies change. Recheck every provider page and contract
before procurement or budgeting. Public list price does not provide an SLA, capacity guarantee,
commercial-use clearance, indemnity, data-protection commitment, or predictable output quality.

## Executive conclusion

**Inference — economics.** Continuously generating every second of a unique 12-minute film is
not a plausible mass-consumer unit-economics baseline at current public API prices. Illustrative
video-generation cost alone ranges from about **$45 to $1,620 per completed session** under the
explicit low/base/high assumptions below, before story models, moderation, validation, music,
support, payment/platform fees, tax, failed jobs beyond the retry factor, and fixed operations.

**Inference — latency.** Current video APIs are asynchronous. Official documentation describes
single renders taking around 90 seconds or several minutes; that is incompatible with a 30-second
p95 consequence target if the next required segment begins only after the viewer acts. The viable
prototype is therefore a rolling-horizon hybrid: play authored/cached segments, decide at bounded
windows, prefetch multiple safe futures, and generate only a small number of transitions or
branch-specific moments.

**Proposal — product posture.** Start as a private web research experience. Do not launch an
“unlimited” consumer subscription. Cap each session's generated candidate seconds and dollars,
reserve spend before jobs, expose graceful fallbacks, and measure cost per delivered viewer-minute.
Consider Steam only after guardrails and live-AI cost collection are proven. Mobile stores and
public export add moderation, payment, age-rating, and disclosure obligations.

## Public price and capability anchors

These are comparable billing anchors, not a provider ranking. Models differ in resolution,
duration, audio, controls, policy, consistency, availability, and quality.

| Service/model | Public fact as of access date | Economic/operational implication |
|---|---|---|
| Runway API `gen4_turbo` | 5 credits per output second; credits cost $0.01, or **$0.05/s** | low price anchor; audio and retry/selection work are not established by price |
| Runway API `gen4.5` | 12 credits per output second, or **$0.12/s** | base visual price anchor |
| Runway API Veo 3.1 | 20 credits/s without audio and 40 credits/s with audio, or **$0.20/$0.40 per s** | provider routing changes price and feature scope |
| Google Vertex AI Veo 3 | **$0.50/s** video, **$0.75/s** video plus synchronized audio | high public direct-service anchor |
| OpenAI Sora 2 | **$0.10/s** at 720p with synchronized audio; Sora 2 Pro **$0.30/s**; model page marks Sora 2 legacy | useful comparison, but not a durable procurement assumption |
| Google Cloud Chirp 3 HD TTS | **$30 per 1 million characters** | speech cost is small beside video, but voice rights and quality remain separate |
| Cloudflare Stream | **$5 per 1,000 stored minutes** and **$1 per 1,000 delivered minutes** | delivery is small beside bespoke generation; storage multiplies with branches |

Sources: [Runway API pricing](https://docs.dev.runwayml.com/guides/pricing/),
[Vertex AI generative-media pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing),
[OpenAI Sora 2 model page](https://developers.openai.com/api/docs/models/sora-2),
[Google Cloud Text-to-Speech pricing](https://cloud.google.com/text-to-speech/pricing), and
[Cloudflare Stream pricing](https://developers.cloudflare.com/stream/pricing/) (all accessed
2026-08-25).

**Fact — price boundaries.** The quoted video rates bill generated output seconds, not
accepted or viewed seconds. Runway states generation credits are charged by model; Google
lists Veo by generated output second; Sora lists video generation per second. **Inference.**
Rejected, unusable, policy-blocked-after-generation, continuity-failing, and speculative
prefetch clips still consume generation budget unless a contract explicitly says otherwise.

## Latency and throughput evidence

- **Fact.** OpenAI documents Sora generation as an asynchronous job and says a single render
  may take several minutes depending on model, API load, and resolution. Source:
  [OpenAI video-generation guide](https://developers.openai.com/api/docs/guides/video-generation)
  (accessed 2026-08-25).
- **Fact.** AWS documents that Nova Reel generation typically takes about 90 seconds for a
  six-second video and approximately 14–17 minutes for a two-minute video. Source:
  [Amazon Nova Reel access and usage](https://docs.aws.amazon.com/nova/latest/userguide/video-gen-access.html)
  (accessed 2026-08-25).
- **Fact.** Google explains that one Veo 3 provisioned-throughput unit can generate a four-
  second video within a few minutes, while quota enforcement windows are separate from request
  latency. Source: [Vertex AI provisioned throughput for Veo](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/provisioned-throughput/veo-models)
  (accessed 2026-08-25).
- **Fact.** Runway's public usage tiers impose per-model, per-organization concurrency and
  monthly credit-purchase limits; higher/guaranteed concurrency requires an exception request.
  Source: [Runway API usage tiers](https://docs.dev.runwayml.com/usage/tiers/)
  (accessed 2026-08-25).
- **Evidence gap.** No representative public p95 end-to-end latency, queue-time SLA, accepted-
  output rate, continuity-pass rate, or guaranteed anchor concurrency was found for the exact
  workload. Marketing examples cannot fill this gap.

**Inference.** A request-at-choice/render-next-shot design fails the anchor's proposed p95
30-second consequence latency before download, moderation, assembly, and playback startup.
Parallel speculation can hide latency but multiplies spend by the number of candidate futures.

**Proposal — latency architecture.** Maintain a safe playable horizon of at least two segments:

1. play the committed segment;
2. precompute likely bounded intents and render/cache one or more next segments;
3. acknowledge a choice immediately and map it to the closest governed branch;
4. use an authored bridge, game-engine shot, dialogue/audio modification, or cached branch
   while slower audiovisual work completes;
5. never stall waiting for a provider; degrade visibly to a safe authored path;
6. record whether the consequence was generated, cached, mapped, or fallback.

This preserves playback but limits literal freedom. Product language must say “your choices
shape the story,” not “every frame is generated instantly for you,” unless measured evidence
later supports that claim.

## Unit-economics model

### Formula and cost boundary

For one session:

```text
candidate_video_seconds = newly_generated_final_seconds × generation_multiplier
video_cost = candidate_video_seconds × provider_price_per_output_second
tts_cost = billable_dialogue_characters × tts_price_per_character
delivery_cost = watched_minutes × delivery_price_per_minute

variable_session_cost = video_cost + tts_cost + delivery_cost
                      + story + moderation + validation + music + storage delta
                      + orchestration + support/refunds + payment/platform charges
```

The quantified table includes only video, an explicit TTS allowance when video audio is not
included, and delivery. All other terms are **unknown/excluded**, not zero.

### Shared assumptions

- **Hypothesis.** Anchor duration is 12 minutes/720 delivered seconds.
- **Hypothesis.** Dialogue averages 90 spoken words per minute; 1,080 words/session; six
  characters including spaces/punctuation per word; therefore 6,480 TTS characters. At
  $30/M characters, this is **$0.1944/session** before free tiers. This is an explicit planning
  approximation, not measured script data.
- **Fact applied to assumption.** Cloudflare delivery for 12 watched minutes at $1/1,000
  minutes is **$0.012/session**. Storage depends on how many generated branches are retained.
- **Hypothesis.** Generation multiplier covers alternate candidates, rejected continuity/
  policy outputs, and retries. It is 1.25× low, 2× base, and 3× high. Provider failure fees and
  refunds must be measured; no assumption is made that failed jobs are free.
- **Boundary.** Taxes, discounts, story/intent LLM, moderation, embedding/search, music and
  sound effects, transcoding outside the cited delivery service, database, observability,
  support, refunds, fraud, platform/payment fees, staff, legal, and fixed production are excluded.

### Scenario A: hybrid rolling horizon

The reuse percentage means the delivered segment is authored, previously generated and
approved, cached across sessions, or rendered locally without the cited video API. “New video”
is unique video generated for this session.

| Case | Explicit assumptions | Arithmetic | Quantified variable floor/session |
|---|---|---|---:|
| Low | 95% reused; 36 s new; 1.25×; Runway `gen4_turbo` $0.05/s; separate Chirp TTS | 36 × 1.25 × .05 + .1944 + .012 | **$2.46** |
| Base | 85% reused; 108 s new; 2×; Runway `gen4.5` $0.12/s; separate Chirp TTS | 108 × 2 × .12 + .1944 + .012 | **$26.13** |
| High | 70% reused; 216 s new; 3×; Vertex Veo 3 video+audio $0.75/s; no separate TTS | 216 × 3 × .75 + .012 | **$486.01** |

**Inference.** Only the low hybrid case is even near ordinary paid-entertainment economics,
and it still excludes several variable and all fixed costs. The base and high cases require
premium pricing, a heavily subsidized demonstration, enterprise/installation economics, or
much greater reuse and provider discounts.

### Scenario B: every delivered second generated uniquely

| Case | Explicit assumptions | Arithmetic | Quantified variable floor/session |
|---|---|---|---:|
| Low | 720 s; 1.25×; $0.05/s; separate TTS | 720 × 1.25 × .05 + .1944 + .012 | **$45.21** |
| Base | 720 s; 2×; $0.12/s; separate TTS | 720 × 2 × .12 + .1944 + .012 | **$173.01** |
| High | 720 s; 3×; $0.75/s with audio | 720 × 3 × .75 + .012 | **$1,620.01** |

**Inference.** Fully unique generation is unsuitable as the default consumer experience at
these list prices. This conclusion does not depend on small story-model or CDN optimizations;
video generation dominates by orders of magnitude.

### Sensitivities that matter

| Variable | Why it dominates | Measurement required |
|---|---|---|
| newly generated final seconds | linear first-order driver | generated vs reused seconds per accepted intervention |
| candidate multiplier | speculative branches and quality failures multiply cost | candidates started, completed, rejected, accepted, abandoned |
| cache hit/reuse | converts per-session generation into amortized library cost | hit rate by segment, intent, locale, and cohort |
| provider price/model routing | 15× spread between $0.05 and $0.75 anchors | realized price recorded per job |
| consequence window | shorter target forces more speculative prefetch | spend vs measured perceived agency |
| branch amplification | retaining unused futures grows storage and moderation | new retained artifacts per accepted intervention |
| locale count | voice, text, moderation, and QA multiply; visual reuse may not | marginal cost and parity pass rate per locale |
| public sharing | creates replay traffic, moderation, support, and claims operations | cost per public view, report, appeal, and takedown |

**Proposal.** Cost telemetry must be ledger based, not invoice based. Attach provider, model,
price version, requested/realized seconds, attempts, outcome, rejection reason, selected artifact,
cache state, user/session/tenant, and reserved/released spend to every job. The invoice arrives
too late to stop an abuse burst.

## Business-model implications

### Viable early forms

1. **Research installation or festival experience.** Small concurrency, scheduled sessions,
   high-touch operations, and an explicit experience budget. Useful for value evidence, not
   proof of consumer scale.
2. **Premium creator-authored title.** Most content is authored/cached; paid session credits
   purchase a bounded number of generated deviations. The creative proposition, not unlimited
   compute, is the product.
3. **Enterprise creative tool.** Users wait for branch renders and pay production-tool prices.
   This is economically and operationally different from a live viewer experience.
4. **Game-engine hybrid.** Real-time visuals come from controlled engine assets; generation
   changes narrative, dialogue, blocking, or cinematography. This may have better variable
   economics but requires separate quality and architecture research.

### Models to reject initially

- **Proposal.** No unlimited generation subscription until measured p99 spend, concurrency,
  abuse, and fallback make the maximum liability bounded.
- **Proposal.** No ad-supported model for the anchor. Ad yield is unlikely to cover even the
  low quantified floor without extreme reuse, while personalized advertising adds privacy and
  child-safety complexity.
- **Proposal.** Do not sell tokenized ownership or universal copyright in branches. Rights and
  protectability are mixed and jurisdiction-specific.
- **Proposal.** Do not price per failed prompt. Charge for understandable experience budgets
  or included interventions, and absorb bounded technical failures; otherwise users bear model
  unreliability they cannot control.

### Contribution-margin gate

**Proposal.** Before a paid pilot, define:

```text
net_session_revenue
- generation, moderation, validation, TTS/music, storage, and delivery
- payment and platform charges
- expected fraud, refunds, support, and incident cost
= contribution_margin
```

Require positive contribution in the measured p75 session and a hard maximum loss per session.
Do not average a small group of runaway sessions into invisibility. A paid pilot must show the
distribution of spend per accepted intervention and per delivered minute.

## Distribution constraints

### Web/private link — recommended prototype channel

**Inference.** A private web experience offers the most control over release cadence,
experiment access, provider failover, disclosure, and payment design. It does not remove GDPR,
consumer, copyright, accessibility, age, or hosting duties. It only avoids app-store review as
the first dependency.

**Proposal.** Begin invite-only with no indexable/public branches, no anonymous use, no user
uploads, an adult-only declared audience, explicit AI disclosure, accessible player, and
session budget shown before generation. Treat URLs as access capabilities: short-lived,
revocable, audience bound, and non-enumerable.

### Steam

- **Fact.** Steam's Content Survey requires detailed disclosure of AI content. For
  live-generated AI, developers must describe guardrails intended to prevent illegal output.
  Steam also says external live-AI service costs and payment collection must be managed through
  Steam-supported methods; it lists game-price inclusion, microtransactions, subscriptions,
  and DLC as possible structures. Source:
  [Steamworks Content Survey](https://partner.steamgames.com/doc/gettingstarted/contentsurvey)
  (accessed 2026-08-25).
- **Fact.** The same Steam page says live-generated Adult Only Sexual Content is not shipped.
- **Inference.** Steam is a plausible paid distribution path for a governed game-like title,
  but the store submission requires a stable guardrail design and monetization envelope before
  review. A prototype that changes providers or safety boundaries after approval needs a survey
  change process with Steam Support.

### Apple App Store

- **Fact.** Apple's App Review Guideline 1.2 requires UGC apps to filter objectionable
  material, support reporting and timely responses, allow blocking abusive users, and publish
  contact information. Creator content is treated as UGC. Apple also requires accurate age
  ratings and rights for app materials. Source:
  [Apple App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
  (accessed 2026-08-25).
- **Inference.** A private, non-shared generated session may not trigger every UGC provision,
  but public branch sharing/remixing plainly increases review risk. Seek pre-submission advice
  rather than designing around a narrow label.

### Google Play

- **Fact.** Google Play's AI-Generated Content policy covers apps generating text, image,
  voice, or video and requires prevention of prohibited content. Covered apps must contain an
  in-app reporting/flagging feature and use reports to inform filtering and moderation. Source:
  [Google Play AI-generated content policy](https://support.google.com/googleplay/android-developer/answer/13985936?hl=en-GB)
  (accessed 2026-08-25).
- **Fact.** Google Play also uses asset-level self-declaration for AI-generated store assets
  under specified circumstances. Source:
  [Google Play AI content declaration](https://support.google.com/googleplay/android-developer/answer/17262077?hl=en)
  (accessed 2026-08-25).
- **Inference.** A provider filter alone cannot satisfy the product's reporting and moderation
  operations. Mobile launch requires staffed handling, telemetry, and policy iteration.

### Video export and YouTube

- **Fact.** YouTube requires disclosure when meaningfully altered or synthetic content seems
  realistic, including a realistic scene that did not occur, and may penalize repeated
  nondisclosure. Disclosure alone does not authorize another person's likeness. Sources:
  [YouTube altered-content disclosure](https://support.google.com/youtube/answer/14328491?hl=en)
  and [YouTube likeness claims](https://support.google.com/youtube/answer/17133929)
  (accessed 2026-08-25).
- **Inference.** Export should carry a visible disclosure and C2PA credentials when supported,
  plus a plain-language reminder that the user must follow destination-platform rules. The
  project remains responsible for its own authorization and must not imply that a label cures
  likeness or copyright problems.

### Ratings and territory

**Inference.** Dynamic output weakens the usual assumption that all shipped audiovisual
content was classified before release. The project constitution must cap the rating, and
generated output must be tested against the rating questionnaire and territory rules. “The
model should avoid mature content” is not a rating control. Confirm IARC/ESRB/PEGI/USK and
national audiovisual obligations with each distributor before release; this research does not
assert one universal classification route.

## Reliability and operating model

### Session SLO and budget contract

**Proposal.** A prototype session has two independent budgets:

- **playback budget:** p95 stall below 1 second; no stall above 3 seconds; immediate
  acknowledgement; consequence through generated, cached, or disclosed fallback within the
  research target; and
- **spend budget:** maximum generated candidate seconds, attempts per segment, concurrent jobs,
  provider dollars, retained speculative seconds, and session wall time.

Exhausting spend must choose an authored/cached ending, not generate on an unmetered path.
Exhausting the playable horizon must pause at an intentional decision or recap experience,
not display a spinner over silence.

### Failure policy

| Failure | User behavior | State/economic behavior |
|---|---|---|
| provider queue exceeds deadline | play cached/authored compatible branch and disclose adaptation | cancel where possible; never commit pending branch; record incurred cost |
| candidate fails safety/rights/continuity | do not play; offer safe mapped choice or fallback | bounded retry; no story advance; retain minimum incident receipt |
| provider outage/rate limit | circuit break provider; use compatible cached path | stop new reservations; no retry storm |
| assembly/caption/audio mismatch | block artifact; use prior approved branch | retry only failed stage if rights/state identity remains intact |
| client disconnect | stop speculative work after grace period | release reservation; retain only committed artifacts per policy |
| budget exhausted | finish via declared authored path | zero further paid jobs |
| manifest/signing failure | do not export/publish; private playback only if policy permits | quarantine artifact until provenance repaired |

### Capacity planning

**Proposal.** Size from generated jobs, not active viewers:

```text
required_concurrency ~= active_sessions
                     × interventions_per_minute
                     × candidates_per_intervention
                     × mean_job_minutes
```

This is a queueing approximation, not a capacity guarantee. A several-minute mean job causes
concurrency to accumulate even at modest arrival rates. Obtain provider-specific quota and
burst commitments in writing, then load test with the exact model, resolution, duration,
region, references, moderation, and webhook path.

### Observability and reconciliation

**Proposal.** Track by provider/model/version, region, locale, story, and cache state:

- queue, generation, download, moderation, assembly, signing, and startup latency percentiles;
- requested, completed, failed, canceled, rejected, selected, played, and abandoned seconds;
- provider cost, reserved cost, released reservation, cache amortization, storage, and delivery;
- safe-fallback and hidden-wait attempts; playable-horizon depth and near-stall events;
- policy/rights/continuity/accessibility rejection reason and human appeal outcome;
- output-quality acceptance and identity/canon error per delivered minute;
- provider invoice reconciliation against the internal immutable cost ledger.

Never label a session successful merely because playback continued. Report generated response,
mapped cached branch, authored fallback, and ignored/rejected intervention separately.

### Provider procurement checklist

**Proposal.** Before using a provider in a live trial, record:

- exact model/version lifecycle and deprecation notice;
- p50/p95/p99 latency and capacity for the contracted region, or mark them unguaranteed;
- rate/concurrency/quota and exception process;
- failed/canceled/moderated job billing and refund rules;
- input/output retention, training use, subprocessors, region, transfer and deletion behavior;
- commercial-use/output terms, warranties, indemnity scope/exclusions, and claim process;
- safety policy, configurable controls, audit logs, model-change notice, and incident notice;
- content credentials/watermark behavior and whether transformations strip it;
- support SLO, outage communication, export continuity, and termination/deprecation assistance.

Public pricing pages answer only a fraction of this checklist.

## Prototype economic experiment

**Proposal.** Fix a maximum external generation budget before implementation. A meaningful
economic test uses at least 30 completed anchor sessions across cold/warm cache states and
adversarial/benign choices, while retaining every job and cost receipt. Suggested research
gates—not product forecasts—are:

- median newly generated final video no more than 60 seconds/session;
- p95 generation multiplier no more than 1.5× accepted new seconds;
- median quantified provider variable floor no more than $5/session and p95 no more than $10;
- zero session exceeds the hard predeclared dollar cap;
- at least 80% of accepted interventions produce independently rated material consequence;
- safe fallback is visible and measured; its rate remains below the user-study rejection
  threshold set before testing;
- p95 playback stall and consequence latency meet the anchor targets without misclassifying
  a cached generic branch as generated responsiveness.

**Hypothesis E-1.** With at least 90% reuse, bounded natural-language intent, and generated
transitions rather than continuous video, the anchor can keep the quantified provider floor
under $5/session at acceptable agency. This is the central economic hypothesis to falsify.

**Kill condition.** After one corrective iteration, block this architecture if the p95 cost cap
is exceeded, provider latency forces hidden waiting, or meeting cost/latency requires so much
fallback that the agency study fails. Test a game-engine or discrete branching model before
rejecting the broader interactive-cinema thesis.

## Claims to carry into the package ledger

| ID | Claim | Class | Confidence | Validation still needed |
|---|---|---|---|---|
| EDO-01 | Public video API list prices span at least $0.05–$0.75 per generated output second across cited anchors | Fact | high | contract and price refresh at procurement |
| EDO-02 | Current cited APIs cannot be assumed to meet a 30-second p95 next-segment render target | Fact + inference | high | live exact-workload benchmark and contract SLA |
| EDO-03 | Fully unique 12-minute generation has a $45–$1,620 quantified video/TTS/delivery floor under stated scenarios | Scenario inference | high arithmetic; medium assumptions | measured candidate multiplier and script profile |
| EDO-04 | A rolling-horizon hybrid is the viable prototype shape | Inference | medium-high | agency, latency, continuity, and cache study |
| EDO-05 | At least 90% reuse can keep the quantified provider floor under $5/session without negating agency | Hypothesis | low-medium | 30+ retained live sessions |
| EDO-06 | Public sharing and app-store distribution materially expand moderation and operations | Fact + inference | high | platform pre-review and staffed pilot |

## Evidence score and blockers

**Inference — current score: 1/3 (plausible only)** for unit economics/distribution and 1/3
for latency/operations. Public prices, async behavior, and platform rules establish strong
constraints, but no live job, invoice, cache trace, load test, user study, platform review,
provider contract, or operational drill was performed.

The next decision is blocked on:

1. one exact provider/model/region/resolution and contracted terms;
2. live p50/p95/p99 queue-to-playable benchmarks at representative concurrency;
3. observed generation multiplier and acceptance rate, including billed rejected work;
4. agency-versus-reuse evidence for the 90% reuse hypothesis;
5. complete variable-cost ledger, including moderation, validation, music/audio, and support;
6. provider capacity/deprecation and data/rights commitments;
7. chosen distribution path and platform pre-review;
8. a fixed session cost cap, fallback policy, pilot budget, and stop date.

