import logging
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now().strftime("%H-%M_%d-%m-%Y")
LOG_FILE = LOG_DIR / f"{timestamp}.log"


formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)


file_handler = logging.FileHandler(
    LOG_FILE,
    encoding="utf-8",
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)


root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)


if not root_logger.handlers:
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)

logging.getLogger("transformers").setLevel(logging.WARNING)

LOGGER = logging.getLogger(__name__)

LOGGER.info("Logging initialized.")
LOGGER.info("Log file: %s", LOG_FILE)