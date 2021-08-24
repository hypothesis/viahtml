.PHONY: help
help:
	@echo "make help              Show this help message"
	@echo "make dev               Run the app in the development server"
	@echo 'make services          Run the services that `make dev` requires'
	@echo 'make build             Prepare the build files'
	@echo "make lint              Run the code linter(s) and print any warnings"
	@echo "make format            Correctly format the code"
	@echo "make checkformatting   Crash if the code isn't correctly formatted"
	@echo "make test              Run the unit tests"
	@echo "make coverage          Print the unit test coverage report"
	@echo "make functests         Run the functional tests"
	@echo "make sure              Make sure that the formatter, linter, tests, etc all pass"
	@echo "make update-pdfjs      Update our copy of PDF-js"
	@echo "make pip-compile       Compile requirements.in to requirements.txt"
	@echo "make upgrade-package   Upgrade the version of a package in requirements.txt."
	@echo '                       Usage: `make upgrade-package name=some-package`.'
	@echo "make docker            Make the app's Docker image"
	@echo "make run-docker        Run the app's Docker image locally."

.PHONY: dev
dev: python
	@tox -qe dev

.PHONY: services
services:
	@true

.PHONY: lint
lint: python
	@tox -qe lint

.PHONY: format
format: python
	@tox -qe format

.PHONY: checkformatting
checkformatting: python
	@tox -qe checkformatting

.PHONY: test
test: python
	@tox -q

.PHONY: coverage
coverage: python
	@tox -qe coverage

.PHONY: functests
functests: python
	@tox -qe functests

.PHONY: sure
sure: checkformatting lint test coverage functests

.PHONY: upgrade-package
upgrade-package: python
	@tox -qe pip-compile -- --upgrade-package $(name)

.PHONY: build
build: python
	@tox -qe build

.PHONY: docker
docker:
	@git archive --format=tar HEAD | docker build -t hypothesis/viahtml:$(DOCKER_TAG) -


.PHONY: run-docker
run-docker:
	@docker run \
	    -it --rm \
	    -e "NEW_RELIC_LICENSE_KEY=$(NEW_RELIC_LICENSE_KEY)" \
	    -e "NEW_RELIC_ENVIRONMENT=dev" \
	    -e "NEW_RELIC_APP_NAME=viahtml (dev)" \
	    -e "VIA_H_EMBED_URL=https://cdn.hypothes.is/hypothesis@qa" \
	    -e "VIA_IGNORE_PREFIXES=https://qa.hypothes.is/,https://cdn.hypothes.is/" \
	    -e "VIA_BLOCKLIST_URL=https://hypothesis-via.s3-us-west-1.amazonaws.com/via-blocklist.txt" \
	    -e "VIA_BLOCKLIST_PATH=/var/lib/hypothesis/blocklist.txt" \
	    -e "VIA_ROUTING_HOST=http://localhost:9083" \
	    -e "VIA_DEBUG=1"  \
	    -p 9085:9085 \
	    --name viahtml hypothesis/viahtml:$(DOCKER_TAG)

.PHONY: nginx
nginx: python
	@tox -qe dev --run-command 'docker-compose run --rm --service-ports nginx-proxy'

.PHONY: web
web:
	@tox -qe dev --run-command 'uwsgi conf/development.ini'

.PHONY: python
python:
	@./bin/install-python

DOCKER_TAG = dev
