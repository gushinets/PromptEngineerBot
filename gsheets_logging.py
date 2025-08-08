import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class GoogleSheetsHandler(logging.Handler):
    """
    A logging handler that buffers records and appends them to a Google Sheet
    using a background worker thread for non-blocking, batched writes.

    Configuration supports either a credentials JSON string (env) or a path
    to a service account file. Target sheet can be specified by spreadsheet ID
    or by spreadsheet name.
    """

    def __init__(
        self,
        *,
        credentials_json: Optional[str] = None,
        credentials_file: Optional[str] = None,
        spreadsheet_id: Optional[str] = None,
        spreadsheet_name: Optional[str] = None,
        worksheet_title: str = "Logs",
        batch_size: int = 20,
        flush_interval_seconds: float = 5.0,
        include_fields: Optional[List[str]] = None,
    ) -> None:
        super().__init__()

        if not spreadsheet_id and not spreadsheet_name:
            raise ValueError("Either spreadsheet_id or spreadsheet_name must be provided")

        self._credentials_json = credentials_json
        self._credentials_file = credentials_file
        self._spreadsheet_id = spreadsheet_id
        self._spreadsheet_name = spreadsheet_name
        self._worksheet_title = worksheet_title
        self._batch_size = max(1, int(batch_size))
        self._flush_interval_seconds = max(0.5, float(flush_interval_seconds))

        # If include_fields is provided, only include those record attributes (in order)
        # Supported built-in keys: time, level, logger, message, module, func, line, pathname, process, thread
        # Additionally, if the log message is a JSON object, keys will be looked up from that JSON
        self._include_fields = include_fields or [
            "time",
            "level",
            "logger",
            "message",
            "module",
            "func",
            "line",
        ]

        # Fields that represent timestamp and should not alone justify a row write
        self._datetime_field_names = {"DateTime", "time"}

        self._buffer: List[List[Any]] = []
        self._buffer_lock = threading.Lock()
        self._flush_event = threading.Event()
        self._stop_event = threading.Event()
        self._client = None
        self._worksheet = None

        self._start_client()
        self._worker_thread = threading.Thread(target=self._worker_loop, name="GoogleSheetsHandlerWorker", daemon=True)
        self._worker_thread.start()

    def _start_client(self) -> None:
        # Lazy import so that unit tests can run without gspread unless enabled
        import gspread

        if self._credentials_json:
            try:
                data: Dict[str, Any] = json.loads(self._credentials_json)
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid GOOGLE_SERVICE_ACCOUNT_JSON provided") from exc
            self._client = gspread.service_account_from_dict(data)
        elif self._credentials_file:
            self._client = gspread.service_account(filename=self._credentials_file)
        else:
            # Fall back to default credentials env if present
            self._client = gspread.service_account()

        if self._spreadsheet_id:
            spreadsheet = self._client.open_by_key(self._spreadsheet_id)
        else:
            spreadsheet = self._client.open(self._spreadsheet_name)

        # Get or create worksheet
        try:
            self._worksheet = spreadsheet.worksheet(self._worksheet_title)
        except Exception:
            # Create if missing
            self._worksheet = spreadsheet.add_worksheet(title=self._worksheet_title, rows=1000, cols=20)
            # Optionally add a header row matching include_fields exactly
            header = list(self._include_fields)
            try:
                self._worksheet.append_row(header, value_input_option="USER_ENTERED")
            except Exception:
                # Do not fail logging if header can't be written
                pass

    def format_record_as_row(self, record: logging.LogRecord) -> List[Any]:
        created = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        message_text = self.format(record) if self.formatter else record.getMessage()
        field_map = {
            "time": created,
            "DateTime": created,
            "level": record.levelname,
            "logger": record.name,
            "message": message_text,
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
            "pathname": record.pathname,
            "process": record.process,
            "thread": record.threadName,
        }

        json_data: Optional[Dict[str, Any]] = None
        try:
            json_data = json.loads(message_text)
            if not isinstance(json_data, dict):
                json_data = None
        except Exception:
            json_data = None

        row: List[Any] = []
        for key in self._include_fields:
            if key in field_map:
                row.append(field_map[key])
            elif json_data and key in json_data:
                row.append(json_data[key])
            else:
                row.append("")
        return row

    def emit(self, record: logging.LogRecord) -> None:
        try:
            row = self.format_record_as_row(record)
            # Skip rows that only contain DateTime/time and nothing else
            try:
                non_time_values = [
                    value for idx, value in enumerate(row)
                    if self._include_fields[idx] not in self._datetime_field_names
                ]
                has_non_time_content = any(
                    (str(v).strip() != "") for v in non_time_values
                )
                if not has_non_time_content:
                    return
            except Exception:
                # If any error in checking, fall back to writing
                pass
            with self._buffer_lock:
                self._buffer.append(row)
                if len(self._buffer) >= self._batch_size:
                    self._flush_event.set()
        except Exception:
            # Never raise from logging handler
            self.handleError(record)

    def _worker_loop(self) -> None:
        # Periodically flush buffer or when signaled
        while not self._stop_event.is_set():
            signaled = self._flush_event.wait(timeout=self._flush_interval_seconds)
            if self._stop_event.is_set():
                break
            try:
                self._flush_once()
            finally:
                if signaled:
                    # Clear the event only after a flush attempt
                    self._flush_event.clear()

        # Final flush on exit
        try:
            self._flush_once()
        except Exception:
            pass

    def _flush_once(self) -> None:
        # Snapshot buffer
        with self._buffer_lock:
            if not self._buffer:
                return
            payload = self._buffer
            self._buffer = []

        try:
            # Append in one batch
            # Use append_rows to minimize API calls
            self._worksheet.append_rows(payload, value_input_option="USER_ENTERED")
        except Exception:
            # On failure, attempt a single retry after short sleep
            time.sleep(1.0)
            try:
                self._worksheet.append_rows(payload, value_input_option="USER_ENTERED")
            except Exception:
                # Re-queue at the front to avoid data loss
                with self._buffer_lock:
                    self._buffer = payload + self._buffer

    def close(self) -> None:
        try:
            self._stop_event.set()
            self._flush_event.set()
            if hasattr(self, "_worker_thread") and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=3.0)
        finally:
            super().close()


