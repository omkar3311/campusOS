import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARENT_DIR = os.path.dirname(BASE_DIR)

env_path = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_path):
    env_path = os.path.join(PARENT_DIR, ".env")
load_dotenv(env_path)

LOCAL_DB_HOST = os.getenv("LOCAL_DB_HOST", "localhost")
LOCAL_DB_NAME = os.getenv("LOCAL_DB_NAME")
LOCAL_DB_USER = os.getenv("LOCAL_DB_USER")
LOCAL_DB_PASSWORD = os.getenv("LOCAL_DB_PASSWORD")
LOCAL_DB_PORT = os.getenv("LOCAL_DB_PORT", "5432")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = os.getenv("DB_PORT", "5432")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "filestore")

raw_image_root = os.getenv("LOCAL_IMAGE_ROOT", "local_filestore")
if os.path.isabs(raw_image_root):
    LOCAL_IMAGE_ROOT = raw_image_root
elif os.path.exists(os.path.join(PARENT_DIR, raw_image_root)):
    LOCAL_IMAGE_ROOT = os.path.join(PARENT_DIR, raw_image_root)
else:
    LOCAL_IMAGE_ROOT = os.path.join(BASE_DIR, raw_image_root)

CACHE_DIR = os.path.join(BASE_DIR, "cache", "encodings")
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(LOCAL_IMAGE_ROOT, exist_ok=True)

candidate_model = os.path.join(BASE_DIR, "yolov8n.pt")
if not os.path.exists(candidate_model):
    candidate_model = os.path.join(PARENT_DIR, "yolov8n.pt")
YOLO_MODEL_PATH = candidate_model

STYLES_DIR = os.path.join(BASE_DIR, "styles")
