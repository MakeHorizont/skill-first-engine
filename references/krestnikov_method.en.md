# SKILL-FIRST ARCHITECTURE & GIT-BASED MEMORY FOR AI AGENTS

Methodological distillation based on Konstantin Krestnikov's keynote: "Git-based skills: The new memory of AI agents. My experience" (https://www.youtube.com/watch?v=a-NIeMB-Hj8).

---

## 1. THE LIMIT OF CLASSICAL RAG AND THE SHIFT TO GIT-BASED SKILLS

The traditional pattern for long-term AI memory relies on external vector databases (RAG / Vector DBs), which exhibit fundamental failure modes in production agentic workflows:

1. Stochastic Search vs. Deterministic Retrieval:
   Cosine similarity retrieves text chunks with semantic proximity, but provides zero guarantee of logical completeness, freshness, or schema compliance. Agents routinely retrieve stale or irrelevant documentation.

2. Absence of Temporal History and Provenance:
   Vector databases cannot explain when a rule changed, who modified it, or why an earlier protocol was deprecated.

3. Inability to Execute:
   Vector store chunks are passive text. They force the LLM to burn expensive reasoning tokens reading, parsing, and interpreting even elementary algorithms.

---

## 2. SKILL-FIRST ARCHITECTURE: REPOSITORY AS A MEMORY UNIT

Under Skill-First architecture, each skill is a self-contained Git repository:

```text
+-------------------------------------------------------------+
|                       GIT REPOSITORY                        |
|                                                             |
|  [SKILL.md]     -> Passport, triggers, and operational rules|
|  [scripts/]     -> Executable tools (deterministic lifting) |
|  [data/]        -> Active state, records, and datasets      |
|  [templates/]   -> Rigid schemas and prototypes             |
|  [checks/]      -> Backpressure validation contour (CI)     |
|  [.git/]        -> Immutable audit trail and version history|
+-------------------------------------------------------------+
```

### Core Advantages:
- Precision Retrieval: the agent uses native file tools (`grep`, `find`, `read_file`) to inspect structured files, loading only the necessary slice of data into context.
- Deterministic Tooling: mechanical data transformations are handled by local scripts (Python/Bash), preserving context for high-level reasoning.
- Multi-Agent Collaboration: desktop harnesses (Claude Code, Antigravity, Cursor) and lightweight mobile bots (Hermes, Telegram agents) work concurrently on the same Git repository, with Git handling synchronization and merge conflict resolution.
- Backpressure Protection: local CI/CD scripts validate schemas and invariants, rejecting invalid states before commits.

---

## 3. CONTEXT ECONOMICS AND THE SMART ZONE (FIRST 30%)

Empirical research shows that LLM reasoning fidelity drops non-linearly as context fills up:

- **0% - 30% of Context Window (Smart Zone)**: peak reasoning depth, strict instruction following, minimal hallucinations.
- **30% - 70% of Context Window**: gradual degradation, missed boundary conditions, fuzzy recall.
- **70%+ of Context Window**: critical failure zone, breakdown of complex structured output.

### Context Preservation Strategy:
Large data dumps are forbidden in the main conversation thread. Slicing and extraction are delegated to deterministic local utilities or isolated subagents.

---

## 4. MULTI-TIER AGENTIC LOOPS (LOOP ENGINEERING)

To sustain multi-day, autonomous execution (Dark Factory mode), agentic execution is structured across three nested tiers:

### Tier 1. Inner Loop (Task-level)
The native harness turn loop executing single subtasks and tool calls.

### Tier 2. Outer Loop (Ralph Loop)
An autonomous loop iterating over the repository with clean context across runs:
- State is anchored to `STATE.md` on disk;
- Each iteration tests exactly one falsifiable hypothesis against an objective test suite or benchmark;
- Success -> `git commit` and state update;
- Regression -> `git reset --hard HEAD` and clean context reboot.

### Tier 3. Meta Loop (Anti-Collapse)
When 3 consecutive iterations yield no progress, Karpathy's collapse phenomenon is triggered:
- The current attempt is archived to `archive/attempt_N/`;
- Workspace resets to clean baseline;
- The agent is forced to explore an orthogonal architectural paradigm from scratch;
- The working prototype is later synthesized with earlier archived findings.
