"""Immediate, rotating file logs; no external collector is required."""

import copy
import datetime as dt
import json
import logging
import os
import subprocess
import sys
import threading
import time
import traceback
import uuid
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.telemetry import trace_context

RUN_ID = uuid.uuid4().hex
AUDIT_LOGGER = logging.getLogger("vcroles.audit")


def _unhandled_exception(error_type, error, tb):
    if issubclass(error_type, KeyboardInterrupt):
        sys.__excepthook__(error_type, error, tb)
        return
    logging.getLogger("vcroles.runtime").critical(
        "Unhandled process exception",
        exc_info=(error_type, error, tb),
        extra={"event": "unhandled_exception"},
    )


def _thread_exception(args):
    if args.exc_type is SystemExit:
        return
    logging.getLogger("vcroles.runtime").critical(
        "Unhandled thread exception",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        extra={
            "event": "unhandled_thread_exception",
            "context": {"thread": getattr(args.thread, "name", "unknown")},
        },
    )


def log_paths(log_dir: str | Path | None = None) -> tuple[Path, Path]:
    directory = Path(log_dir or os.environ.get("VCROLES_LOG_DIR", "logs"))
    return directory / "vcroles.jsonl", directory / "generator-audit.jsonl"


def source_revision() -> str:
    try:
        directory = Path(__file__).resolve().parents[1]
        revision = subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=directory,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=2,
        ).strip()
        dirty = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--"],
            cwd=directory,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).returncode
        return revision + ("+dirty" if dirty == 1 else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


class LogContext(logging.Filter):
    def __init__(self, revision: str):
        super().__init__()
        self.revision = revision

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = RUN_ID
        record.revision = self.revision
        if not hasattr(record, "context"):
            record.context = {}
        return True


class ConsoleFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.levelno >= getattr(record, "console_min_level", logging.INFO)


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


def stream_supports_colour(stream) -> bool:
    if "NO_COLOR" in os.environ:
        return False
    if "FORCE_COLOR" in os.environ:
        return os.environ["FORCE_COLOR"] != "0"
    return os.environ.get("TERM") != "dumb" and bool(
        getattr(stream, "isatty", lambda: False)()
    )


class ConsoleFormatter(UTCFormatter):
    COLOURS = {
        logging.DEBUG: "\x1b[40;1m",
        logging.INFO: "\x1b[34;1m",
        logging.WARNING: "\x1b[33;1m",
        logging.ERROR: "\x1b[31m",
        logging.CRITICAL: "\x1b[41m",
    }

    def __init__(self, *, colour: bool):
        self.colour = colour
        prefix = (
            "\x1b[90m%(asctime)sZ\x1b[0m %(levelname)s %(name)s"
            if colour
            else "%(asctime)sZ %(levelname)-8s %(name)s"
        )
        super().__init__(
            prefix + " run=%(run_id).8s %(message)s %(context)s",
            "%Y-%m-%dT%H:%M:%S",
        )

    def format(self, record: logging.LogRecord) -> str:
        if self.colour:
            # Handlers share the record. Keep ANSI codes and the exception cache
            # private to the console, including when handler order changes.
            record = copy.copy(record)
            colour = self.COLOURS.get(record.levelno, "\x1b[0m")
            record.levelname = f"{colour}{record.levelname:<8}\x1b[0m"
            record.name = f"\x1b[35m{record.name}\x1b[0m"
            record.exc_text = None
        return super().format(record)

    def formatException(self, exc_info) -> str:
        text = super().formatException(exc_info)
        return f"\x1b[31m{text}\x1b[0m" if self.colour else text


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": dt.datetime.fromtimestamp(record.created, dt.UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", "log"),
            "message": record.getMessage(),
            "pid": record.process,
            "run_id": record.run_id,
            "revision": record.revision,
            "context": record.context,
            **trace_context(),
        }
        if record.exc_info and record.exc_info[1] is not None:
            error = record.exc_info[1]
            data["exception"] = {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
                "http_status": getattr(error, "status", None),
                "discord_code": getattr(error, "code", None),
            }
        if record.stack_info:
            data["stack"] = record.stack_info
        return json.dumps(data, ensure_ascii=False, default=str)


