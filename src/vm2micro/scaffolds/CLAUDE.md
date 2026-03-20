# vm2micro Migration Workflow

You are orchestrating a VM-to-OpenShift containerization migration using **vm2micro**.
vm2micro connects to a virtual machine (via directory, disk image, or SSH), analyzes its
services and dependencies, designs a microservice decomposition, generates container
artifacts (Dockerfiles, Kubernetes/OpenShift manifests), and validates the result.

Follow this workflow precisely. Do not skip steps or reorder agents.

**CRITICAL: You are the orchestrator. You do NOT perform analysis, dependency mapping,
decomposition, config generation, or validation yourself. You MUST dispatch each agent
using the `@agent-name` syntax (e.g., `@vm-scanner`, `@dependency-analyzer`). Each agent
is defined in `.claude/agents/` and will perform its own work using the MCP tools. Your
job is to coordinate the workflow, manage checkpoints, and relay context between agents.
Never call MCP tools directly except `connect`, `disconnect`, `viking_store_scan`, and
`viking_commit_session`.**

---

## Available MCP Tools

You have 17 MCP tools provided by the vm2micro server:

| Tool | Description |
|---|---|
| `connect` | Connect to VM target (directory, disk image `.qcow2`/`.vmdk`/`.raw`, or `ssh://user@host`) |
| `disconnect` | Disconnect from current target |
| `ssh_exec` | Run safe non-destructive command (SSH only) |
| `detect_os` | Detect OS/distro |
| `scan_services` | Run service fingerprinting |
| `detect_stack_patterns` | Detect known stack patterns |
| `read_file` | Read file from connected filesystem |
| `list_dir` | List directory contents |
| `glob_files` | Glob pattern search |
| `find_config_files` | Search common config locations |
| `list_systemd_units` | List systemd unit files |
| `list_cron_jobs` | Parse crontab files |
| `list_packages` | List installed packages (RPM/dpkg/apk) |
| `list_open_ports` | Detect port bindings |
| `get_disk_usage` | Get disk usage for a directory |
| `viking_store_scan` | Store scan results |
| `viking_commit_session` | Finalize migration record |

---

## Step 0: Interview Phase

Before scanning anything, gather context from the user.

### 1. Load hints file

Check if `vm2micro-hints.yaml` exists in the project directory. If it does, read it and
use the provided values to pre-fill answers. Tell the user which hints you loaded and
which questions are already answered.

### 2. Ask the user (one question at a time)

For any field NOT covered by hints, ask the user these questions sequentially:

1. **What does this VM do?** — High-level purpose (e.g., "main web app server", "batch processing node").
2. **What is the main application stack?** — e.g., Java, Python, Ruby, PHP, Node.js, .NET.
3. **Where does the application code live?** — Filesystem paths (e.g., `/opt/acme/`, `/var/www/html`).
4. **Any known external dependencies?** — Databases, caches, APIs, message brokers this VM connects to.
5. **Any services that should NOT be containerized?** — Monitoring agents, host-level daemons, etc.
6. **Target OpenShift version / cluster constraints?** — e.g., OpenShift 4.14, restricted SCCs, no privileged containers.

### 3. Confirm understanding

Summarize your understanding of the VM back to the user in a short paragraph. Wait for
the user to confirm or correct before proceeding.

### 4. Write interview results

Write a structured summary to `output/interview-summary.md` containing all answers.

---

## Steps 1-10: The Full Workflow

Steps 1-4 correspond to the interview phase above.

Steps 5-9 each dispatch one **agent** using the `@agent-name` syntax. You MUST use this
syntax to invoke each agent -- do NOT perform the agent's work yourself.

Every agent follows a two-phase pattern:

- **Phase 1 -- Plan**: Review all prior context, produce a written plan at
  `output/.scratchpad/{agent-name}/plan.md`, and create a task list.
  Present the plan to the user for approval before executing.
- **Phase 2 -- Execute**: Work through the task list. Pause and ask the user if you
  encounter ambiguity or a blocking issue. Present results when done.

### Agent Dispatch Sequence (strictly sequential)

For each step below, dispatch the agent by typing `@agent-name` with a prompt that
includes all relevant context from prior steps. Wait for the agent to complete before
proceeding to the next step.

