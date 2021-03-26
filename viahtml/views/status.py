"""The status end-point for health checks."""


class StatusView:
    """Status end-point."""

    def __call__(self, context):
        """Provide a status response if required.

        :param context: Context object relating to this call
        :return: An iterator of content if required or None
        """
        if context.path.rstrip("/") != "/_status":
            # We don't want to handle this call
            return None

        return context.make_json_response(
            {"status": "okay"}, headers={"Cache-Control": "no-cache"}
        )
