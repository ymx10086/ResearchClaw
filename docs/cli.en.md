# CLI (Command Line Interface)

ResearchClaw provides CLI tools for initialization, startup, and management.

## Commands

```bash
researchclaw <command> [options]
```

## Command Reference

### `init`

Initialize the working directory:

```bash
researchclaw init             # Interactive init
researchclaw init --defaults  # Init with defaults
```

### `app`

Start the ResearchClaw application:

```bash
researchclaw app                    # Start
researchclaw app --port 9090        # Specify port
researchclaw app --host 0.0.0.0     # Specify host
```

### `skills`

Manage Skills:

```bash
researchclaw skills list              # List installed skills
researchclaw skills install <url>     # Install skill from GitHub
researchclaw skills uninstall <name>  # Uninstall skill
```

### `config`

Manage configuration:

```bash
researchclaw config show              # Show config
researchclaw config set <key> <value> # Set a config value
```

### `version`

Show version info:

```bash
researchclaw version
```

## Global Options

| Option | Description |
|--------|-------------|
| `--working-dir` | Specify working directory |
| `--verbose` | Show verbose logging |
| `--help` | Show help |
