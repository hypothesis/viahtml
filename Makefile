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

# Tell make how to compile requirements/*.txt files.
#
# `touch` is used to pre-create an empty requirements/%.txt file if none
# exists, otherwise tox crashes.
#
# $(subst) is used because in the special case of making requirements.txt we
# actually need to touch dev.txt not requirements.txt and we need to run
# `tox -e dev ...` not `tox -e requirements ...`
#
# $(basename $(notdir $@))) gets just the environment name from the
# requirements/%.txt filename, for example requirements/foo.txt -> foo.
requirements/%.txt: requirements/%.in
	@touch -a $(subst requirements.txt,dev.txt,$@)
	@tox -qe $(subst requirements,dev,$(basename $(notdir $@))) --run-command 'pip --quiet --disable-pip-version-check install pip-tools'
	@tox -qe $(subst requirements,dev,$(basename $(notdir $@))) --run-command 'pip-compile --allow-unsafe --quiet $(args) $<'

# Inform make of the dependencies between our requirements files so that it
# knows what order to re-compile them in and knows to re-compile a file if a
# file that it depends on has been changed.
requirements/dev.txt: requirements/requirements.txt
requirements/tests.txt: requirements/requirements.txt
requirements/functests.txt: requirements/requirements.txt
requirements/lint.txt: requirements/tests.txt requirements/functests.txt

# Add a requirements target so you can just run `make requirements` to
# re-compile *all* the requirements files at once.
#
# This needs to be able to re-create requirements/*.txt files that don't exist
# yet or that have been deleted so it can't just depend on all the
# requirements/*.txt files that exist on disk $(wildcard requirements/*.txt).
#
# Instead we generate the list of requirements/*.txt files by getting all the
# requirements/*.in files from disk ($(wildcard requirements/*.in)) and replace
# the .in's with .txt's.
.PHONY: requirements requirements/
requirements requirements/: $(foreach file,$(wildcard requirements/*.in),$(basename $(file)).txt)

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
	    -e "CHECKMATE_API_KEY=dummy-key" \
	    -e "CHECKMATE_URL=https://qa-checkmate.hypothes.is" \
	    -e "NEW_RELIC_LICENSE_KEY=$(NEW_RELIC_LICENSE_KEY)" \
	    -e "NEW_RELIC_ENVIRONMENT=dev" \
	    -e "NEW_RELIC_APP_NAME=viahtml (dev)" \
	    -e "VIA_ALLOWED_REFERRERS=localhost:9083" \
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
	@docker compose run --rm --service-ports nginx-proxy

.PHONY: web
web:
	@tox -qe dev --run-command 'uwsgi conf/development.ini'

.PHONY: python
python:
	@./bin/install-python

DOCKER_TAG = dev
