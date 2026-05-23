AGENT_HOME ?= $(CURDIR)/.tabula
TABULA_VERSION ?= v0.9.5
TABULA_INSTALL := $(AGENT_HOME)/bin/tabula-install
TABULA_INSTALLER_URL := https://raw.githubusercontent.com/bamanoz/tabula/$(TABULA_VERSION)/scripts/install.sh

.PHONY: agent-install agent-prepare agent-run

agent-install:
	@if [ ! -x "$(TABULA_INSTALL)" ]; then \
		token="$${GITHUB_TOKEN:-$$(gh auth token 2>/dev/null)}"; \
		[ -n "$$token" ] || { printf 'error: GITHUB_TOKEN is empty and gh auth token failed\n' >&2; exit 2; }; \
		installer="$$(mktemp -t tabula-install.XXXXXX.sh)"; \
		trap 'rm -f "$$installer"' EXIT; \
		curl -fsSL -H "Authorization: Bearer $$token" "$(TABULA_INSTALLER_URL)" -o "$$installer"; \
		TABULA_HOME="$(AGENT_HOME)" GITHUB_TOKEN="$$token" bash "$$installer" app prepare; \
	fi

agent-prepare: agent-install
	TABULA_HOME="$(AGENT_HOME)" "$(TABULA_INSTALL)" app prepare

agent-run: agent-install
	TABULA_HOME="$(AGENT_HOME)" "$(TABULA_INSTALL)" app run --foreground
