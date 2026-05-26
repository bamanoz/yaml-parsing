# yaml-parsing Tabula Demo

This repository is a small demonstration workspace for running a Tabula agent
from an app manifest. It keeps the Tabula install local to the repository under
`.tabula/`, which is ignored by Git.

## Files

- `tabula.app.toml` declares the Tabula app/agent to install and run.
- `Makefile` provides short commands for installing, preparing, and running the
  agent.
- `.tabula/` is the local Tabula home for this demo. It contains runtime state,
  installed distros/bundles, generated config, logs, and secrets. Do not commit
  it.

## Requirements

- macOS/Linux shell
- `gh` authenticated against GitHub, because the Tabula repositories are
  private:

```bash
gh auth login
gh auth status
```

## Install

From the repository root:

```bash
make agent-install
```

This downloads the private Tabula installer, installs Tabula into this
repository's `.tabula/`, installs the distro from `tabula.app.toml`, and creates
the initial app materialization.

## Prepare

After install, prepare the app explicitly:

```bash
make agent-prepare
```

This refreshes the app materialization using the already installed local
`.tabula/bin/tabula-install`.

## Configure Driver Provider And Secrets

After `make agent-prepare`, update these local files:

- `.tabula/config/global.toml`
- `.tabula/secrets.json`

These files are under `.tabula/`, so they are ignored by Git.

### Example `global.toml`

Use `[clients.driver]` to select the default provider and define provider
settings. The `api_key` entries below reference values stored in
`.tabula/secrets.json`.

```toml
[clients.driver]
provider = "codexsale"

[clients.driver.providers.codexsale]
type = "openai"
api_key = { source = "store", id = "driver.codexsale.api_key" }
base_url = "https://codex.sale/v1"
api = "chat_completions"
responses_state = "auto"
default_model = "gpt-5.4"
context_window = 200000

[clients.driver.providers.codexsale.models."gpt-5.4"]
effort = "medium"
reasoning_summary = "auto"

[clients.driver.providers.codexsale.models."gpt-5.5"]
effort = "high"
reasoning_summary = "auto"

[sessions]
idle_timeout = 300
poll_interval = 2

[mcp.pool]
url = ""
host = "0.0.0.0"
port = 0
```

You can add more providers the same way. For example:

```toml
[clients.driver.providers.externcash]
type = "openai"
api_key = { source = "store", id = "driver.externcash.api_key" }
base_url = "https://ai.externcashpn.cv/v1"
api = "responses"
responses_state = "auto"
default_model = "gpt-5.4"
context_window = 200000

[clients.driver.providers.externcash.models."gpt-5.4"]
effort = "medium"
```

### Example `secrets.json`

Create `.tabula/secrets.json` with API keys for the providers referenced by
`global.toml`:

```json
{
  "driver.codexsale.api_key": "sk-your-codexsale-key",
  "driver.externcash.api_key": "sk-your-externcash-key"
}
```

Set strict permissions on the secrets file:

```bash
chmod 600 .tabula/secrets.json
```

The selected provider in `global.toml` must have a matching secret in
`.tabula/secrets.json`. For example, if:

```toml
[clients.driver]
provider = "codexsale"
```

then `.tabula/secrets.json` must include:

```json
{
  "driver.codexsale.api_key": "sk-your-codexsale-key"
}
```

## Run

Start the agent in the foreground:

```bash
make agent-run
```

`make agent-run` uses `.tabula/bin/tabula-install app run --foreground`, so the
process stays attached to the terminal and can be stopped with `Ctrl+C`.

The web gateway opens in the browser automatically when it starts. If you need
to open it manually, read the local token and open the gateway URL:

```bash
token=$(cat .tabula/run/plugins/gateway-web/token)
open "http://127.0.0.1:8765/?tenant_id=code-immune-tabula-dev&token=$token"
```

## Run With Docker

The repository also includes a single-container Docker deployment. The container
runs Tabula, the installed distro, drivers, plugins, and gateway-web. This repo
is mounted into the container as `/workspace`, and `TABULA_HOME` is
`/workspace/.tabula`, so existing local config and secrets are reused.

Build and start:

```bash
GITHUB_TOKEN=$(gh auth token) UID=$(id -u) GID=$(id -g) docker compose up --build -d
```

`GITHUB_TOKEN` is required because `tabula.app.toml` installs the private Tabula
distro from GitHub. Provider API keys are still read from `.tabula/secrets.json`;
they are not passed through Docker environment variables.

Docker ports are intentionally different from the local foreground runner, so a
local agent and Docker agent can run side by side:

- `28089` -> container kernel `8089`
- `28765` -> container gateway-web `8765`

Open the Docker web gateway:

```bash
token=$(cat .tabula/run/plugins/gateway-web/token)
open "http://127.0.0.1:28765/?token=$token"
```

Force a fresh reinstall from git sources:

```bash
docker compose down
rm -rf .tabula/cache/git \
  .tabula/tenants/code-immune-tabula-dev/plugins/gateway-web \
  .tabula/plugins/gateway-web \
  .tabula/run/plugins/gateway-web
GITHUB_TOKEN=$(gh auth token) UID=$(id -u) GID=$(id -g) \
  TABULA_DOCKER_REINSTALL=1 docker compose up --build -d --force-recreate
```

Stop the Docker agent:

```bash
docker compose down
```

## Reset

To remove the local install and start from scratch:

```bash
rm -rf .tabula tabula.app.lock
make agent-prepare
```
