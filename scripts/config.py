# Ingestion Pipeline Config

MAX_FILES_PER_RUN = 350
MAX_RUNTIME_MINUTES = 50
FAILURE_THRESHOLD_PERCENT = 30
PREVIEW_BITRATE = '128k'
DRY_RUN = True  # Set to False for production execution

# Metadata Extraction
SUPPORTED_EXTENSIONS = ['.wav', '.mp3', '.aif', '.aiff', '.flac']

# Storage Organization
PREVIEW_SUBFOLDER = 'previews'
WAVEFORM_SUBFOLDER = 'waveforms'
