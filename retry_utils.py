import time
import random
import logging
from typing import Any, Callable, Tuple, Optional


def log_struct(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    try:
        msg = {"event": event, **fields}
        logger.log(level, str(msg))
    except Exception:
        try:
            logger.log(level, f"{event} {fields}")
        except Exception:
            pass


def retry_call(
    func: Callable,
    *args: Any,
    retries: int = 3,
    delay: float = 0.5,
    backoff: float = 1.8,
    exceptions: Tuple[type, ...] = (Exception,),
    logger: Optional[logging.Logger] = None,
    op: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    attempt = 0
    wait = max(0.0, float(delay))
    last_exc: Optional[BaseException] = None
    while attempt <= retries:
        try:
            return func(*args, **kwargs)
        except exceptions as e:
            last_exc = e
            if attempt == retries:
                if logger:
                    log_struct(logger, logging.ERROR, "retry_failed", op=op or getattr(func, "__name__", "func"), attempt=attempt, err=str(e))
                raise
            if logger:
                log_struct(logger, logging.WARNING, "retry", op=op or getattr(func, "__name__", "func"), attempt=attempt, err=str(e))
            sleep_time = wait * (1 + 0.1 * random.random())
            time.sleep(sleep_time)
            wait *= backoff if backoff and backoff > 1 else 1.0
            attempt += 1
    if last_exc:
        raise last_exc
    return None
