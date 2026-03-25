import re

# Standardized Key Mapping
KEY_MAP = {
    'c#': 'C#', 'db': 'C#',
    'd#': 'D#', 'eb': 'D#',
    'f#': 'F#', 'gb': 'F#',
    'g#': 'G#', 'ab': 'G#',
    'a#': 'A#', 'bb': 'A#',
    'min': 'm', 'minor': 'm', 'maj': '', 'major': ''
}

def normalize_key(key_str):
    if not key_str: return 'Unknown'
    k = key_str.lower().strip()
    # Replace long forms
    for old, new in KEY_MAP.items():
        k = k.replace(old, new)
    # Remove redundant info
    k = re.sub(r'[^A-G#m]', '', k)
    return k if k else 'Unknown'

def extract_metadata(filename):
    """
    Extracts BPM and Musical Key from a filename using regex.
    Examples: 
    'Kick_124_Am.wav' -> {'bpm': 124, 'key': 'Am'}
    'Synth 128 C# minor.wav' -> {'bpm': 128, 'key': 'C#m'}
    """
    # 1. Sanitize for analysis
    clean_name = filename.lower()
    
    # 2. Extract BPM: Look for 2-3 digits followed or preceded by bpm/_/space
    bpm_match = re.search(r'(?i)(\d{2,3})(?=\s?bpm|BPM|_bpm|[-_\s])', filename)
    bpm = int(bpm_match.group(1)) if bpm_match else 0
    
    # 3. Extract Key: Look for A-G with optional #/b and m/min/minor
    key_match = re.search(r'(?i)\b([A-G][#b]?(?:m|min|minor)?)\b', filename)
    key = normalize_key(key_match.group(1)) if key_match else 'Unknown'
    
    return {
        'bpm': bpm,
        'key': key,
        'needs_review': (bpm == 0 or key == 'Unknown')
    }

def sanitize_filename(filename):
    """lowercase_snake_case with basic collision handling support in main loop"""
    name = filename.rsplit('.', 1)[0]
    ext = filename.rsplit('.', 1)[1] if '.' in filename else ''
    
    # Remove special chars, spaces to underscore
    clean = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
    clean = re.sub(r'_+', '_', clean).strip('_')
    
    return f"{clean}.{ext}" if ext else clean
