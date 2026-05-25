# Autonomous Engineering Orchestration System PRD v1.3 Final

## What Changed In This Final Version

- Replaced Gemma 2 with the already-downloaded Gemma 4 uncensored GGUF model.
- NVIDIA API is the only required cloud provider.
- Claude is optional and disabled by default.
- Local-first routing is used for ordinary tasks.
- High-risk critical tasks route directly to NVIDIA API.
- GGUF system RAM offload is allowed with hardware safety caps.
- Skills and plugins are supported through a permission-gated capability layer.

## 1. Executive Summary

Build a self-hosted autonomous engineering orchestration system for one developer.

The system accepts a project plan or task, inspects the repo, asks for missing assets or clarifications, chooses the right local or cloud model, generates code changes, validates them, repairs failures, commits clean work to Git, and keeps the operator informed through Telegram and VSCode/Codex/Claude-Code-style tools.

The system is quality-first. Speed and cost are secondary. For ordinary tasks, it prefers local GGUF models. For complex, high-risk, or failed tasks, it escalates to NVIDIA API.

## 2. Core Goal

The first useful version must reliably do this:

1. Accept one engineering task.
2. Inspect the repo.
3. Ask for missing context, assets, credentials, or business rules.
4. Route to a local GGUF model or NVIDIA API.
5. Generate a patch.
6. Run validation.
7. Retry or repair failures.
8. Commit passing work on a task branch.
9. Notify the operator.

DAG execution, memory, plugins, browser QA, GitHub automation, and overnight autonomy come after the single-task loop is stable.

## 3. Operator Profile

The operator is a single developer who:

- Uses Telegram for mobile supervision.
- Uses VSCode plus Codex/Claude Code-style workflows for inspection.
- Runs Ollama locally on Windows.
- Uses GGUF quantized models.
- Already has Gemma 4 uncensored GGUF downloaded.
- Is okay with system RAM offload.
- Wants NVIDIA API for cloud models.
- May optionally add Claude later if it stays simple.
- Values quality over speed and cost.
- Will provide assets, credentials, screenshots, business rules, and clarifications when asked.

## 4. Model Strategy

### Local Models

All local models are GGUF quantized through Ollama or a compatible local runtime.

| Role | Local Model |
| --- | --- |
| Fast/simple work | Gemma 4 uncensored GGUF |
| Primary local coding | Qwen2.5-Coder 7B GGUF |
| Local planning fallback | Hermes 3 8B GGUF or smaller safe planning model |
| Local vision/OCR | Qwen2.5-VL 7B GGUF |
| Local image generation | Pony/local image model if configured |
| Embeddings | nomic-embed-text or equivalent |

Gemma 4 uncensored is used for simple local tasks, summaries, commit-message drafts, direct rewrites, creative copy, and uncensored/local-only content where appropriate. It must not be used for high-risk critical engineering tasks unless explicitly overridden.

Local models may offload layers to system RAM.

### Cloud Models

NVIDIA API is the required cloud provider.

| Role | NVIDIA API Model |
| --- | --- |
| Primary cloud coding | Qwen2.5-Coder 72B |
| Planning | Llama 3.1 70B or Nemotron 70B |
| Hard reasoning | Nemotron 70B |
| Vision/OCR | Qwen2.5-VL 72B |
| Image generation | FLUX if available |

### Optional Claude

Claude is optional and disabled by default.

If configured, Claude may be used as an optional maximum-reasoning provider for critical tasks after NVIDIA failure or by explicit operator override. The system must remain fully usable without Claude.

## 5. Hardware Safety Policy

System RAM offload is allowed, but unattended execution must be protected.

| Resource | Warning | Hard Stop |
| --- | ---: | ---: |
| GPU temperature | 78C | 83C |
| Free system RAM | 4GB | 3GB |
| Sustained memory pressure | 85% | 90% for 2 minutes |
| Generation progress | slow warning | no meaningful token progress for 3 minutes |
| GPU/driver instability | any warning | stop local execution |

Hard-stop behavior:

- Stop local model execution.
- Mark current task as paused or failed safely.
- Do not continue critical tasks locally.
- Route to NVIDIA API if allowed.
- Otherwise ask the operator.

