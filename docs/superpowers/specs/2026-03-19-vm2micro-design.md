# vm2micro: AI-Powered VM-to-OpenShift Migration Tool — Design Spec

## 1. Overview

vm2micro is a tool that uses AI to analyze a Linux VM (via disk image or SSH), identify its services and dependencies, decompose them into microservices, and generate OpenShift/Kubernetes manifests + Dockerfiles. The primary interface is Claude Code — the user has an interactive conversation where they steer the migration at every step. The tool provides an MCP server (filesystem analysis, SSH, OpenViking) and custom Claude Code agents for specialist roles.

**Key principles:**
- Static disk image analysis is the primary path; SSH is secondary
- Human-in-the-loop at every stage via natural conversation
- Hardcoded detection patterns for common stacks + AI-driven exploration for the rest
- OpenShift is the primary target platform
- Superpowers-style orchestration: interview → plan → execute → review per agent

**License:** Apache 2.0
**Repository:** Personal GitHub (JonahSussman)

## 2. Architecture

```
User ↔ Claude Code (interactive conversation)
          │
          ├── .claude/agents/          ← 5 specialist agent definitions
          │     ├── vm-scanner.md
          │     ├── dependency-analyzer.md
          │     ├── decomposition-planner.md
          │     ├── config-generator.md
          │     └── validator.md
          │
          ├── CLAUDE.md                ← Migration workflow instructions
          │
          └── MCP Server (Python/uv)  ← Tools Claude Code can call
                ├── VirtualFS layer    ← Abstracted filesystem interface
                │     ├── GuestFSBackend    (disk images via guestmount)
                │     ├── LocalPathBackend  (mounted dirs, tarballs, exports)
                │     ├── SSHBackend        (live VM access via asyncssh)
                │     └── CloudDiskBackend  (stubbed — future)
                │
                ├── Analysis tools     ← Operate against VirtualFS
                │     ├── OS detection
                │     ├── Service/package discovery
                │     ├── Config file analysis
                │     └── Detection pattern library
                │
                └── Viking tools       ← OpenViking integration (optional)
                      ├── Store scan results (L0/L1/L2)
                      └── Session commit for record-keeping
```

### Why this architecture

- **Human-in-the-loop is natural** — the user reviews and steers at every step via conversation
- **Claude Code handles orchestration** — context management, session persistence, compaction, agent dispatch
- **VirtualFS abstraction** — analysis code is backend-agnostic; disk image, local path, SSH, or cloud are transparent
- **MCP server is reusable** — standard protocol, works with Claude Code natively
- **Detection patterns live in the MCP server** — agents receive structured, pre-analyzed data and focus on reasoning

## 3. VirtualFS Interface

A read-only protocol that all analysis tools operate against:

```python
class VirtualFS(Protocol):
    async def read_file(self, path: str, max_lines: int | None = None) -> str
    async def list_dir(self, path: str) -> list[DirEntry]
    async def exists(self, path: str) -> bool
    async def glob(self, pattern: str) -> list[str]
    async def stat(self, path: str) -> FileStat
    async def read_link(self, path: str) -> str
```

Six methods. No write operations — read-only by design.

### Backends

| Backend | Input | Implementation |
|---|---|---|
| `GuestFSBackend` | Path to disk image (`.qcow2`, `.vmdk`, `.raw`, `.vdi`, `.vhdx`) | Shells out to `guestmount --ro`, delegates to `LocalPathBackend` for reads |
| `LocalPathBackend` | Path to a directory (mounted disk, extracted rootfs) | Direct `aiofiles`/`pathlib` operations |
| `SSHBackend` | `ssh://user@host` | `asyncssh` — translates each method to remote commands |
| `CloudDiskBackend` | Cloud resource identifier | Stubbed — raises `NotImplementedError` with future support message |

`GuestFSBackend` is thin — handles mount/unmount lifecycle, then wraps `LocalPathBackend` for actual file operations.

### Connection flow

```
User: "analyze /path/to/vm.qcow2"
  → Claude calls connect(target="/path/to/vm.qcow2")
  → MCP server detects file extension → GuestFSBackend
  → guestmount --ro mounts to temp dir
  → All analysis tools use VirtualFS
  → disconnect → guestunmount cleans up

User: "analyze ssh://admin@10.0.1.5"
  → SSHBackend via asyncssh

User: "analyze /mnt/exported-rootfs"
  → LocalPathBackend (directory detected)
```

