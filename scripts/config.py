import os

# Ingestion Pipeline Config

MAX_FILES_PER_RUN = 350
MAX_RUNTIME_MINUTES = 50
FAILURE_THRESHOLD_PERCENT = 30
PREVIEW_BITRATE = '128k'
DRY_RUN_DB = False       # Real Supabase DB writes
DRY_RUN_STORAGE = False  # Real Telegram/Storage uploads

# Metadata Extraction
SUPPORTED_EXTENSIONS = ['.wav', '.mp3', '.aif', '.aiff', '.flac']

# Storage Organization
PREVIEW_SUBFOLDER = 'previews'
WAVEFORM_SUBFOLDER = 'waveforms'

# Telegram Channel IDs (overridable via environment)
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')          # PACKS channel (ZIPs)
TELEGRAM_SAMPLES_CHAT_ID = os.getenv('TELEGRAM_SAMPLES_CHAT_ID', '')  # SAMPLES channel (WAVs)

