# =============================================================
# TTL #184 demo stack: ACS 26.3 pre-release + ADW 8.1 pre-release + Search Enterprise
# =============================================================
# compose.yaml        pristine copy of acs-deployment docker-compose/pre-release-compose.yaml
# compose.ttl184.yaml audit, download audit policy, cascading dictionaries, STOMP, search 5.10.0-A.6,
#                     unused services off
#
#   make check   Is the laptop ready? (Docker, quay.io login, free ports, memory)
#   make up      Start the stack and wait until the repository answers
#   make seed    Load the demo users, site, folders, files and dictionaries (../seed.py)
#   make urls    Print the demo URLs
#   make cli     Build the ACS-CLI Go binary from a local copy in ../acs-cli (not public)
#   make stop | start | down | ps | logs
#   make reset CONFIRM=yes   Remove the containers AND the data volumes [DESTRUCTIVE]
#
# Data lives in Docker volumes of the project ttl184-demo. `down` keeps them; only `reset` deletes them.
# =============================================================

PROJECT := ttl184-demo
DC := docker compose -p $(PROJECT) -f compose.yaml -f compose.ttl184.yaml

unexport COMPOSE_FILE COMPOSE_PROFILES COMPOSE_PROJECT_NAME

# Host ports published by compose.yaml (kibana 5601 and sync 9090 are switched off).
PORTS := 8080 8888 5432 9200 9300 8161 5672 61616 61613 8095 8090 8099
BASE_URL := http://localhost:8080
PROBE := $(BASE_URL)/alfresco/api/-default-/public/alfresco/versions/1/probes/-ready-

.PHONY: check up seed urls cli stop start down ps logs reset

check:
	@docker info >/dev/null 2>&1 && echo "[ok] Docker is running" || { echo "[fail] Docker is not running"; exit 1; }
	@grep -q '"quay.io"' $(HOME)/.docker/config.json && echo "[ok] quay.io login found" || echo "[fail] no quay.io login (docker login quay.io)"
	@mem=$$(docker info --format '{{.MemTotal}}'); [ $$mem -gt 12000000000 ] && echo "[ok] Docker memory $$((mem/1000000000)) GB" || echo "[warn] Docker memory under 12 GB"
	@docker run --rm -v "$(CURDIR)":/x:ro alpine ls /x/compose.yaml >/dev/null 2>&1 && echo "[ok] Docker can read this folder" || echo "[fail] Docker cannot read this folder (macOS privacy settings)"
	@running=$$(docker compose -p $(PROJECT) ps -q 2>/dev/null | wc -l | tr -d ' '); \
	for p in $(PORTS); do \
	  if lsof -nP -iTCP:$$p -sTCP:LISTEN >/dev/null 2>&1 && [ "$$running" = "0" ]; then echo "[fail] port $$p is in use (another stack?)"; fi; \
	done; echo "[ok] port check done"
	@curl -sf -o /dev/null $(PROBE) && echo "[ok] repository is ready" || echo "[info] repository not running or not ready"

up:
	$(DC) up -d
	@echo "Waiting for the repository (first start takes a few minutes)..."
	@for i in $$(seq 1 60); do curl -sf -o /dev/null $(PROBE) && { echo "[ok] repository is ready"; exit 0; }; sleep 10; done; echo "[fail] repository not ready after 10 min"; exit 1

seed:
	python3 -I ../seed.py --url $(BASE_URL)

urls:
	@echo "ADW             $(BASE_URL)/workspace/"
	@echo "Control Center  $(BASE_URL)/admin/"
	@echo "REST API        $(BASE_URL)/alfresco/api/-default-/public/alfresco/versions/1/"
	@echo "API Explorer    $(BASE_URL)/api-explorer/ (if routed)"
	@echo "Traefik         http://localhost:8888/"
	@echo "Users           see ../seed.py (admin / admin for setup only)"

cli:
	$(MAKE) -C ../acs-cli go && ../acs-cli/dist/go/acs --version

stop:
	$(DC) stop

start:
	$(DC) start

down:
	$(DC) down

ps:
	$(DC) ps

logs:
	$(DC) logs -f --tail 100 $(SVC)

reset:
	@[ "$(CONFIRM)" = "yes" ] || { echo "This deletes all demo data. Run: make reset CONFIRM=yes"; exit 1; }
	$(DC) down -v