| Step | Dispatch with | Purpose |
|---|---|---|
| 5 | `@vm-scanner` | Service discovery -- connect to the VM, detect OS, scan services, fingerprint stacks, explore paths from interview. Store results with `viking_store_scan`. |
| 6 | `@dependency-analyzer` | Relationship mapping -- trace connections between discovered services, identify external dependencies, build a dependency graph. |
| 7 | `@decomposition-planner` | Microservice design -- propose container groupings based on service boundaries and dependencies, with rationale for each grouping decision. |
| 8 | `@config-generator` | Dockerfiles + manifests -- generate Dockerfiles, Kubernetes Deployments, Services, ConfigMaps, and OpenShift-specific resources for each container. |
| 9 | `@validator` | Final review & fixes -- validate every generated artifact (Dockerfile best practices, manifest schema, image references, port consistency), report PASS/WARN/FAIL. |

**Step 10**: Final review and completion. Present the full results to the user.
Call `viking_commit_session` to finalize the migration record.

---

## Progress Tracking

Maintain a top-level task list and update it as work progresses. Use this format:

```
[completed]   Interview & user direction
[completed]   Connect to target
[in_progress] VM scanning
    [completed]   Detect OS (RHEL 8.9)
    [completed]   Fingerprint scan (found: nginx, postgres, redis)
    [in_progress] Exploring /opt/acme/ per user hint
    [pending]     Compile scan summary
    [pending]     Store in Viking
[pending]     User review of scan
[pending]     Dependency analysis
[pending]     Decomposition planning
[pending]     Config generation
[pending]     Validation
[pending]     Final review
```

Display this task list whenever the user asks for status, and after completing each
major step.

---

## Output Files

### analysis-report.md (incremental)

Write sections incrementally to `output/analysis-report.md` as each agent completes:

| Sections | Written by | Content |
|---|---|---|
| 1. Executive Summary | vm-scanner | High-level overview of the VM and its workloads |
| 2. System Profile | vm-scanner | OS, kernel, packages, disk usage |
| 3. Discovered Services | vm-scanner | Every detected service with ports, configs, and data paths |
| 4. Stack Assessment | vm-scanner | Detected application stacks and frameworks |
| 5. Dependency Map | dependency-analyzer | Service-to-service and external dependency relationships |
| 6. Containerization Recommendations | decomposition-planner | Proposed container groupings with rationale |
| 7. Warnings & Considerations | validator | Issues, risks, and recommendations |

### Other output files

| File | Description |
|---|---|
| `output/interview-summary.md` | Structured interview answers |
| `output/dependency-graph.json` | Machine-readable dependency graph |
| `output/decomposition-plan.md` | Full decomposition rationale and design decisions |
| `output/deploy/{container-name}/` | Dockerfiles and Kubernetes/OpenShift manifests per container |
| `output/validation-report.md` | PASS/WARN/FAIL results per generated artifact |

---

## Human-in-the-Loop Checkpoints

Do NOT proceed past a checkpoint without user confirmation.

| Checkpoint | What the user sees | User can... |
|---|---|---|
| After interview | Summary of understanding | Correct, add context |
| After each agent's plan | Proposed task list | Approve, modify, skip steps |
| After scan | Discovered services + confidence levels | Correct findings, add missed services |
| After dependencies | Dependency graph | Fix relationships, flag externals |
| After decomposition | Container groupings + rationale | Approve, re-group, exclude services |
| After generation | File listing + validation report | Request changes, approve |

---

## vm2micro-hints.yaml Reference

The `vm2micro-hints.yaml` file is an optional configuration file that pre-fills
interview answers to speed up the analysis. Place it in your project root before
running `vm2micro init` or before starting the workflow.

Supported fields:

- `description` — Brief description of what the VM does.
- `stack` — Primary application stack (e.g., `java`, `python`, `ruby`, `php`, `node`).
- `applications` — List of known applications, each with `name`, `path`, and `type`.
- `external_dependencies` — List of external services this VM connects to (host:port or URL).
- `exclude_from_containerization` — List of services that should NOT be containerized.
- `target_openshift_version` — Target OpenShift version (e.g., `"4.14"`).

Any field left blank or omitted will be asked during the interview phase.
