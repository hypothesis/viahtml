"""Collect stats from uWSGI and send them to New Relic."""

import logging
import sys
from time import sleep

import importlib_resources
import newrelic.agent

from viahtml.stats import UWSGINewRelicStatsGenerator

METRICS_INTERVAL = 60
LOG = logging.getLogger(__name__)
# If you set this to DEBUG, you get a lot of New Relic info in there, but it
# can be useful locally
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def _report_stats():
    # Read metrics from the stats end-point of uWSGI

    with importlib_resources.as_file(
        importlib_resources.files("viahtml") / "../conf/newrelic.ini"
    ) as config_file:
        newrelic.agent.initialize(config_file=config_file)
    newrelic.agent.register_application(timeout=5)
    application = newrelic.agent.application()

    generate_stats = UWSGINewRelicStatsGenerator(stats_endpoint="http://localhost:3033")

    while True:
        application.record_custom_metrics(generate_stats())
        sleep(METRICS_INTERVAL)


if __name__ == "__main__":
    try:
        _report_stats()
    finally:
        LOG.fatal("ViaHTML metrics collection has stopped un-expectedly")
