"""uWSGI -> New Relic metrics collection logic."""

from collections import Counter, defaultdict
from logging import getLogger

import requests
from requests import RequestException

LOG = getLogger(__name__)


class UWSGINewRelicStatsGenerator:
    """A callable which returns stats from uWSGI stats for New Relic."""

    # Mappings from various parts of the JSON structure we get back from
    # uWSGI stats end-point to some suitable metrics names for New Relic
    ROOT_STATS = {
        "load": "System/Load",
        "listen_queue": "Queue/Listen/Size",
        "listen_queue_errors": "Queue/Listen/Errors",
        "signal_queue": "Queue/Signal/Size",
    }

    WORKER_STATS = {
        "avg_rt": "Worker/AverageResponseTime[ms]",
        "requests": "Worker/Request/Total",
        "exceptions": "Worker/Request/Failed",
        "harakiri_count": "Worker/Count/Killed",
        "running_time": "Worker/UpTime[ms]",
        "rss": "Worker/Memory/Resident[kiloBytes]",
        "vsz": "Worker/Memory/Virtual[kiloBytes]",
    }
    # Don't include zeros in these numbers as they reflect the worker being
    # inactive and artificially bring down the average
    WORKER_PRUNE_ZEROS = ("avg_rt", "running_time", "rss", "vsz")
    WORKER_SCALE_STATS = {
        # From micro-seconds to milliseconds
        "avg_rt": 1 / 1000,
        "running_time": 1 / 1000,
        # From bytes to kilobytes
        "rss": 1 / 1000,
        "vsz": 1 / 1000,
    }

    SOCKET_STATS = {
        "queue": "Queue/Socket/Size",
        "max_queue": "Queue/Socket/Max",
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
            raw_stats = requests.get(url=self._stats_endpoint, timeout=1).json()
        except RequestException as err:
            LOG.debug("Stats collection from uWSGI failed with error: %s", err)

            yield "Alive/App", 0
            return

        yield "Alive/App", 1

        # General metrics
        for key, stat_name in self.ROOT_STATS.items():
            yield stat_name, raw_stats[key]

        # Socket metrics
        yield from self._stats_from_items(
            raw_stats["sockets"], stat_mapping=self.SOCKET_STATS
        )

        yield from self._get_worker_stats(raw_stats)

    def _get_worker_stats(self, raw_stats):
        workers = raw_stats["workers"]
        accepting_workers = [worker for worker in workers if worker["accepting"]]

        status = Counter()
        for worker in workers:
            status[f"Worker/Count/{worker['status'].title()}"] += 1

        for metric, value in status.items():
            yield metric, value

        yield "Worker/Count/Accepting", len(accepting_workers)
        yield "Worker/Count/Max", len(workers)

        yield from self._stats_from_items(
            accepting_workers,
            stat_mapping=self.WORKER_STATS,
            prune_zero=self.WORKER_PRUNE_ZEROS,
            scale_stats=self.WORKER_SCALE_STATS,
        )

    @classmethod
    def _stats_from_items(cls, items, stat_mapping, prune_zero=None, scale_stats=None):
        """Map a list of dicts into a set of stats.

        :param items: Data items to map
        :param stat_mapping: Mapping from keys to New Relic metric name
        :param prune_zero: Remove zeros from these keys
        :param scale_stats: Scale these stats by the given number
        """
        stats = defaultdict(list)

        # Turn the individual dicts into a single dict with lists of values
        for item in items:
            for key, stat_name in stat_mapping.items():
                value = item[key]
                if not value and prune_zero and key in prune_zero:
                    continue

                if scale_stats and key in scale_stats:
                    # Give two decimal places of accuracy
                    value = int(100 * value * scale_stats[key]) / 100

                stats[stat_name].append(value)

        # Summarise those lists of values
        for stat_name, values in stats.items():
            yield stat_name, {
                "total": sum(values),
                "count": len(values),
                "min": min(values),
                "max": max(values),
                # Squash this to the nearest int for repeatability in the tests
                # It'll be close enough for metrics purposes
                "sum_of_squares": int(sum(value**2 for value in values)),
            }
