Via HTML
========

A proxy that serves up third party HTML pages with the
[Hypothesis client](https://github.com/hypothesis/client) embedded, so you can
annotate them.

Installing Via HTML in a development environment
------------------------------------------------

### You will need

* Via HTML integrates with h and the Hypothesis client, so you will need to
  set up development environments for each of those before you can develop Via:

  * https://h.readthedocs.io/en/latest/developing/install/
  * https://h.readthedocs.io/projects/client/en/latest/developers/developing/

* [Git](https://git-scm.com/)

* [pyenv](https://github.com/pyenv/pyenv)
  Follow the instructions in the pyenv README to install it.
  The Homebrew method works best on macOS.

### Clone the git repo

    git clone https://github.com/hypothesis/viahtml.git

This will download the code into a `viahtml` directory in your current working
directory. You need to be in the `viahtml` directory from the remainder of the
installation process:

    cd viahtml

### Start the development server

    make dev

The first time you run `make dev` it might take a while to start because it'll
need to install the application dependencies and build the assets.

This will start NGINX running on http://localhost:9085 and reverse proxying to
UWSGI running the app. If you make changes to the app, you will need to restart
it.

**That's it!** You’ve finished setting up your Via HTML development environment. 
Run `make help` to see all the commands that are available for running the tests,
linting, code formatting, etc.

Configuration
-------------

Environment variables:

| Name | Effect | Example |
|------|--------|---------|
| `CHECKMATE_URL`       | The URL of the URL checking service       | `https://some-aws-machine` |
| `CHECKMATE_API_KEY`   | API key to authenticate with checkmate    | `dev_api_key` |
| `CHECKMATE_IGNORE_REASONS`   | Ignored reasons on checkmate detections    | `reason1,reason2` |
| `VIA_DEBUG`           | Enable debugging logging in dev           | `1` |
| `VIA_H_EMBED_URL`     | Hypothesis client URL                     | `https://cdn.hypothes.is/hypothesis` |
| `VIA_IGNORE_PREFIXES` | Prefixes not to proxy                     | `https://hypothes.is/,https://qa.hypothes.is/` |
| `VIA_ROUTING_HOST`    | The host to perform content based routing | `https://via3.hypothes.is` |
| `VIA_SECRET`          | Secret used for checking signed URLs      | `a_very_long_random_string` |
| `VIA_DISABLE_AUTHENTICATION` | Disable auth for dev purposes      | `false` |
| `VIA_ENABLE_REDIRECT_SIGNING` | Enable signing of proxied redirect locations | `false` |


For details of changing the blocklist see:

 * https://stackoverflow.com/c/hypothesis/questions/102/250

Architecture
------------

Via HTML is composed of three compoments:

 * NGINX running on port 9085
 * UWSGI running a `pywb` based application
 * A docker container running `supervisor` to run the other two parts
 
The UWSGI app runs using a binary protocol, which means you can't directly
contact it using a browser.

Static content is served directly from NGINX after being built using 
`make build`. This should happen for you automatically on first run. But if
you change the content you may want to re-run it.