def build_google_sheets_handler_from_env(env_getter) -> Optional[GoogleSheetsHandler]:
    """
    Create a GoogleSheetsHandler if GSHEETS_LOGGING_ENABLED is truthy.

    Reads configuration from environment using the provided getter (e.g., os.getenv):
      - GSHEETS_LOGGING_ENABLED: 'true' to enable
      - GOOGLE_SERVICE_ACCOUNT_JSON: Raw JSON credentials (optional)
      - GOOGLE_APPLICATION_CREDENTIALS: Path to service account file (optional)
      - GSHEETS_SPREADSHEET_ID or GSHEETS_SPREADSHEET_NAME: target spreadsheet
      - GSHEETS_WORKSHEET: worksheet title (default 'Logs')
      - GSHEETS_BATCH_SIZE: int (default 20)
      - GSHEETS_FLUSH_INTERVAL_SECONDS: float (default 5.0)
    """
    enabled = str(env_getter("GSHEETS_LOGGING_ENABLED", "")).strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return None

    credentials_json = env_getter("GOOGLE_SERVICE_ACCOUNT_JSON")
    credentials_file = env_getter("GOOGLE_APPLICATION_CREDENTIALS")
    spreadsheet_id = env_getter("GSHEETS_SPREADSHEET_ID")
    spreadsheet_name = env_getter("GSHEETS_SPREADSHEET_NAME")
    worksheet_title = env_getter("GSHEETS_WORKSHEET", "Logs")
    batch_size = int(env_getter("GSHEETS_BATCH_SIZE", 20))
    flush_interval_seconds = float(env_getter("GSHEETS_FLUSH_INTERVAL_SECONDS", 5.0))

    # Optional fields configuration (comma-separated);
    # default to a schema suited for LLM exchange logging
    fields_env = env_getter("GSHEETS_FIELDS")
    include_fields = None
    if fields_env:
        include_fields = [item.strip() for item in str(fields_env).split(',') if item.strip()]
    else:
        include_fields = [
            "DateTime",
            "BotID",
            "TelegramID",
            "LLM",
            "OptimizationModel",
            "UserRequest",
            "Answer",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        ]

    try:
        handler = GoogleSheetsHandler(
            credentials_json=credentials_json,
            credentials_file=credentials_file,
            spreadsheet_id=spreadsheet_id,
            spreadsheet_name=spreadsheet_name,
            worksheet_title=worksheet_title,
            batch_size=batch_size,
            flush_interval_seconds=flush_interval_seconds,
            include_fields=include_fields,
        )
        # Keep logs concise in sheet; rely on base format for console/file
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(message)s"))
        return handler
    except Exception as exc:
        # If handler cannot be created, fail silently but note in root logger once stdout/stderr available
        logging.getLogger(__name__).warning(f"GoogleSheetsHandler disabled due to initialization error: {exc}")
        return None


