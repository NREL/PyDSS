
from collections import deque
import logging

import numpy as np
import pandas as pd


logger = logging.getLogger(__name__)


class CircularBufferHelper:
    def __init__(self, window_size):
        self._buf = deque(maxlen=window_size)
        self._window_size = window_size

    def __len__(self):
        return len(self._buf)

    def append(self, val):
        self._buf.append(val)

    def average(self):
        assert self._buf
        if isinstance(self._buf[0], list):
            return pd.DataFrame(self._buf).rolling(self._window_size).mean().values
        if len(self._buf) < self._window_size:
            return np.NaN
        return sum(self._buf) / len(self._buf)


class TimerStats:
    """Tracks timer stats."""
    def __init__(self, label):
        self._label = label
        self._count = 0
        self._max = 0.0
        self._min = None
        self._avg = 0.0
        self._total = 0.0

    def get_stats(self):
        """Get the current stats summary.

        Returns
        -------
        dict

        """
        avg = 0 if self._count == 0 else self._total / self._count
        return {
            "min": self._min,
            "max": self._max,
            "total": self._total,
            "avg": avg,
            "count": self._count,
        }

    def log_stats(self):
        """Log a summary of the stats."""
        if self._count == 0:
            logger.info("No stats have been recorded for %s.", self._label)
            return

        x = self.get_stats()
        text = "total={:.3f}s avg={:.3f}ms max={:.3f}ms min={:.3f}ms count={}".format(
            x["total"], x["avg"] * 1000, x["max"] * 1000, x["min"] * 1000, x["count"]
        )
        logger.info("TimerStats summary: %s: %s", self._label, text)

    def update(self, duration):
        """Update the stats with a new timing."""
        self._count += 1
        self._total += duration
        if duration > self._max:
            self._max = duration
        if self._min is None or duration < self._min:
            self._min = duration
