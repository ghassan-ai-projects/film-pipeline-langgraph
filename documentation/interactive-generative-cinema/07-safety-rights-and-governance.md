# Safety, Rights, Privacy, Accessibility, and Governance

Status: decision research; not legal advice  
Source access date: 2026-08-25  
Scope: the 10–12 minute, fictional-adult anchor in `00-research-plan.md`, plus the risks
created by later likeness, upload, sharing, localization, and minor-user extensions

## Reading key and legal boundary

- **Fact** means a claim directly supported by the cited source in its stated jurisdiction.
- **Inference** means a conclusion drawn from named facts; it still needs prototype evidence.
- **Hypothesis** means a falsifiable proposition that has not been demonstrated.
- **Proposal** means a design or operating recommendation.

This is an engineering risk analysis, not legal advice. Copyright, publicity, biometric,
labor, child-safety, privacy, consumer-protection, platform, and accessibility obligations
vary by territory and facts. Qualified counsel must approve target territories, chain of
title, performer/voice agreements, vendor terms, user terms, privacy notices, age posture,
takedown process, retention schedule, and launch claims before external release.

## Executive conclusion

**Inference — position impact.** The anchor can plausibly be researched safely only because
it excludes minors, real-person likenesses, public publishing, passive emotion inference,
unrestricted prompts, and user-uploaded copyrighted characters. Those exclusions are not
temporary implementation shortcuts. They are the boundary that keeps a prototype tractable.

**Proposal.** Authorize only a closed, adult, fictional-character prototype with a fully
documented rights ledger; bounded intent vocabulary; input and output enforcement; immutable
story-state commits; per-segment provenance; short-lived raw prompts; accessible choice and
playback controls; and no public sharing. A safety or rights rejection must not silently
advance story state. Expansion needs a new review, not a feature flag.

**Inference — principal blockers.** The hardest unresolved controls are not a text filter.
They are (1) reliable output review across image, motion, speech, sound, and narrative context;
(2) proof that every reference, character, voice, and musical element is authorized for each
use; (3) revocation and deletion without destroying audit integrity; (4) protection against
cross-tenant or provider leakage of high-value character/likeness assets; and (5) accessible,
policy-equivalent operation in every supported language.

## Authoritative baseline

### Synthetic-media transparency and provenance

- **Fact — EU.** Article 50 of the EU AI Act requires providers of systems that generate
  synthetic audio, image, video, or text to mark outputs in a machine-readable, detectable
  format. Deployers of systems producing deepfakes must disclose artificial generation or
  manipulation. For evidently artistic, creative, satirical, fictional, or analogous works,
  the disclosure may be made in an appropriate way that does not hamper enjoyment. Source:
  [Regulation (EU) 2024/1689, Article 50](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=en)
  (accessed 2026-08-25).