## 4. Detection Pattern Library

Two-layer detection living in the MCP server (not in agents).

### Layer 1 — Service Fingerprinting

Pattern-match individual services from filesystem evidence:

```python
@dataclass
class ServiceFingerprint:
    name: str              # e.g. "nginx", "postgresql"
    category: str          # "web-server", "database", "cache", "queue", "app-server"
    version: str | None
    config_paths: list[str]
    data_paths: list[str]
    ports: list[int]
    evidence: list[str]    # what was found and where

@dataclass
class ServiceDetector:
    name: str                              # canonical name
    variants: dict[str, DistroVariant]     # keyed by distro family

@dataclass
class DistroVariant:
    package_names: list[str]      # ["httpd"] for RHEL, ["apache2"] for Debian
    service_names: list[str]      # ["httpd.service"] vs ["apache2.service"]
    config_paths: list[str]       # ["/etc/httpd/"] vs ["/etc/apache2/"]
    data_paths: list[str]
```

Detection sources (via VirtualFS):
- `/etc/systemd/system/`, `/usr/lib/systemd/system/` — unit files
- Package DB — `/var/lib/rpm/`, `/var/lib/dpkg/`, `/lib/apk/`
- Well-known paths (`/etc/nginx/`, `/etc/httpd/`, `/var/lib/postgresql/`)
- `/etc/init.d/` for SysVinit systems
- Config file contents for port bindings

Cross-distro support: detect distro first via `/etc/os-release`, then use appropriate variant for each detector. Supported families: RHEL/CentOS/Fedora (deepest coverage), Debian/Ubuntu, Alpine, SUSE.

### Layer 2 — Stack Pattern Recognition

Match combinations of fingerprints against known stack templates:

```python
@dataclass
class StackPattern:
    name: str
    services: list[str]
    relationships: list[tuple[str, str, str]]  # ("webapp", "connects_to", "database")
    decomposition_hint: str
```

Initial pattern library (~10-15 patterns):
- LAMP (Apache + PHP + MySQL)
- LEMP (Nginx + PHP + MySQL/Postgres)
- Rails (Ruby + Puma/Unicorn + Sidekiq + Redis + Postgres)
- Java/Tomcat (JDK + Tomcat + database)
- Django (Python + Gunicorn + Celery + Redis/RabbitMQ + Postgres)
- Node.js (Node + PM2 + Mongo/Postgres)
- WordPress (LAMP variant with wp-content detection)
- ELK stack
- Single database server
- Single web server (static files)

Patterns are data (Python dataclasses), not logic. Easy to extend.

### What agents receive

Agents get structured `ServiceFingerprint` and `StackPattern` results — not raw file contents. But agents also have full access to VirtualFS tools to investigate further when the patterns aren't enough.

### Discovery flow

**User direction → fingerprints → AI exploration → user correction → final picture**

## 5. User-Provided Context

Two mechanisms for the user to provide direction before and during scanning:

### Conversational (primary)

Step 0 of the workflow asks the user what they know, one question at a time. This shapes what the scanner looks for.

### vm2micro-hints.yaml (optional)

For repeat or pre-planned runs:

```yaml
description: "Main web application server"
stack: "java"
applications:
  - name: "acme-webapp"
    path: "/opt/acme/"
    type: "java-war"
  - name: "worker"
    path: "/home/deploy/worker/"
    type: "python"
external_dependencies:
  - "redis.prod.internal:6379"
  - "api.thirdparty.com"
exclude_from_containerization:
  - "monitoring-agent"
target_openshift_version: "4.14"
```

The scanner reads this before analysis and incorporates it. The interview step can be shortened if hints are provided.

## 6. MCP Server Tools

### Connection tools

| Tool | Description |
|---|---|
| `connect` | Connect to target — auto-detects type from input. Returns detected OS info. |
| `disconnect` | Unmount/disconnect, clean up |

### Analysis tools (all operate through VirtualFS)

