# vm2micro

AI-powered VM-to-microservice migration tool for OpenShift. Connects to a Linux VM (via disk image, local directory, or SSH), analyzes its services and dependencies, designs a microservice decomposition, and generates container artifacts (Dockerfiles + OpenShift manifests).

vm2micro works as an [MCP server](https://modelcontextprotocol.io/) for [Claude Code](https://docs.anthropic.com/en/docs/claude-code), providing 17 tools that let AI agents inspect a VM's filesystem, detect services, map dependencies, and generate migration output.

## How it works

```
Linux VM (disk image / SSH / directory)
    |
    v
vm2micro MCP Server (17 tools)
    |
    v
Claude Code + 5 Custom Agents
    |
    +-- vm-scanner          -> discovers OS, services, stacks
    +-- dependency-analyzer -> maps service relationships
    +-- decomposition-planner -> designs container groupings
    +-- config-generator    -> produces Dockerfiles + manifests
    +-- validator           -> reviews everything for correctness
    |
    v
output/deploy/  (Dockerfiles, Deployments, Services, Routes, ConfigMaps)
```

## Quick start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- **For disk image analysis:** `python3-libguestfs` (system package, not pip-installable)
  - Fedora/RHEL: `sudo dnf install python3-libguestfs`
  - Ubuntu/Debian: `sudo apt install python3-guestfs`

### Install

```bash
# Install from GitHub
uv tool install git+https://github.com/JonahSussman/vm2micro.git

# Or from source
git clone https://github.com/JonahSussman/vm2micro.git
cd vm2micro
uv tool install .

# Update to latest
uv tool upgrade vm2micro

# Uninstall
uv tool uninstall vm2micro
```

### Set up a migration project

```bash
mkdir my-migration && cd my-migration
git init

# Scaffold agents, workflow, and hints file
vm2micro init

# Register MCP server with Claude Code (writes .mcp.json in project dir)
claude mcp add --transport stdio --scope project vm2micro -- vm2micro-server
```

This creates:
- `CLAUDE.md` - orchestration workflow for Claude Code
- `.claude/agents/` - 5 custom agent definitions
- `vm2micro-hints.yaml` - optional pre-filled context about the VM

### Run the migration

Start Claude Code in your migration project directory. The `CLAUDE.md` workflow guides it through an interview phase, then dispatches agents sequentially to analyze the VM and generate container artifacts.

```bash
# Point at a disk image
claude "Connect to /path/to/vm-disk.qcow2 and analyze it for migration to OpenShift"

# Or SSH into a live VM
claude "Connect to ssh://admin@10.0.1.50 and analyze it for migration to OpenShift"

# Or a local directory (useful for testing with fixtures)
claude "Connect to ./tests/fixtures/lamp-rhel and analyze it for migration to OpenShift"
```

## Connection backends

| Backend | Target format | Use case |
|---------|--------------|----------|
| **Local directory** | `/path/to/rootfs` | Testing, extracted filesystem snapshots |
| **libguestfs** | `*.qcow2`, `*.vmdk`, `*.raw` | Disk image analysis (no VM needed) |
| **SSH** | `ssh://user@host` | Live VM inspection |
| **Cloud disk** | *(stub)* | Future: cloud provider disk APIs |

## MCP tools

| Tool | Description |
|------|-------------|
| `connect` | Connect to a VM target |
| `disconnect` | Disconnect and clean up |
| `ssh_exec` | Run a safe command over SSH |
| `detect_os` | Detect OS and distribution |
| `scan_services` | Fingerprint running services |
| `detect_stack_patterns` | Identify known stacks (LAMP, ELK, etc.) |
| `read_file` | Read a file from the VM |
| `list_dir` | List directory contents |
| `glob_files` | Search files by pattern |
| `find_config_files` | Find config files for a service |
| `list_systemd_units` | List systemd unit files |
| `list_cron_jobs` | Parse crontab entries |
| `list_packages` | List installed packages |
| `list_open_ports` | Detect port bindings |
| `get_disk_usage` | Get disk usage stats |
| `viking_store_scan` | Store scan results |
| `viking_commit_session` | Finalize migration record |

## Service detection

vm2micro detects 15 services across 5 categories:

- **Web servers:** nginx, apache
- **Databases:** postgresql, mysql, redis, mongodb
- **App servers:** tomcat, gunicorn, puma, pm2
- **Message queues:** rabbitmq, kafka
- **Search/monitoring:** elasticsearch, logstash, kibana

It also recognizes 11 stack patterns (LAMP, LEMP, Django, Rails, Java/Tomcat, ELK, etc.) to provide higher-level architectural context.

## Hints file

Optionally pre-fill `vm2micro-hints.yaml` to skip interview questions:

```yaml
description: "Main web application server"
stack: "java"
applications:
  - name: "acme-webapp"
    path: "/opt/acme/"
    type: "java-war"
external_dependencies:
  - "redis.prod.internal:6379"
exclude_from_containerization:
  - "monitoring-agent"
target_openshift_version: "4.14"
```

## Running without installing

If you don't want to install vm2micro as a tool, you can run everything directly from the repo:

```bash
git clone https://github.com/JonahSussman/vm2micro.git
cd vm2micro

# Create a migration project
mkdir /tmp/my-migration && cd /tmp/my-migration
git init

# Scaffold using uv run --project
uv run --project /path/to/vm2micro vm2micro init

# Register MCP server pointing at the repo
claude mcp add --transport stdio --scope project vm2micro -- \
  uv run --project /path/to/vm2micro vm2micro-server

# Start Claude Code
claude
```

## Development

```bash
git clone https://github.com/JonahSussman/vm2micro.git
cd vm2micro

# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v

# Type check
uv run mypy src/vm2micro/

# Build
uv build
```

## License

Apache-2.0