RAM offload is not normally hardware-damaging. The real risks are heat, driver resets, paging, instability, and unattended runaway jobs.

## 6. Routing Rules

Routing order:

1. Manual model override wins unless it violates safety.
2. Missing assets or unclear requirements pause the task and ask the operator.
3. High-risk critical tasks go directly to NVIDIA API.
4. Ordinary tasks run local first.
5. If local fails twice, escalate to NVIDIA API.
6. If context is too large for local, use NVIDIA API.
7. If local resource health is unsafe, stop local execution and use NVIDIA API or ask.
8. If NVIDIA is unavailable for a critical task, pause and ask. Do not silently downgrade.
9. Optional Claude is used only if configured and explicitly allowed.

Critical tasks include:

- auth
- payments
- security
- secrets
- deployment
- database migrations
- data deletion
- production CI/CD
- architecture decisions
- complex debugging
- tasks marked high-risk by scout

Local-first applies only to non-critical work.

## 7. Asset And Clarification Protocol

The system must ask before assuming.

It asks for:

- API keys
- credentials
- `.env` values
- brand colors
- logos
- screenshots
- reference designs
- business rules
- deployment targets
- GitHub repo names
- project copy/content
- user profile data
- pricing/permission rules
- anything required to avoid hallucination

No placeholder may be used in production-ready output unless the operator explicitly approves placeholder mode.

Placeholder mode cannot mark a project complete.

## 8. Skills And Plugins

Yes, the workflow supports skills and plugins.

They are implemented as a simple capability layer.

Supported capability types:

- native orchestrator skills
- MCP tools
- Codex-style skills/plugins
- Claude Code-style skills if available
- browser automation
- document tools
- spreadsheet tools
- presentation tools
- image generation tools
- GitHub tools

Rules:

- Skills/plugins are capabilities, not authorities.
- They cannot bypass validation.
- They cannot directly change task state.
- They cannot commit, merge, push, or release directly.
- They cannot access secrets unless declared and approved.
- They cannot write files unless approved.
- They cannot install dependencies unless approved.
- They cannot use network unless approved.

Read-only inspection can run without approval if the capability is already enabled.

## 9. Task Lifecycle

```text
PENDING
  -> READY
  -> SCOUTING
  -> AWAITING_ASSETS
  -> AWAITING_CLARIFICATION
  -> AWAITING_APPROVAL
  -> EXECUTING
  -> VALIDATING
  -> COMPLETE

Failure path:
VALIDATING
  -> FAILED
  -> RETRYING
  -> ESCALATED
  -> DEAD_LETTER
```

Rules:

- Only deterministic orchestrator code changes task state.
- Every transition is logged.
- Every task has a branch.
- Generated changes go to temp files first.
- Real files are updated only after validation.
- No task is complete until validation passes.
- Dead-letter tasks remain queryable and can be decomposed.

## 10. Validation Profiles

Validation must match the project type.

### Python Profile

- syntax/AST parse
- ruff
- mypy if applicable
- pytest
- coverage
- detect-secrets
- bandit for security-sensitive code
- dependency vulnerability scan

### Frontend Profile

- install/build check
- lint
- unit tests if present
- Playwright browser test
- console error check
- responsive viewport check
- layout overlap check
- Lighthouse/performance check where applicable
- canvas/WebGL nonblank pixel check for visual/canvas apps

### Documentation/Artifact Profile

- render docs where applicable
- validate diagrams
- check links
- verify exported PDFs/PPTX/images open correctly
- screenshot/render review for layout-sensitive artifacts

### Mixed Project Profile

Use all relevant checks from each profile.

The planner must assign a validation profile when a project is created.

## 11. Git Workflow

Per task:

1. Create task branch.
2. Generate patch into temp area.
3. Validate patch.
4. Apply patch to real files.
5. Add only touched files.
6. Run secret scan on staged files.
7. Commit with conventional commit message.
8. Update memory/index.
9. Notify operator.

Never use `git add .`.

Rollback must restore the repo to the pre-task state for that task only.

