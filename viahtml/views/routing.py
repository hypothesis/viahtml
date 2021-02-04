"""Handle requests from the root for routing."""
from http import HTTPStatus


class RoutingView:
    """A view for routing content (by handing it off to Via proper)."""

    # Cache control values lifted from Via route_by_content for the values it
    # returns. I figure we are good to match them.
    MAX_AGE = 300
    STALE_WHILE_REVALIDATE = 86400

    def __init__(self, routing_host):
        """Create a view for routing requests to present content.

        Currently we don't do routing ourselves, but just pass it off to the
        main Via component to do for us.

        :param routing_host: The host which will actually do the routing
        """
        self._routing_host = routing_host

    def __call__(self, context):
        """Redirect to the content based routing service if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        if context.path != "/":
            return None

        location = f"{self._routing_host.rstrip('/')}/"
        cache_control = ", ".join(
            [
                "public",
                f"max-age={self.MAX_AGE}",
                f"stale-while-revalidate={self.STALE_WHILE_REVALIDATE}",
            ]
        )

        return context.make_response(
            HTTPStatus.TEMPORARY_REDIRECT,
            headers={"Location": location, "Cache-Control": cache_control},
        )
