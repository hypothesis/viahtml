"""The abstract blocklist object."""

import fnmatch
import os
import re
from enum import Enum
from logging import getLogger
from urllib.parse import urlparse


class Blocklist:
    """A blocklist which URLs can be checked against.

    For details of how to change the blocklist see:
      * https://stackoverflow.com/c/hypothesis/questions/102/250

    And is downloaded locally, via supervisor using `bin/fetch-blocklist`
    """

    LOG = getLogger(__name__)

    class Reason(Enum):
        """List of reasons a blocklist can be blocked."""

        MALICIOUS = "malicious"  # Actively hostile content of some kind
        PUBLISHER_BLOCKED = "publisher-blocked"  # Content owner has asked us to block
        MEDIA_VIDEO = "media-video"  # Sites which are mostly video content
        MEDIA_AUDIO = "media-audio"  # Sites which are mostly audio content
        MEDIA_IMAGE = "media-image"  # Sites which are mostly image content
        MEDIA_MIXED = "media-mixed"  # Sites with a mixture of content
        HIGH_IO = "high-io"  # Sites with high interactivity and AJAX calls
        OTHER = "other"  # Escape hatch for poorly formatted values

        @classmethod
        def parse(cls, value):
            """Parse a value into an enum object."""
            try:
                return cls(value)
            except ValueError:
                return cls.OTHER

    # viahtml is ok with video, as far as we can tell
    PERMITTED = (Reason.MEDIA_VIDEO,)

    def __init__(self, filename):
        self.LOG.debug("Monitoring blocklist file '%s'", filename)

        self._filename = filename
        self._last_modified = None
        self.domains = {}
        self.patterns = {}

        self._refresh()

    def is_blocked(self, url):
        """Get the blocked reason for a URL, or False if it's not blocked."""
        self._refresh()

        domain = self._domain(url)
        blocked = self.domains.get(domain)
        if blocked:
            return blocked

        for pattern, reason in self.patterns.items():
            if pattern.match(domain):
                return reason

        return False

    def clear(self):
        """Remove all domains from the blocklist."""
        self.domains, self.patterns = {}, {}

    def add_domain(self, domain, reason):
        """Add a domain (or domain pattern) to the blocklist."""

        reason = Blocklist.Reason.parse(reason)
        if reason in self.PERMITTED:
            # This is listed as blocked, but this service can actually
            # serve this type without incident
            return

        if "*" in domain:
            # Convert a string with '*' wildcards into a regex
            pattern = re.compile(fnmatch.translate(domain), re.IGNORECASE)
            self.patterns[pattern] = reason
        else:
            self.domains[domain] = reason

    @classmethod
    def _domain(cls, url):
        parsed_url = urlparse(url)

        if not parsed_url.scheme:
            parsed_url = urlparse(f"http://{url.lstrip('/')}")

        return parsed_url.hostname

    def _refresh(self):
        if self._file_changed:
            self.LOG.debug("Reloading blocklist file")

            self.clear()
            for domain, reason in self._parse(self._filename):
                self.add_domain(domain, reason)

    @property
    def _file_changed(self):
        if not os.path.exists(self._filename):
            self.LOG.warning("Cannot find blocklist file '%s'", self._filename)
            return False

        last_modified = os.stat(self._filename).st_mtime
        if last_modified != self._last_modified:
            self._last_modified = last_modified
            return True

        return False

    LINE_PATTERN = re.compile(r"^(\S+)\s+(\S+)(?:\s*#.*)?$")

    @classmethod
    def _parse(cls, filename):
        with open(filename) as handle:
            for line in handle:
                line = line.strip()

                if not line or line.startswith("#"):
                    # Empty or comment line.
                    continue

                match = cls.LINE_PATTERN.match(line)
                if match:
                    domain, reason = match.group(1), match.group(2)
                else:
                    cls.LOG.warning("Cannot parse blocklist file line: '%s'")
                    continue

                yield domain, reason
