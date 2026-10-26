"""Small event loop and monotonic scheduler for the audio manager."""

from __future__ import annotations

import heapq
import logging
import queue
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable


LOG = logging.getLogger("audio-manager.scheduler")


@dataclass(order=True)
class _ScheduledCall:
    """Internal heap entry for a scheduled callback."""

    due: float
    sequence: int
    callback: Callable[[], None] = field(compare=False)
    interval: float | None = field(default=None, compare=False)
    cancelled: bool = field(default=False, compare=False)


class TimerHandle:
    """Handle that can cancel a scheduled one-shot or periodic callback."""

    def __init__(self, call: _ScheduledCall) -> None:
        self._call = call

    @property
    def cancelled(self) -> bool:
        """Return whether this timer has been cancelled."""

        return self._call.cancelled

    def cancel(self) -> None:
        """Cancel the callback if it has not been executed yet."""

        self._call.cancelled = True


class MonotonicScheduler:
    """Schedule callbacks using monotonic time without blocking the caller."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._calls: list[_ScheduledCall] = []
        self._sequence = 0

    def call_later(self, delay: float, callback: Callable[[], None]) -> TimerHandle:
        """Schedule a one-shot callback after ``delay`` seconds.

        Args:
            delay: Non-negative delay in monotonic seconds.
            callback: Callback executed by the event-loop thread.

        Returns:
            A handle that can cancel the callback.
        """

        return self._schedule(self._clock() + max(0.0, delay), callback, None)

    def call_every(
        self,
        interval: float,
        callback: Callable[[], None],
        *,
        immediate: bool = False,
    ) -> TimerHandle:
        """Schedule a fixed-rate callback.

        The next deadline is based on the previous deadline rather than on
        callback completion time.  Missed intervals are skipped, preventing a
        slow probe from causing a burst of catch-up calls.

        Args:
            interval: Positive interval in monotonic seconds.
            callback: Callback executed by the event-loop thread.
            immediate: Execute once immediately before starting the interval.

        Returns:
            A cancellable timer handle.

        Raises:
            ValueError: If ``interval`` is not positive.
        """

        if interval <= 0:
            raise ValueError("Timer interval must be positive")
        first_due = self._clock() if immediate else self._clock() + interval
        return self._schedule(first_due, callback, interval)

    def _schedule(
        self,
        due: float,
        callback: Callable[[], None],
        interval: float | None,
    ) -> TimerHandle:
        self._sequence += 1
        call = _ScheduledCall(due, self._sequence, callback, interval)
        heapq.heappush(self._calls, call)
        return TimerHandle(call)

    def run_due(self) -> None:
        """Execute all callbacks whose deadlines have elapsed."""

        now = self._clock()
        while self._calls and self._calls[0].due <= now:
            call = heapq.heappop(self._calls)
            if call.cancelled:
                continue
            try:
                call.callback()
            except Exception:
                LOG.exception("Scheduled callback failed")

            if call.interval is not None and not call.cancelled:
                call.due += call.interval
                current = self._clock()
                if call.due <= current:
                    call.due = current + call.interval
                heapq.heappush(self._calls, call)
            now = self._clock()

    def seconds_to_next(self) -> float | None:
        """Return seconds to the next active callback, or ``None``."""

        while self._calls and self._calls[0].cancelled:
            heapq.heappop(self._calls)
        if not self._calls:
            return None
        return max(0.0, self._calls[0].due - self._clock())


class EventLoop:
    """Run callbacks and queued events without polling or busy waiting."""

    def __init__(self, scheduler: MonotonicScheduler | None = None) -> None:
        self.scheduler = scheduler or MonotonicScheduler()
        self._queue: queue.Queue[Callable[[], None]] = queue.Queue()
        self._condition = threading.Condition()
        self._stop = False

    def post(self, callback: Callable[[], None]) -> None:
        """Queue a callback from any thread and wake the event loop."""

        self._queue.put(callback)
        with self._condition:
            self._condition.notify()

    def stop(self) -> None:
        """Request loop termination and wake a sleeping loop."""

        with self._condition:
            self._stop = True
            self._condition.notify()

    def run(self) -> None:
        """Run until :meth:`stop` is called."""

        while not self._stop:
            self._drain_queue()
            self.scheduler.run_due()
            timeout = self.scheduler.seconds_to_next()
            with self._condition:
                if self._stop:
                    break
                if not self._queue.empty():
                    continue
                self._condition.wait(timeout)

    def _drain_queue(self) -> None:
        while True:
            try:
                callback = self._queue.get_nowait()
            except queue.Empty:
                return
            try:
                callback()
            except Exception:
                LOG.exception("Queued callback failed")


class WorkerPool:
    """Execute blocking probes and return results on the event-loop thread."""

    def __init__(self, loop: EventLoop, max_workers: int = 8) -> None:
        self._loop = loop
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="audio-manager-worker",
        )

    def submit(
        self,
        work: Callable[..., Any],
        *args: Any,
        on_success: Callable[[Any], None],
        on_error: Callable[[BaseException], None],
    ) -> Future[Any]:
        """Submit blocking work and post its result back to the event loop."""

        future = self._executor.submit(work, *args)

        def complete(done: Future[Any]) -> None:
            try:
                result = done.result()
            except BaseException as exc:  # pragma: no cover - thread boundary
                error = exc
                self._loop.post(lambda error=error: on_error(error))
            else:
                self._loop.post(lambda result=result: on_success(result))

        future.add_done_callback(complete)
        return future

    def shutdown(self) -> None:
        """Stop accepting work and wait for currently running probes."""

        self._executor.shutdown(wait=True, cancel_futures=True)
