class PackError(Exception):
    """A problem with the pack file or how tent-pack was asked to run.

    Raised for things the student or lecturer can fix; the CLI prints the
    message without a traceback.
    """
