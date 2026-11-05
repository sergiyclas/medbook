# Background process that delivers queued notifications.
# Usage: python -m app.worker

import logging
import signal
import threading

from app.bootstrap import build_dispatcher
from app.core.config import get_settings

log = logging.getLogger("medbook.worker")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = get_settings()
    dispatcher = build_dispatcher()
    stop = threading.Event()
    # docker compose stop sends SIGTERM: finish the current batch, then exit
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    log.info(
        "worker started: mode=%s, every %ss",
        settings.notification_mode,
        settings.worker_interval_seconds,
    )
    while not stop.is_set():
        try:
            results = dispatcher.process_due()
            if results:
                log.info("batch done: %s", {s.value: n for s, n in results.items()})
        except Exception:
            # System boundary: a database hiccup must not kill the worker
            log.exception("dispatch cycle failed")
        stop.wait(settings.worker_interval_seconds)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
