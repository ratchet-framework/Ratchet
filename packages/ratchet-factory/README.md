# ratchet-factory

Scaffold and generate agents and modules for the [Ratchet framework](https://getratchet.dev).

## Install

```bash
pip install ratchet-factory
```

## Usage

### Create a new agent

```bash
ratchet init my-agent
```

Creates a ready-to-run agent with config, trust tiers, guardrails, incident directory, backlog, and entry point script.

### Create a new module

```bash
ratchet new module disk-monitor --description "Monitor disk usage and alert on thresholds"
```

Creates a new `ratchet-*` package with pyproject.toml, RatchetModule implementation, and README.

## License

MIT
