---
name: skill-first-engine
description: "Git-based Skill-First memory architecture and multi-tier loop engine for AI agents. Replaces fragile RAG with version-controlled Git skill repositories, strict transactional sync with backpressure, top 30% smart zone context management, Ralph Loop benchmark iteration, and Meta Loop anti-collapse restarts."
---

# GIT-BASED SKILL-FIRST MEMORY ARCHITECTURE & LOOP ENGINE (SKILL-FIRST & LOOP ENGINE)

## PURPOSE

You operate under the Skill-First architecture, where every skill is not merely a static prompt, but an autonomous Git repository combining operational guidelines (`SKILL.md`), deterministic executable tools (`scripts/`), structured data with state contracts (`templates/`, `data/`), and continuous change history (`.git`). This file-based environment replaces external vector databases (RAG) and functions as your verifiable, deterministic, long-term memory.

Methodological foundation: Keynote by Konstantin Krestnikov - "Git-based skills: The new memory of AI agents. My experience" (https://www.youtube.com/watch?v=a-NIeMB-Hj8).

---

## RULE 1. SKILL ANATOMY AND REPOSITORY STRUCTURE

Every skill created or operated by an agent must follow a strict internal structure:

```text
skill-name/
|-- SKILL.md                 # Skill passport, triggers, and full operational doctrine
|-- scripts/                 # Executable deterministic utilities (Python / Bash)
|-- data/                    # Concrete datasets, audit logs, and accumulated artifacts
|-- templates/               # Rigid entity schemas, card templates, and state definitions
|-- checks/                  # Backpressure validation contour (CI / schema checkers)
`-- references/              # Methodological references, theory, and background documentation
```

### 1.1. Skill Passport (`SKILL.md`)
* Short Trigger Description (1-2 sentences in YAML frontmatter): the only part loaded into the resident system prompt prior to activation. Must state triggers and applicability with high precision.
* Full Operational Doctrine: loaded into context only when the skill is explicitly activated. Contains decision rules, edge cases, input/output contracts, and past calibration learnings.

### 1.2. Executable Tools (`scripts/` or `bin/`)
* Local scripts in Python or PowerShell/Bash that handle deterministic transformations, data extraction, and repetitive parsing.
* Never waste LLM tokens on mechanical operations (sorting, hashing, formatting, regex filtering). All raw processing is delegated to local scripts.

### 1.3. Data and State Contour (`data/` and `templates/`)
* `templates/`: strict entity contracts and document prototypes (item cards, user profiles, report formats, loop states).
* `data/`: active data and persisted artifacts. Never load full directories into prompt context: use targeted queries (`grep`, `find`, or dedicated scripts) to pull only necessary slices.

### 1.4. Backpressure Contour (`checks/` or CI)
* Deterministic verification scripts validating data schema, syntax, and business invariants.
* Scripts exit with code 0 on success, or non-zero with descriptive errors. The agent must resolve any failure before completing a step.

---

## RULE 2. RIGID GIT PROTOCOL AND BACKPRESSURE VALIDATION

For every interaction with a stateful skill, the agent must execute a four-phase transactional cycle:

```text
[Ingress] -> git pull/status -> [Execution] -> checks/ (Backpressure) -> [Egress] -> git commit & push
```

1. Ingress Synchronization:
   Before reading state or performing tasks, execute `git pull` (or inspect `git status`) inside the skill repository to incorporate changes from other agents or external workers.

2. Merge Conflict Resolution:
   Never halt or wait for human intervention if a merge conflict is logically reconcilable. Analyze conflicting branches, combine valid records without data loss (preserving timestamps and unique entries), and commit the merge resolution.

3. Backpressure Verification:
   After altering code, data, or rules, execute validation scripts from `checks/`. Completing a task or creating a commit is strictly forbidden if validation fails. Any error forces the agent back to the correction step.

4. Egress Commit & Push:
   Upon passing backpressure checks, execute an atomic `git add`, compose a semantic commit message, and run `git push`.

---

## RULE 3. AUTOMATED SKILL CREATION AND CURATION

The agent's memory evolves continuously under three operational laws:

### 3.1. 5-Step Creation Trigger
If solving a task requires more than 5 consecutive tool calls (reading, searching, debugging commands, parsing outputs) and reveals a reproducible pipeline:
* Immediately propose saving the sequence as a new skill, or scaffold a standard draft automatically.
* Transform one-off execution into a reusable, version-controlled organizational asset.

### 3.2. Continuous Feedback Calibration
When a user points out a logical flaw, edge-case failure, or incorrect output:
* Never limit the fix to the active chat session.
* Immediately open the corresponding `SKILL.md` and append a new rule, boundary condition, or exception to the doctrine.
* Every mistake is corrected in the repository exactly once.

### 3.3. Curator Mode (Weekly Memory Hygiene)
Triggered weekly or on maintenance requests:
* Consolidation: merge overlapping, narrow, or duplicate skills into modular, mature skills while preserving git history.
* Pruning:
  - Skills unused for >30 days: compress frontmatter description to a single line to preserve resident context budget.
  - Skills unused for >90 days: move to `archive/` with full git history preservation.

---

## RULE 4. CONTEXT HYGIENE, SMART ZONE (TOP 30%), AND NESTED LOOPS

### 4.1. Smart Zone Preservation (First 30% of Context Window)
* LLM reasoning fidelity drops non-linearly once context usage exceeds 30-40%.
* Never load large files or raw log dumps directly into chat context.
* Use targeted filtering (`grep`, `head -n`, `tail -n`, Python JSON selectors) or delegate heavy reading to isolated subagents that return concise factual summaries.

### 4.2. Outer Execution Cycle (Ralph Loop)
For long-horizon tasks, refactoring, and metric optimization, operate in an autonomous loop with state anchored to disk:

1. Maintain `STATE.md` on disk:
   - Primary objective and quantifiable target metric;
   - Current metric score;
   - Tested hypotheses ledger (marked as ACCEPTED or REJECTED);
   - Exactly one next actionable step.
2. Iteration: formulate 1 hypothesis, apply minimal code/data diff, execute objective benchmark or test suite.
3. Decision:
   - Metric improved and tests pass: commit changes, update `STATE.md`.
   - Metric regressed or tests fail: immediately execute `git reset --hard HEAD` to the last known good commit, log failure in `STATE.md`, and clean context for a fresh attempt.

### 4.3. Escaping Local Optima (Meta Loop / Anti-Collapse)
When 3 consecutive iterations yield no metric gain and the model circles around the same architecture:
1. Snapshot current attempts into `archive/attempt_N/`.
2. Reset workspace to baseline (`git reset --hard <baseline>`).
3. Forbid previous approaches and design an alternative along an orthogonal architectural vector.
4. Once a working prototype emerges on the new vector, inspect the archive and synthesize the strengths of both approaches.

---

## RULE 5. FACETED CATALOG AND TWO-STROKE NAVIGATION

To scale beyond 50 skills without deep hierarchical traversal traps (P = 0.9^5 = 0.59 routing collapse):
* Maintain a strict 2-level layout: `domain/skill`.
* Stroke 1: read domain overview from `ROOT_INDEX.md` and load the specific domain `INDEX.md` (1 tool call).
* Stroke 2: open the target `SKILL.md` directly via relative path.
* Fast Fallback: use `grep -rn "keyword" */INDEX.md` for instant lookup across the entire catalog.

---

## BUNDLED SCRIPTS & TOOLS

- `scripts/build_index.py`: faceted catalog builder, domain classifier, and `ROOT_INDEX.md` / `INDEX.md` generator.
- `scripts/git_skill_sync.py`: transactional git sync controller with backpressure check execution.
- `scripts/curate_skills.py`: memory hygiene auditor detecting stale skills (>30d, >90d) and consolidation candidates.
- `scripts/loop_runner.py`: Ralph Loop controller managing `STATE.md`, test verification, and automated rollbacks.
- `checks/validate_skill.py`: backpressure validator verifying skill anatomy, frontmatter, and typography hygiene.
- `templates/`: scaffolds for skill passports (`SKILL_TEMPLATE.md`), state logs (`STATE_TEMPLATE.md`), and backpressure checks (`CHECK_TEMPLATE.py`).
- `references/krestnikov_method.md`: engineering distillation of Konstantin Krestnikov's keynote.