| Tool | Description |
|---|---|
| `detect_os` | Read `/etc/os-release`, kernel info, arch — determines distro family |
| `scan_services` | Run fingerprint library, return structured results |
| `detect_stack_patterns` | Match fingerprints against known stack templates |
| `list_systemd_units` | List all systemd units (enabled/running) |
| `list_packages` | Installed packages (auto-selects RPM/dpkg/apk) |
| `read_file` | Read any file via VirtualFS |
| `list_dir` | List directory contents |
| `glob_files` | Glob pattern search |
| `find_config_files` | Search common config locations, optionally by service |
| `list_cron_jobs` | Parse crontabs for all users |
| `list_open_ports` | Parse configs for port bindings (static) or `ss` output (SSH) |
| `get_disk_usage` | Directory sizes |

### Viking tools

| Tool | Description |
|---|---|
| `viking_store_scan` | Store scan results with L0/L1/L2 tiering |
| `viking_commit_session` | Finalize session, store migration record |

## 7. Claude Code Agents

Five specialist agents defined as `.claude/agents/*.md` files with YAML frontmatter. All agents have access to all MCP tools — no artificial restrictions. Agent prompts define role and focus. Each agent is told that previous agents' results are available in conversation context and in their scratchpad folders.

### 1. vm-scanner.md

**Role:** After user provides initial direction, runs fingerprint-based scan, then explores filesystem for things patterns missed. Looks for custom systemd units, application code in non-standard locations, cron-launched services, unexpected listeners. Stores results in Viking. Outputs structured scan summary with confidence levels.

### 2. dependency-analyzer.md

**Role:** Takes scan summary and maps relationships between discovered services. Reads config files to find connection strings, socket paths, shared directories, environment variables. Outputs dependency graph (JSON) with nodes = services, edges = relationships, and flags external dependencies.

### 3. decomposition-planner.md

**Role:** Takes dependency graph and designs the microservice split. Groups services into containers, recommends base images, identifies config/data to extract. Flags poor containerization candidates. Outputs decomposition plan with container definitions, migration order, and risk assessment.

### 4. config-generator.md

**Role:** Takes decomposition plan and produces Dockerfiles + OpenShift manifests for each container. Reads original config files from the VM to extract settings. Generates Deployment, Service, Route, ConfigMap, PVC, SecurityContextConstraints. Writes to `output/deploy/`.

### 5. validator.md

**Role:** Reviews all generated artifacts. Checks: valid YAML, matching port/selector references, no plaintext secrets, non-root containers, resource limits, health checks, appropriate SCCs. Commits Viking session. Can fix issues directly. Outputs PASS/WARN/FAIL report.

## 8. Superpowers-Style Orchestration

### Interview Phase

Before any scanning:

1. Load `vm2micro-hints.yaml` if present
2. Ask the user about the VM, one question at a time:
   - What does this VM do?
   - What's the main application stack?
   - Where does the application code live?
   - Any known external dependencies?
   - Any services that should NOT be containerized?
   - Target OpenShift version / cluster constraints?
3. Summarize understanding back to user for confirmation
4. Write interview results to `output/interview-summary.md`

### Plan-Then-Execute Per Agent

Each agent follows a two-phase loop:

**Phase 1 — Plan.** Before doing any work:
- Review all prior context (interview, previous agents' results, scratchpads)
- Produce a written plan → `output/.scratchpad/{agent-name}/plan.md`
- Create tasks for each step → `output/.scratchpad/{agent-name}/tasks.md`
- Present plan to user for approval

**Phase 2 — Execute.** After user approval:
- Work through task list, updating status as it goes
- Each task: `pending` → `in_progress` → `completed`
- If blocked or uncertain, pause and ask the user
- On completion, present results with summary

**Self-assessment loop:**
```
Plan → Execute tasks → Self-assess: "Am I done?"
  ├── Yes → Present results, mark complete
  └── No  → Update plan with new tasks, continue
```

Agents iterate until satisfied, not until a fixed number of steps complete. Each agent's prompt includes self-assessment criteria (e.g., vm-scanner knows it's done when all user-mentioned locations are checked, all detected services have config/port info, no unexplored units remain).

### Progress Tracking

Each agent creates and manages its own task list. The CLAUDE.md workflow maintains a top-level task list:

