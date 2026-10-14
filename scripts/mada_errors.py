#!/usr/bin/env python3

"""Base class of the errors that stop a DAQ run in a controlled way."""


class MadaError(RuntimeError):
    """A DAQ failure that is already described by its message (no traceback
    is needed)."""
