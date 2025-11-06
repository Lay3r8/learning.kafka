"""
Helper functions for integration tests.
"""
import time


def wait_for_event_processing(seconds: float = 1.0) -> None:
    """
    Helper function to wait for event processing.
    Used after sending commands to allow time for events to propagate.
    """
    time.sleep(seconds)