```
Top-level progress:
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

### Human-in-the-Loop Checkpoints

| Checkpoint | What the user sees | User can... |
|---|---|---|
| After interview | Summary of understanding | Correct, add context |
| After each agent's plan | Proposed task list | Approve, modify, skip steps |
| After scan | Discovered services + confidence | Correct findings, add missed services |
| After dependencies | Dependency graph | Fix relationships, flag externals |
| After decomposition | Container groupings + rationale | Approve, re-group, exclude services |
| After generation | File listing + validation report | Request changes, approve |

### Agent Dispatching

Sequential — each depends on the previous: vm-scanner → dependency-analyzer → decomposition-planner → config-generator → validator.

## 9. OpenViking Integration

### MVP Scope

**In scope:**
- Within-session L0/L1/L2 tiered storage of scan results
- `viking_commit_session` to store completed migration as a record

**Deferred:**
- Cross-session pattern retrieval and learning
- Active querying of past migrations from agent prompts

### Storage

Scan results at `viking://resources/scans/{vm-id}/`:
- **L0** (~100 tokens): "RHEL 8.9, LAMP stack, 3 services detected"
- **L1** (~2k tokens): Service list with versions, ports, key config paths
- **L2** (full): Complete fingerprint data, config contents, raw evidence

### Graceful Degradation

Viking is initialized at server startup. If it fails (missing dependency, no embedding config), the MCP server logs a warning and continues. All `viking_*` tools return a helpful message ("Viking not configured — scan results stored locally as JSON fallback"). The core pipeline never blocks on Viking.

### Setup

`vm2micro install` configures Viking data at `~/.vm2micro/viking-data/`. Embedding provider set via environment variables.

## 10. Output Structure

```
output/
├── .scratchpad/                     # Agent working space
│   ├── vm-scanner/
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   └── notes.md
│   ├── dependency-analyzer/
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   └── notes.md
│   ├── decomposition-planner/
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   └── notes.md
│   ├── config-generator/
│   │   ├── plan.md
│   │   ├── tasks.md
│   │   └── notes.md
│   └── validator/
│       ├── plan.md
│       ├── tasks.md
│       └── notes.md
├── interview-summary.md
├── scan-report.md
├── dependency-graph.json
├── decomposition-plan.md
├── validation-report.md
└── deploy/
    ├── webapp/
    │   ├── Dockerfile
    │   └── openshift/
    │       ├── deployment.yaml
    │       ├── service.yaml
    │       ├── route.yaml
    │       └── configmap.yaml
    ├── postgres/
    │   ├── Dockerfile
    │   └── openshift/
    │       ├── deployment.yaml
    │       ├── service.yaml
    │       ├── pvc.yaml
    │       └── configmap.yaml
    └── redis/
        ├── Dockerfile
        └── openshift/
            ├── deployment.yaml
            ├── service.yaml
            └── pvc.yaml
```

## 11. Project Structure

```
vm2micro/
├── pyproject.toml
├── LICENSE                          # Apache 2.0
├── README.md
├── src/vm2micro/
│   ├── __init__.py
│   ├── py.typed                     # PEP 561 marker
│   ├── server.py                    # MCP server entry point (FastMCP, stdio)
│   ├── cli.py                       # vm2micro init / install (click)
│   ├── viking.py                    # OpenViking client wrapper + graceful degradation
│   ├── virtualfs/
│   │   ├── __init__.py              # VirtualFS protocol definition
│   │   ├── guestfs.py              # GuestFSBackend
│   │   ├── local.py                # LocalPathBackend
│   │   ├── ssh.py                  # SSHBackend
│   │   └── cloud.py               # CloudDiskBackend (stubbed)
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── os_detect.py            # Distro detection
│   │   ├── fingerprint.py          # Service fingerprinting engine
│   │   ├── patterns.py             # Stack pattern matching
│   │   └── detectors/
│   │       ├── __init__.py
│   │       ├── web_servers.py      # nginx, apache, caddy
│   │       ├── databases.py        # postgres, mysql, mongo, redis
│   │       ├── app_servers.py      # tomcat, gunicorn, puma, pm2
│   │       ├── queues.py           # rabbitmq, kafka, celery
│   │       └── common.py           # cron, custom systemd units
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── connection.py           # connect/disconnect
│   │   ├── analysis.py             # scan_services, detect_os, etc.
│   │   ├── filesystem.py           # read_file, list_dir, glob_files
│   │   └── viking_tools.py         # viking_store_scan, viking_commit_session
│   └── scaffolds/
│       ├── CLAUDE.md               # Migration workflow template
│       ├── vm2micro-hints.yaml     # Example hints file
│       └── agents/
│           ├── vm-scanner.md
│           ├── dependency-analyzer.md
│           ├── decomposition-planner.md
│           ├── config-generator.md
│           └── validator.md
└── tests/
    ├── conftest.py
    ├── fixtures/                    # Fake rootfs layouts for testing
    │   ├── lamp-stack/
    │   ├── rails-app/
    │   └── java-tomcat/
    ├── test_virtualfs.py
    ├── test_fingerprint.py
    ├── test_patterns.py
    └── test_tools.py
```