## 12. Memory And Context

The system uses fresh context per task.

Context priority:

1. task description
2. operator instructions
3. provided assets
4. scout plan
5. files being edited
6. relevant interfaces/imports
7. failure digest
8. semantic summaries
9. project summary

If the model lacks required information, it must return `NEEDS_CONTEXT`, and the task pauses to ask the operator.

## 13. Observability

Log every important event:

- task state transitions
- model selected
- provider used
- prompt metadata
- token usage
- latency
- validation result
- failures
- retries
- asset requests
- plugin/skill invocations
- operator approvals
- commits

SQLite is the source of truth.

Langfuse and Sentry are optional but recommended after the core loop works.

## 14. Spend And Provider Policy

NVIDIA API is the required cloud provider.

Track:

- requests
- input tokens
- output tokens
- estimated spend
- free credits
- rate-limit errors
- failed calls

Cost policy:

- Ordinary work: prefer local first.
- Critical work: use the model most likely to succeed.
- If spend cap is reached, pause cloud calls and ask.
- Do not downgrade critical tasks silently.
- Optional Claude spend is tracked only if Claude is configured.

## 15. Build Plan

### Phase 1: Single-Task Local Runner

Deliverable: one task runs locally, validates, and commits.

Build:

- project config
- SQLite state
- task table
- local model call
- patch generation
- validation runner
- Git branch/commit
- basic CLI or Telegram submit

### Phase 2: Retry And NVIDIA Escalation

Deliverable: local failure escalates to NVIDIA.

Build:

- model router
- NVIDIA OpenAI-compatible adapter
- failure classification
- retry loop
- resource safety checks
- provider usage tracking

### Phase 3: Asset Asking

Deliverable: missing inputs pause task and ask operator.

Build:

- asset request table
- clarification request table
- Telegram prompts
- encrypted credential storage
- resume after answer

### Phase 4: Telegram Control

Deliverable: mobile supervision works.

Build commands:

- `/new_task`
- `/status`
- `/task`
- `/approve`
- `/reject`
- `/retry`
- `/rollback`
- `/switch_model`
- `/pause`
- `/resume`
- `/vram`
- `/spend`

### Phase 5: Skills And Plugins

Deliverable: approved capabilities can be invoked safely.

Build:

- capability registry
- MCP adapter
- read-only skill invocation
- approval gates for mutating tools
- invocation logs
- validation after skill output

### Phase 6: Repo Memory

Deliverable: model receives relevant repo context.

Build:

- file summaries
- embeddings
- semantic search
- failure digest memory
- changed-file reindexing

### Phase 7: DAG Execution

Deliverable: approved project plan becomes ordered task graph.

Build:

- planner
- DAG validation
- dependency tracking
- file locks
- task scheduler
- critical path detection

### Phase 8: Browser And Visual QA

Deliverable: frontend work is visually checked.

Build:

- browser automation
- screenshots
- viewport checks
- console checks
- Lighthouse
- canvas/WebGL checks

### Phase 9: GitHub Automation

Deliverable: PR-ready workflow.

Build:

- GitHub branch/PR creation
- CI status tracking
- PR summary
- release/changelog later

## 16. Success Criteria

The system is useful when:

- It can complete one real coding task without manual code editing.
- It asks when information is missing.
- It validates before committing.
- It escalates from local to NVIDIA when needed.
- It does not damage workflow state.
- It does not silently guess critical details.
- It can be paused, redirected, retried, or rolled back.
- It works without Claude.
- Skills/plugins can be used safely.
- The operator remains supervisor, not manual implementer.

## Assumptions And Defaults

- NVIDIA API is the only required cloud provider.
- Claude is optional and disabled by default.
- Local GGUF models may use system RAM offload.
- Gemma 4 uncensored GGUF replaces Gemma 2 for simple local tasks.
- Gemma 4 uncensored is not the default for high-risk engineering work.
- Hardware safety caps are enabled by default.
- Local-first applies only to ordinary tasks.
- High-risk critical tasks use NVIDIA directly.
- Skills/plugins are supported but permission-gated.
- The MVP should be single-task first, not full DAG automation.
