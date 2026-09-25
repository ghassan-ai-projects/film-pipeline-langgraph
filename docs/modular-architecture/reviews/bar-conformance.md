# Capstone review of the original modular architecture program

Review date: 2026-09-25. Baseline source commit: `fb85baa0e6b769b709791a96a89980089304bf13`. Objects judged: `00`–`05` and their supporting audit, design, and review files **as found for this review**. The reviewer did not author the original program. This is an independent decision on the original A/B bars, not a retroactive approval of its migration. See `../06-independent-review-and-decision.md` for the replacement direction.

## Verdict

**The original package is not ready to execute.** It contains useful, often reproduced findings and a serious design attempt. Its quantitative summaries and phase gates are not closed against the second review round. The right outcome is to finish the *review* with a no-go decision and a smaller, test-led plan, rather than declare the original bars met.

| Bar from `00` | Verdict | Decisive evidence and limit |
|---|---|---|
| A1 — coverage | **Partial** | The coverage adversary found 13 missed seams (`adversarial-coverage.md` §3–4); some were subsequently added to audits, but `02` still defers 11 of them from its concern mapping (`02` appendix). File coverage is stronger than concern coverage. |
| A2 — reproducible evidence | **Not met** | The evidence adversary replayed 146 finding samples and reported 9 non-reproducing or missing `Reproduce` items (`adversarial-evidence.md` §2, §8). This review did not replay a corrected full corpus. |
| A3 — drift proof | **Not met** | `verify-19.md` rejects `F-ARTIFACT-13`: the named phase-column mutation is not live and the proposed enum mutation fails 19 tests. The ledger still counts it. |
| A4 — classification | **Partial** | The coverage adversary found two live blocks without a valid O-class (`adversarial-coverage.md` §4). Some later corrections exist, but no closed corpus-wide pass is recorded. |
| A5 — single-owner concerns | **Partial** | `01` maps clean concerns, but its corpus totals are 178 while the current audit text has 189 severity bullets. It is a historical snapshot, not a current closure ledger. |
| A6 — independent verification | **Partial** | `verify-01`–`verify-20` exist. The old README promised `verify-21`, which does not exist. More importantly, `verify-15`–`verify-20` correct and reject findings that `02`–`05` still treat as live or at old severity. Verification exists; reconciliation does not. |
| A7 — prior art | **Partial** | Several second-round reviewers identify incorrect `new` claims and wrong prior-art anchors (`verify-18.md` and `verify-19.md`). No later comprehensive closure is recorded. |
| A8 — actionable owner and guard | **Partial** | Most finding blocks propose both. A guard sketch is not evidence that it can fail under mutation or pass CI; the old enforcement plan has unsatisfied guard assumptions (`adversarial-architecture.md` §1; `adversarial-roadmap.md` R2.6). |
| A9 — adversarial coverage | **Not met** | The adversarial pass was done and found real holes; the resulting audit additions were not fully reconciled into `02` or independently closed as a set. |
| B1 — one responsibility per module | **Partial** | `03` has responsibility and non-goal descriptions, but the adversary found five module justifications whose declared N/I/R criterion was not established (`adversarial-architecture.md` O-18). The replacement design does not pre-approve the catalog. |
| B2 — declared contract | **Partial** | `03` lists API and state, but its `public_api` does not constrain actual cross-package imports as proposed (`adversarial-architecture.md` O-05). |
| B3 — dependency law | **Partial** | The target matrix was shown acyclic; the originally proposed layer-direction guard was absent (`adversarial-architecture.md` O-04), and `05` is a design for future source/tests, not a passing gate at this commit. |
| B4 — conformance map | **Met for the original snapshot** | The adversarial architecture review reproduced a 281/281 source-file assignment (`adversarial-architecture.md` FA-3). This does not validate the target architecture itself. |
| B5 — independently shippable phases | **Not met** | The roadmap's revision-2 reviewer names P7, P11, P12, P19, P20 as not shippable alone and identifies entry-point, compatibility, and rollback contradictions (`adversarial-roadmap.md` R2.5–R2.6). |
| B6 — guard tests | **Not met** | The proposed suite is not installed. The reviewed canary omits `--no-cov` despite `pyproject.toml`'s 90% threshold, the acyclicity guard misses intra-package cycles, and an agreement guard is green with the recorded kind mismatch (`adversarial-roadmap.md` R2.6). |
| B7 — compatibility | **Partial** | `03` names contracts, but the adversary found unlisted persisted-representation changes and an absent MCP freeze test (`adversarial-architecture.md` O-14, O-22). No old-data migration proof exists. |
| B8 — adversarial validation | **Not met** | The four attacks are substantive; architecture and roadmap objections remain blocking in their latest recorded verdicts. This capstone does not waive them. |
| B9 — concrete module justification | **Not met** | The proposed `budget`, `governance`, and other new modules have APIs without current call sites or behavior proofs (`adversarial-architecture.md` O-18); the 20-module count is not forced by the audited defects. |

## Independent checks in this review

- The source revision remains `fb85baa0e6b769b709791a96a89980089304bf13`.
- `rg '^### F-'` finds **191** headings and `rg '^- **Severity:**'` finds **189** live bullets in `audit/*.md`; `02` maps 178 and explicitly defers 11 at its last sync. Text counts are not verification counts.
- `verify-19.md:346-438` rejects `F-ARTIFACT-13`, while `02:518-520` still consolidates it and `04:235` still schedules it.
- `graph/graph.py:201` constructs a graph at import time and `:40-51` may create a checkpoint directory when persistence is enabled; `verify-15.md:100-106` narrows the impact from the original finding.
- `app/_graph_exec.py:336-345` does not carry `_pending_row_updates` back into persisted state, while `graph/nodes/qc.py:68-80` consumes it for matrix patches.
- `.gitignore` previously excluded the entire `docs/` tree; this review makes the written package visible to Git while leaving `enola-out/` generated files and the unshipped prototype ignored. Git visibility does not change `.github/workflows/ci.yml`'s `docs/**` path exclusion.

## Closure boundary

The review and decision are complete. The **architecture implementation and original A/B bars are not complete**. A team can now act on the smaller plan in `06`, beginning with behavior tests, without mistaking an unreconciled historical ledger for an approved migration. A future claim that A/B is met requires current source reproducers, a reconciled finding inventory, passing guards, persisted-data compatibility evidence, and a fresh review after implementation.
