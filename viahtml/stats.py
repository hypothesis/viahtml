"""uWSGI -> New Relic metrics collection logic."""

from collections import defaultdict
from logging import getLogger

import requests
from requests import RequestException

LOG = getLogger(__name__)


# pylint: disable=missing-yield-doc,missing-yield-type-doc


class UWSGINewRelicStatsGenerator:
    """A callable which returns stats from uWSGI stats for New Relic."""

    # Mappings from various parts of the JSON structure we get back from
    # uWSGI stats end-point to some suitable metrics names for New Relic
    ROOT_STATS = {
        "load": "System/Load",
        "listen_queue": "ListenQueue/Size",
        "listen_queue_errors": "ListenQueue/Errors",
        "signal_queue": "SignalQueue/Size",
    }

    WORKER_STATS = {
        "avg_rt": "Worker/AverageResponseTime",
        "requests": "Worker/Request/Total",
        "exceptions": "Worker/Request/Failed",
        "harakiri_count": "Worker/Killed",
        "running_time": "Worker/UpTime",
        "rss": "Worker/Memory/Resident",
        "vsz": "Worker/Memory/Virtual",
    }

    SOCKET_STATS = {
        "queue": "Socket/Queue/Size",
        "max_queue": "Socket/Queue/Max",
    }

    def __init__(self, stats_endpoint):
        """Create a callable metrics generator.

        :param stats_endpoint: The uWSGI stats end-point to call
        """
        self._stats_endpoint = stats_endpoint

    def __call__(self):
        """Generate stat name value pairs."""

        for stat_name, values in self._get_stats():
            LOG.debug("Reporting stat %s = %s", stat_name, values)
            yield f"Custom/{stat_name}", values

    def _get_stats(self):
        # General "I'm alive!" type stuff
        yield "Alive/Metrics", 1

        try:
            raw_stats = requests.get(self._stats_endpoint).json()
        except RequestException as err:
            LOG.debug("Stats collection from uWSGI failed with error: %s", err)

            yield "Alive/App", 0
            return

        yield "Alive/App", 1

        # General metrics
        for key, stat_name in self.ROOT_STATS.items():
            yield stat_name, raw_stats[key]

        # Socket metrics
        yield from self._stats_from_items(raw_stats["sockets"], self.SOCKET_STATS)

        # Worker metrics
        workers = raw_stats["workers"]
        accepting_workers = [worker for worker in workers if worker["accepting"]]

        yield "Worker/Count/Accepting", len(accepting_workers)
        yield "Worker/Count/Max", len(workers)

        yield from self._stats_from_items(accepting_workers, self.WORKER_STATS)

    @classmethod
    def _stats_from_items(cls, items, stat_mapping):
        """Map a list of dicts into a set of stats.

        :param items: Data items to map
        :param stat_mapping: Mapping from keys to New Relic metric name
        """
        stats = defaultdict(list)

        # Turn the individual dicts into a single dict with lists of values
        for item in items:
            for key, stat_name in stat_mapping.items():
                stats[stat_name].append(item[key])

        # Summarise those lists of values
        for stat_name, values in stats.items():
            yield stat_name, {
                "total": sum(values),
                "min": min(values),
                "max": max(values),
                "sum_of_squares": sum(value ** 2 for value in values),
                "count": len(values),
            }
