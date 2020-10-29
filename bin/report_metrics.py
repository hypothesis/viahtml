"""Collect stats from uWSGI and send them to New Relic."""

import logging
import sys
from time import sleep

import newrelic.agent
from pkg_resources import resource_filename

from viahtml.stats import UWSGINewRelicStatsGenerator

METRICS_INTERVAL = 60
LOG = logging.getLogger(__name__)
# If you set this to DEBUG, you get a lot of New Relic info in there, but it
# can be useful locally
logging.basicConfig(stream=sys.stdout, level=logging.INFO)


def _report_stats():
    # Read metrics from the stats end-point of uWSGI

    newrelic.agent.initialize(
        config_file=resource_filename("viahtml", "../conf/newrelic.ini")
    )
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