## 12. Dependencies

```toml
[project]
name = "vm2micro"
version = "0.1.0"
description = "AI-powered VM-to-microservice migration tool for OpenShift"
license = "Apache-2.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.18",
    "asyncssh>=2.17.0",
    "pyyaml>=6.0",
    "click>=8.0",
]

[project.optional-dependencies]
viking = ["openviking>=0.2.0"]
dev = ["mypy>=1.0", "pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
vm2micro = "vm2micro.cli:main"
vm2micro-server = "vm2micro.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Type checking: `mypy --strict` must pass. `py.typed` marker included. `VirtualFS` defined as `typing.Protocol` for structural typing.

## 13. Packaging & Installation

```bash
# One-time setup
uv tool install vm2micro              # Install MCP server + CLI globally
vm2micro install                       # Register MCP server in ~/.claude/settings.json

# Per-project setup
cd ~/migrations/webserver-01/
vm2micro init                          # Scaffolds .claude/agents/*.md + CLAUDE.md + example hints
claude                                 # Start Claude Code — MCP tools available immediately
```

`vm2micro install` adds to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "vm2micro": {
      "command": "vm2micro-server",
      "args": [],
      "env": {}
    }
  }
}
```

## 14. Implementation Order

1. **Project scaffolding** — Directory structure, `pyproject.toml`, verify `uv run vm2micro --help`
2. **VirtualFS interface + LocalPathBackend** — Protocol definition, local implementation, tests with fixture rootfs
3. **OS detection + fingerprint engine** — `os_detect.py`, `fingerprint.py`, first detectors (web servers, databases). Test against fixtures.
4. **Stack pattern matching** — `patterns.py` with initial patterns. Test against fixtures.
5. **MCP server + analysis tools** — Wire VirtualFS and analysis into FastMCP tools. Verify in Claude Code.
6. **CLI commands** — `vm2micro init` and `vm2micro install`
7. **GuestFSBackend** — guestmount wrapper, test with real disk image
8. **SSHBackend** — asyncssh implementation
9. **CloudDiskBackend stub** — NotImplementedError with helpful messages
10. **OpenViking integration** — `viking.py`, `viking_tools.py`, graceful degradation
11. **Agent prompts** — All 5 agent markdown files with plan-then-execute, self-assessment loops, progress tracking
12. **CLAUDE.md template** — Full orchestration: interview, checkpoints, progress tracking
13. **Remaining detectors** — app servers, queues, common patterns
14. **End-to-end testing** — Full migration against a test VM/image

## 15. Verification

1. `uv tool install .` — `vm2micro` and `vm2micro-server` on PATH
2. `vm2micro install` — MCP server registered
3. `vm2micro init` in a new directory — scaffolds agents + CLAUDE.md + example hints
4. `claude` in that directory — MCP server connects, tools appear
5. `mypy --strict src/` — passes
6. `pytest` — all tests pass against fixture rootfs layouts
7. Point at a test disk image → full migration workflow produces valid output
8. Point at a test VM via SSH → same workflow works
9. Verify `output/deploy/*/openshift/*.yaml` are valid with `oc apply --dry-run=client`
10. Verify Viking stores scan results (when configured) and degrades gracefully (when not)
