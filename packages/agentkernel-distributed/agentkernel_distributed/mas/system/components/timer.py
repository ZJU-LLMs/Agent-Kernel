"""System timer actor that tracks simulation ticks and wall-clock durations."""

import datetime
from typing import List

import ray

from ....toolkit.logger import get_logger
from ....types.configs.system import TimerConfig
from .base import SystemComponent

logger = get_logger(__name__)

__all__ = ["Timer"]


@ray.remote
class Timer(SystemComponent):
    """Track simulation ticks and their corresponding durations."""

    def __init__(self, **kwargs: int) -> None:
        """
        Initialize the timer with the provided configuration.

        Args:
            **kwargs (int): Fields used to construct a `TimerConfig`.
        """
        super().__init__(**kwargs)
        self.config = TimerConfig(**kwargs)

        self._start_tick: int = self.config.start_tick

        self._current_tick = self._start_tick
        self.timeout_ticks: int = self.config.timeout_ticks

        start_timestamp = datetime.datetime.now(datetime.timezone.utc)
        self._tick_timestamps: List[datetime.datetime] = [start_timestamp]

        logger.info(
            f"Timer Actor initialized at {start_timestamp.isoformat()} with config: {self.config.model_dump_json()}"
        )

    async def post_init(self, *args, **kwargs) -> None:
        """Run post-initialization tasks."""
        pass

    def get_tick(self) -> int:
        """
        Return the current simulation tick.

        Returns:
            int: Current tick number.
        """
        return self._current_tick

    def set_tick(self, tick: int) -> None:
        """
        Set the current simulation tick to a specific value, rolling back
        timestamp history to that point.

        Args:
            tick (int): Tick number to set as the current tick. Must be within
                the range [0, current_tick].

        Raises:
            ValueError: Raised when the requested tick is negative or
                        greater than the current tick (out of recorded range).
        """
        if not (0 <= tick <= self._current_tick):
            raise ValueError(
                f"Can only set tick to a value between 0 and the " f"current tick ({self._current_tick}). Got {tick}."
            )

        if tick == self._current_tick:
            return

        self._current_tick = tick
        self._tick_timestamps = self._tick_timestamps[: (self._current_tick - self._start_tick) + 1]

        logger.info(f"Timer state restored to tick {tick} at " f"{self._tick_timestamps[-1].isoformat()}")

    def add_tick(self, duration_seconds: float) -> None:
        """
        Advance the timer by one tick and record its elapsed duration.

        Args:
            duration_seconds (float): Wall-clock seconds spent completing the tick.

        Raises:
            ValueError: Raised when a negative duration is provided.
        """
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be a non-negative number.")

        last_timestamp = self._tick_timestamps[-1]
        new_timestamp = last_timestamp + datetime.timedelta(seconds=duration_seconds)
        self._tick_timestamps.append(new_timestamp)

        self._current_tick += 1

    def get_timestamp_for_tick(self, tick: int) -> str:
        """
        Return the timestamp recorded at the end of the specified tick.

        Args:
            tick (int): Tick number to look up (0 represents the initial timestamp).

        Returns:
            str: ISO-8601 timestamp for the requested tick.

        Raises:
            ValueError: Raised when the requested tick is out of range.
        """
        if not (0 <= tick <= self._current_tick):
            raise ValueError(f"Tick {tick} is out of the recorded range [0, {self._current_tick}].")

        return self._tick_timestamps[tick].isoformat()

    def get_duration_of_tick(self, tick: int) -> float:
        """
        Return the duration of a previously recorded tick.

        Args:
            tick (int): Tick number to inspect (must be >= 1).

        Returns:
            float: Duration of the tick in seconds.

        Raises:
            ValueError: Raised when the requested tick is out of range.
        """
        if not (1 <= tick <= self._current_tick):
            raise ValueError(f"Can only get duration for recorded ticks in range [1, {self._current_tick}].")

        duration_timedelta = self._tick_timestamps[tick] - self._tick_timestamps[tick - 1]
        return duration_timedelta.total_seconds()

    async def close(self) -> None:
        """Placeholder close hook to maintain a consistent interface."""
        return None