- **Fact — standard.** C2PA Content Credentials 2.4 represent signed provenance claims and
  content bindings; the specification supports embedded or external manifests. C2PA itself
  says provenance signals are not value judgments about whether content is good, bad, or
  true. Sources: [C2PA Content Credentials 2.4](https://spec.c2pa.org/specifications/specifications/2.4/specs/ContentCredentials.html)
  and [C2PA guiding principles](https://c2pa.org/principles/) (accessed 2026-08-25).
- **Fact — residual risk.** C2PA's own harms analysis warns that manifests can disclose
  sensitive information, prior redacted versions may remain discoverable through soft
  binding, and provenance infrastructure can be misused for surveillance. Source:
  [C2PA Harms Modelling 2.4](https://spec.c2pa.org/specifications/specifications/2.4/security/Harms_Modelling.html)
  (accessed 2026-08-25).
- **Inference.** A visible “AI-generated” label plus a C2PA manifest is necessary for the
  intended product, but neither proves factual truth, consent, non-infringement, or safety.
  Rights and moderation receipts must be separate assertions backed by internal evidence.

### Copyright, authorship, music, and user branches

- **Fact — United States.** The U.S. Copyright Office concludes that purely AI-generated
  material, or material with insufficient human control over expressive elements, is not
  copyrightable. Human-authored expression, creative selection/arrangement, and creative
  modifications can be protected case by case; prompts alone ordinarily do not provide
  sufficient control under the assessed technology. Source:
  [Copyright and Artificial Intelligence, Part 2: Copyrightability](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-2-Copyrightability-Report.pdf)
  (accessed 2026-08-25).
- **Fact — music.** A musical composition and a sound recording are distinct works and are
  commonly owned and licensed separately. Source:
  [U.S. Copyright Office, Musical Compositions and Sound Recordings](https://copyright.gov/circs/circ56a.pdf)
  (accessed 2026-08-25).
- **Inference.** The product must not promise that a viewer “owns their movie” without
  territory-specific analysis. The branch may contain studio-authored material, licensed
  assets, AI-generated material with uncertain protectability, and a user's limited creative
  contribution. Product copy should promise access/export rights defined by contract, not a
  universal copyright conclusion.
- **Proposal.** Preserve evidence of human authorship: story constitution, authored scene
  graph, accepted direction, edits, selections, arrangements, approvals, and final manifest.
  Do not manufacture a false authorship narrative; record what humans actually controlled.

### Likeness, voice, performers, and digital replicas

- **Fact — policy landscape.** The U.S. Copyright Office found existing U.S. protections for
  unauthorized digital replicas insufficient and recommended federal legislation covering
  realistic unauthorized replicas of all people; that recommendation is not itself enacted
  law. Source:
  [Copyright and Artificial Intelligence, Part 1: Digital Replicas](https://www.copyright.gov/ai/Copyright-and-Artificial-Intelligence-Part-1-Digital-Replicas-Report.pdf)
  (accessed 2026-08-25).
- **Fact — California examples.** California Labor Code provisions effective January 1,
  2025 address certain digital-replica contract terms, and California Civil Code provisions
  address digital replicas of deceased personalities. These are jurisdiction-specific, not a
  complete U.S. rule. Sources: [California Labor Code section 927](https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?article=&chapter=1.&division=2.&lawCode=LAB&part=3.&title=)
  and [California Civil Code section 3344.1](https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?article=3.&chapter=2.&division=4.&lawCode=CIV&part=1.&title=2.)
  (accessed 2026-08-25).
- **Fact — labor.** SAG-AFTRA's public 2026 TV/Theatrical summary says the agreement expands
  protections around no-scan replicas, alterations, foreign-language dubbing, biometric data,
  security, transfers, strike use, and minor replicas. Applicability depends on the production
  and agreement. Source: [SAG-AFTRA 2026 TV/Theatrical Contracts](https://www.sagaftra.org/contracts-industry-resources/contracts/2026-tvtheatrical-contracts)
  (accessed 2026-08-25).
- **Inference.** A vendor's permission to use generated output cannot grant rights in a real
  person's face, voice, performance, character, composition, master, trademark, or uploaded
  reference that the customer did not control.
- **Proposal.** Keep real people, celebrity prompts, voice clones, and deceased personalities
  out of the prototype. A later likeness program needs separate, conspicuous, per-purpose
  authorization; reasonably specific uses; media and character scope; territory; term;
  compensation; training/retraining permission; storage/security terms; transfer rules;
  dubbing/localization scope; revocation mechanics; and union/counsel review. Consent to scan
  is not consent to every future scene.

### Privacy, biometrics, children, and hosting

- **Fact — EU privacy.** GDPR requires lawful, fair, transparent, purpose-limited, and
  data-minimized processing; privacy by design/default and appropriate security; and a data
  protection impact assessment where processing is likely to create high risk. Biometric data
  used to uniquely identify a person is special-category data. Source:
  [Regulation (EU) 2016/679, Articles 5, 9, 25, 32, and 35](https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX%3A32016R0679)
  (accessed 2026-08-25).
- **Fact — U.S. children.** COPPA applies to covered child-directed services and services with
  actual knowledge they collect personal information from a child under 13. The 2025 amended
  rule added, among other changes, biometric identifiers to personal information and limits
  indefinite retention. Sources: [FTC COPPA rule page](https://www.ftc.gov/legal-library/browse/rules/childrens-online-privacy-protection-rule-coppa)
  and [2025 final amendments](https://www.ftc.gov/legal-library/browse/federal-register-notices/16-cfr-part-312-coppa-final-rule-amendments)
  (accessed 2026-08-25).
- **Fact — illegal child sexual-abuse material.** U.S. federal law imposes CyberTipline
  reporting duties on covered providers that obtain actual knowledge of qualifying apparent
  violations. Source: [18 U.S.C. § 2258A](https://uscode.house.gov/view.xhtml?edition=2023&num=0&req=granuleid%3AUSC-2023-title18-section2258A)
  (accessed 2026-08-25). Applicability and preservation duties require specialist counsel and
  a rehearsed process; staff should never improvise handling of suspected material.
- **Fact — hosted user content.** EU DSA Article 16 requires hosting services in scope to
  provide an accessible electronic notice-and-action mechanism for alleged illegal content.
  U.S. DMCA section 512 safe harbors are conditional, including designated-agent,
  notice-and-takedown, and other requirements. Sources:
  [Regulation (EU) 2022/2065](https://eur-lex.europa.eu/eli/reg/2022/2065/oj?locale=en)
  and [U.S. Copyright Office section 512 resources](https://www.copyright.gov/512/)
  (accessed 2026-08-25).
- **Inference.** Adding galleries, remixing, public links, or friend-likeness features changes
  the system from a private creation tool into a hosting and abuse-operations program. That
  change is materially larger than adding a share button.

## Rights ledger: minimum chain of title

**Proposal.** No asset may become a generation reference or a playable ingredient until a
machine-readable rights record passes validation. “The user checked a box” is not sufficient
proof for high-risk assets.

| Asset or contribution | Required evidence before prototype use | Required enforcement |
|---|---|---|
| Story world, screenplay, character constitution | author/owner; source version; project license; allowed derivatives | immutable source hash; project and territory scope |
| Character design, environment, prop, logo, costume | owner/license; reference source; trademark review where relevant | approved reference set only; no arbitrary URL ingestion |
| Human face, body, movement, performance | excluded from anchor unless fully fictional; later explicit scoped consent and labor review | identity vault; per-use authorization check; revocation stops new generation |
| Voice | synthetic stock voice license or performer authorization; no “sounds like” evasion | voice ID allowlist; spoken character mapping; language/dubbing scope |
| Music | composition and recording/master rights, or cleared original generation terms | cue-level rights IDs; no prompt requesting a living artist's style |
| Sound effects and ambience | library or provider license and attribution obligations | source/version retained at cue level |
| User prompt | product license only to process, retain as declared, and reproduce the session | avoid ownership grab; redact secrets; bounded retention |
| User-uploaded reference | excluded from anchor; later provenance, rights attestation, technical checks, and claims workflow | quarantine before use; perceptual/identity checks; no training by default |
| Model/provider output | applicable enterprise terms, model/version, safety policy, usage rights, indemnity exclusions | provider/version pinning; output receipt; re-review after terms/model change |
| Final branch | ingredient ledger, human contribution record, policy receipts, manifest | export only after rights and safety release gates pass |

**Inference.** Rights are dynamic. Expiry, revocation, territory, changed vendor terms, and a
successful claim can invalidate future generation or sharing even if an old session remains
lawfully retained. Treat `can_generate`, `can_play_private`, `can_export`, and `can_publish`
as separate decisions.

## Safety constitution and enforcement path

### Product policy layers

**Proposal.** Use three layers, evaluated in order:

1. **Non-negotiable service prohibitions:** child sexual exploitation, non-consensual sexual
   content, sexualized minors, realistic impersonation for deception or fraud, targeted
   harassment, credible threats, extremist recruitment, instructions that enable serious
   wrongdoing, and unlawful content in the served territory.
2. **Project constitution:** rating ceiling, violence/sexual-content boundaries, protected
   character traits, forbidden themes, cultural constraints, creator intent, and brand rules.
3. **Scene allowance:** what is narratively and visually permitted now, given prior facts,
   current location, characters, and unresolved obligations.

NIST identifies confabulation, dangerous/violent/hateful content, privacy, intellectual
property, information integrity, and other cross-modal risks for generative systems. **Fact.**
Source: [NIST AI 600-1 Generative AI Profile](https://doi.org/10.6028/NIST.AI.600-1)
(accessed 2026-08-25). **Inference.** A provider's generic safety filter is defense in depth,
not evidence that this product's constitution was enforced.

### Generation transaction

**Proposal.** Every intervention follows this fail-closed transaction:

1. authenticate session and enforce tenant, age, rate, and spend policy;
2. normalize language and detect secrets, identifiers, unsupported language, and unsafe input;
3. map accepted text to a bounded intent schema; never concatenate it into provider prompts;
4. validate intent against story, rights, and scene constitutions;
5. reserve budget and create a pending state transition;
6. generate candidates in an isolated provider job with only approved references;
7. inspect script, frames, motion, faces, speech transcript, audio events, music, and metadata;
8. validate narrative continuity, accessibility tracks, rights IDs, and provenance;
9. atomically commit the chosen playable artifact and story transition;
10. otherwise release the reservation and play a disclosed, pre-approved fallback without
    committing the rejected branch.

**Hypothesis S-1.** A bounded intent schema plus multimodal output review can keep critical
policy violations at zero in the anchor's predeclared adversarial suite while accepting at
least 80% of benign in-scope interventions. Test with human-adjudicated prompts and outputs
across every supported language; report false acceptance and false rejection separately.

**Kill condition.** Two critical output escapes after one predeclared corrective iteration,
or a safe-fallback rate high enough to negate perceived agency, blocks the architecture.

### Moderation and incident operations

**Proposal.** Before any external test, implement:

- an abuse taxonomy and severity matrix with named incident commander and legal escalation;
- immutable policy-decision receipts without unnecessary raw sensitive content;
- user-visible rejection and appeal/reporting paths;
- emergency generation disable, provider disable, asset/voice disable, and public-link revoke;
- human review tooling that shows only the minimum data needed and logs access;
- a separate, counsel-approved CSAM response and preservation procedure;
- a takedown and counter-notice workflow for any externally visible content;
- red-team corpora for prompt obfuscation, cross-language attacks, unsafe image references,
  character impersonation, adversarial subtitles/audio, and multi-turn boundary erosion;
- weekly abuse-spend, rejection, appeal, escape, and reviewer-wellbeing review during trials.

## Privacy and security architecture

### Data classification and retention

**Proposal.** Classify data before implementation:

| Class | Examples | Default posture |
|---|---|---|
| Restricted identity | face/voice embeddings, scans, performer contracts, verification media | excluded from anchor; isolated vault; tenant key; no model training; access approval |
| Sensitive creative | unreleased scripts, character bibles, reference art, generated dailies | tenant scoped; encrypted; signed URLs; no public provider reuse |
| Personal | account, prompts, choices, support reports, IP/device data | purpose limited; minimize; documented deletion/export |
| Audit | hashes, artifact IDs, policy result, provider/model/version, consent/rights ID | durable but pseudonymous; never use hashes as a substitute for deletion analysis |
| Public | explicitly released branch and public provenance disclosure | release gate and revocation/takedown state |

**Hypothesis P-1.** The anchor can operate with raw prompts retained for no more than 30 days
for abuse investigation, while retaining a normalized intent and pseudonymous audit record
for replay. This is a research retention target, not a legal safe harbor; validate with privacy,
safety, support, and replay tests before adopting it.

**Proposal.** Complete a data-flow inventory and, for EU deployment, a DPIA assessment before
live user testing. Record controller/processor roles, subprocessors, regions, transfer basis,
provider training/retention settings, deletion propagation, backup expiry, and incident notice
commitments. Do not infer these from a vendor's consumer product policy.

### Threat model

| Threat | Consequence | Minimum control |
|---|---|---|
| Prompt injection or policy smuggling | unsafe output or hidden tool action | intent parser; no raw prompt-to-tool path; allowlisted tools and schemas |
| Cross-tenant artifact/reference leak | unreleased IP or likeness exposure | tenant authorization on every object; scoped service identities; encryption and isolation tests |
| Arbitrary remote URL/reference ingestion | SSRF, malware, illicit media | no arbitrary URLs; proxy allowlist; size/type/decode limits; sandbox and quarantine |
| Malformed video/image/audio | parser exploit or worker compromise | hardened decoders in sandbox; dependency scanning; resource ceilings |
| Signed-URL or artifact-ID guessing | unauthorized playback | short-lived audience-bound URLs; non-enumerable IDs; authorization at origin |
| Provider or model drift | safety, quality, rights, or latency regression | pin snapshot where possible; release evaluation; kill switch; retained receipts |
| Spend exhaustion | denial of service and uncontrolled cost | per-user/session/tenant budget; reservation; concurrency and retry caps |
| Provenance key compromise | false trusted manifests | KMS/HSM-backed signing; separation of duties; rotation and revocation rehearsal |
| Audit/log exfiltration | prompts, identities, or creative secrets leak | structured redacted logs; access audit; no raw media by default |
| Insider misuse of likeness or unreleased assets | irreversible personal/creative harm | just-in-time access, dual approval, watermarking, alerting, contractual controls |

## Provenance and audit contract

**Proposal.** Emit two linked but distinct records:

1. a public C2PA 2.4 Content Credential for released audiovisual artifacts, containing the
   minimum appropriate creation/edit provenance and synthetic-media disclosure; and
2. a private append-only production receipt containing story state, viewer intent ID, policy
   decisions, ingredient rights IDs, provider/model/version, candidate lineage, human approval,
   artifact hashes, and accessibility/localization versions.

Never put raw prompts, performer contact details, consent documents, secrets, or stable viewer
identifiers in the public manifest. Support manifest stripping by retaining an external
verification route and visible in-product disclosure. **Inference.** Because C2PA is opt-in
and metadata can be removed, absence of a credential cannot prove that media is non-synthetic.

**Hypothesis A-1.** Every delivered anchor segment can be resolved from its public credential
to an authorized private receipt, while a privacy review finds no unnecessary personal or
commercially sensitive data in the public layer. Test stripping, tampering, key rotation,
revocation, deleted-user, and offline-verification cases.

## Accessibility and localization are generation invariants

### Accessibility baseline

- **Fact — standard.** WCAG 2.2 requires captions for prerecorded synchronized media at
  Level A, live captions at Level AA, and audio description for prerecorded video at Level AA.
  W3C guidance also calls for transcripts, accessible players, and planning description during
  scripting rather than bolting it on afterward. Sources: [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
  and [WAI Making Audio and Video Media Accessible](https://www.w3.org/WAI/media/av/)
  (accessed 2026-08-25).
- **Fact — EU scope.** The European Accessibility Act covers, among other areas, access to
  audiovisual media services and e-commerce; application depends on the service and national
  transposition. Source: [European Commission EAA overview](https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/disability/european-accessibility-act-eaa_en)
  (accessed 2026-08-25).
- **Inference.** A generated branch that lacks usable captions, descriptions, or accessible
  choice controls is not complete. Accessibility cannot be an asynchronous post-production
  step if the branch is played immediately.

**Proposal.** The anchor release gate requires:

- WCAG 2.2 AA user interface and player behavior, keyboard and assistive-technology operation;
- user-controlled pause or extended decision windows; no choice available only by timing,
  color, audio, gesture, or fine motor input;
- synchronized captions with speaker identity and meaningful non-speech audio, not dialogue-
  only subtitles;
- a descriptive transcript and an audio-description strategy for information communicated
  only visually;
- no unreviewed flashing patterns; volume, dialogue/music balance, and reduced-motion options;
- accessibility tracks bound to the same segment and story-state version as the picture;
- tests with disabled participants before product claims, not automation alone.

**Hypothesis AX-1.** Captions and concise scene descriptions can be generated from the
structured scene plan before picture render, then reconciled against the final output within
the consequence-latency budget. Measure semantic omissions and timing errors with disabled
reviewers; do not count model self-grading as proof.

### Localization controls

**Proposal.** Support no language until all of the following exist for that locale:

- input safety coverage including slang, euphemism, code-switching, and transliteration;
- intent-mapping and story-constitution tests with parity against the source language;
- subtitle line, reading-speed, names, pronouns, and speaker-label quality rules;
- cultural and rating review; locale-specific legal and platform classification;
- voice authorization for the exact language, accent, character, and dubbing use;
- human evaluation of narrative consequence, safety, and accessibility parity;
- a declared fallback that never silently processes unsupported input as another language.

**Inference.** Translation can change the accepted intent, rating, character relationship, or
rights scope. Localized text, voice, and policy decisions must be versioned artifacts, not
decorations on the source-language branch.

## Governance and release gates

### Decision rights

**Proposal.** The following approvals are non-substitutable:

| Decision | Accountable approval |
|---|---|
| story constitution and allowed agency | creative owner |
| asset, likeness, voice, music, and territory rights | production counsel/rights owner |
| policy taxonomy and critical-harm threshold | safety lead with legal escalation |
| data purposes, retention, subprocessors, and DPIA | privacy lead/DPO where applicable |
| threat model and production security | security lead |
| captions, description, controls, and locale release | accessibility/localization leads |
| provider/model/version release | engineering, safety, rights, and operations jointly |
| public publishing or minor access | new executive gate after dedicated legal/safety review |

### Prototype entry gate

**Proposal.** Do not admit live users until all are true:

- fictional adult anchor and target territories are fixed;
- rights ledger is complete for every ingredient, including provider terms;
- vendor data, training, retention, subprocessor, and incident terms are reviewed;
- moderation transaction fails closed and has passed the adversarial suite;
- per-session spend, retry, concurrency, and provider kill switches are tested;
- privacy inventory, retention/deletion tests, and DPIA decision are recorded;
- accessibility controls and branch-bound captions/descriptions pass representative tests;
- provenance and private audit receipts survive tampering and stripping tests;
- incident, takedown, user-report, and legal escalation exercises are completed;
- no minors, public gallery, arbitrary upload, real-person likeness, or passive inference path
  is reachable.

### Expansion gates

| Expansion | New evidence required; existing anchor evidence is insufficient |
|---|---|
| Public sharing/remixing | DMCA/DSA applicability, moderation staffing, claims/appeals, repeat-abuse policy, takedown SLO, provenance UX |
| User uploads | malware/media isolation, rights evidence, identity/CSAM detection and reporting procedure, deletion propagation |
| Real-person or performer replicas | scoped consent, compensation, union/labor and publicity review, biometric security, revocation and transfer tests |
| Minors as users or subjects | child-safety case, age assurance, parental/guardian process, COPPA and territory review; adult anchor cannot validate this |
| More languages | locale policy suite, human narrative/safety/accessibility evaluation, voice/dubbing rights |
| Personalized profiling | necessity/proportionality, lawful basis, user controls, discrimination and manipulation study; no covert emotion inference |

## Claims to carry into the package ledger

| ID | Claim | Class | Confidence | Validation still needed |
|---|---|---|---|---|
| SRG-01 | EU synthetic-media disclosure and machine-readable marking are design inputs for target EU distribution | Fact | high | counsel maps provider/deployer roles and exact launch UX |
| SRG-02 | C2PA provides verifiable provenance associations, not truth, consent, rights, or safety | Fact + inference | high | implementation and stripping/key tests |
| SRG-03 | The fictional-adult, private anchor is materially safer than likeness/upload/publishing variants | Inference | high | closed red team and legal review |
| SRG-04 | A bounded-intent, fail-closed transaction can preserve safety without erasing agency | Hypothesis | medium | adversarial multilingual prototype study |
| SRG-05 | Public sharing is a separate hosting/abuse-operations product | Inference | high | jurisdiction and platform analysis |
| SRG-06 | Accessibility metadata must be generated and bound before immediate playback | Inference | high | latency and disabled-user evidence |
| SRG-07 | Raw-prompt retention can be short while normalized intent plus artifacts preserves replay | Hypothesis | medium | replay, abuse, privacy, and deletion tests |

## Evidence score and open blockers

**Inference — current score: 1/3 (plausible only)** for safety/rights and 1/3 for
accessibility/localization. Authoritative rules and a credible control design exist, but no
repository implementation, live provider evaluation, legal opinion, red-team result, disabled-
user study, incident exercise, or retained audit receipt has been demonstrated in this research.

The prototype cannot move beyond a closed research direction until these blockers have owners:

1. target-country legal analysis and chain-of-title template;
2. provider enterprise terms, data handling, output rights, policy, and change-notice review;
3. multimodal moderation benchmark with critical-harm adjudication;
4. rights ledger and revocation semantics tied to generation, play, export, and publish;
5. C2PA/public disclosure plus privacy-preserving private receipts;
6. accessible branch generation and disabled-participant evaluation;
7. localization policy parity for any non-source language;
8. staffed incident, appeal, claims, takedown, and—if applicable—mandatory reporting process.