class PersistentFileHandler(RotatingFileHandler):
    def __init__(
        self, path: Path, *, max_bytes: int, backups: int, audit: bool = False
    ):
        self.audit = audit
        super().__init__(
            path, mode="a", maxBytes=max_bytes, backupCount=backups, encoding="utf-8"
        )

    def emit(self, record: logging.LogRecord) -> None:
        # StreamHandler.emit flushes each record before returning. Sync rare
        # errors/audit records as well, without syncing every debug log.
        super().emit(record)
        if self.audit or record.levelno >= logging.ERROR:
            try:
                if self.stream is not None:
                    os.fsync(self.stream.fileno())
            except OSError:
                self.handleError(record)

    def handleError(self, record: logging.LogRecord) -> None:
        if self.audit:
            # A failed audit intent prevents destructive actions from proceeding
            # without a persisted record. Never recurse into logging here.
            raise OSError(
                f"Could not persist audit log {self.baseFilename}"
            ) from sys.exception()
        sys.stderr.write(f"Persistent log write failed: {self.baseFilename}\n")
        super().handleError(record)


def _separate_partial_record(path: Path) -> None:
    # Preserve a partial final record after a crash, but start the next run on
    # its own line instead of corrupting the next complete JSON record as well.
    with path.open("a+b") as stream:
        if stream.tell():
            stream.seek(-1, os.SEEK_END)
            if stream.read(1) != b"\n":
                stream.write(b"\n")
                stream.flush()
                os.fsync(stream.fileno())


def setup_logging(
    log_dir: str | Path | None = None,
    *,
    max_bytes: int = 20 * 1024 * 1024,
    audit_max_bytes: int = 5 * 1024 * 1024,
    backups: int = 10,
) -> None:
    if min(max_bytes, audit_max_bytes, backups) < 1:
        raise ValueError("Log sizes and backup count must be positive")
    paths = log_paths(log_dir)
    paths[0].parent.mkdir(parents=True, exist_ok=True)
    context = LogContext(source_revision())
    new_handlers: list[logging.Handler] = []
    try:
        for path, size, audit in (
            (paths[0], max_bytes, False),
            (paths[1], audit_max_bytes, True),
        ):
            _separate_partial_record(path)
            handler = PersistentFileHandler(
                path, max_bytes=size, backups=backups, audit=audit
            )
            new_handlers.append(handler)
            handler.setLevel(logging.DEBUG if not audit else logging.INFO)
            handler.setFormatter(JSONFormatter())
            handler.addFilter(context)
        console = logging.StreamHandler()
        new_handlers.append(console)
        console.setFormatter(
            ConsoleFormatter(colour=stream_supports_colour(console.stream))
        )
        console.addFilter(context)
        console.addFilter(ConsoleFilter())
    except BaseException:
        for handler in new_handlers:
            handler.close()
        raise

    root = logging.getLogger()
    for logger in (root, AUDIT_LOGGER):
        for handler in list(logger.handlers):
            if getattr(handler, "_vcroles_owned", False):
                logger.removeHandler(handler)
                handler.close()
    for handler in new_handlers:
        handler._vcroles_owned = True
    root.setLevel(logging.INFO)
    root.addHandler(new_handlers[0])
    root.addHandler(console)
    AUDIT_LOGGER.setLevel(logging.INFO)
    AUDIT_LOGGER.addHandler(new_handlers[1])
    AUDIT_LOGGER.propagate = True
    sys.excepthook = _unhandled_exception
    threading.excepthook = _thread_exception
    logging.getLogger("internal.bot").setLevel(logging.DEBUG)
    for name in ("discord.voice_client", "discord.player", "aiohttp", "httpx", "gtts"):
        logging.getLogger(name).setLevel(logging.WARNING)
    root.info(
        "Persistent logging initialized",
        extra={
            "event": "logging_initialized",
            "context": {"main_log": str(paths[0]), "audit_log": str(paths[1])},
        },
    )


def audit_event(event: str, *, error: BaseException | None = None, **context) -> None:
    AUDIT_LOGGER.log(
        logging.ERROR if error is not None else logging.INFO,
        event,
        extra={"event": event, "context": context},
        exc_info=(type(error), error, error.__traceback__)
        if error is not None
        else None,
    )
