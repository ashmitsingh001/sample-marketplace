import zipfile
import struct
import os
import json

class ZipIndexer:
    """
    Surgically parses a ZIP file to find absolute byte offsets of internal files.
    This is used for high-performance on-demand extraction via HTTP Range requests.
    """

    AUDIO_EXTENSIONS = {'.wav', '.aiff', '.aif', '.flac'}

    @staticmethod
    def get_index(zip_path):
        if not os.path.exists(zip_path):
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

        results = []
        with open(zip_path, 'rb') as f:
            # First, use standard zipfile to get Central Directory info
            with zipfile.ZipFile(f) as z:
                for info in z.infolist():
                    # Skip directories
                    if info.is_dir():
                        continue
                        
                    ext = os.path.splitext(info.filename.lower())[1]
                    is_audio = ext in ZipIndexer.AUDIO_EXTENSIONS
                    
                    header_offset = info.header_offset
                    compression = info.compress_type
                    needs_repack = compression != zipfile.ZIP_STORED
                    
                    # Read the Local File Header (LFH) to find the exact start of data
                    f.seek(header_offset)
                    lfh_data = f.read(30)
                    
                    if len(lfh_data) < 30:
                        continue
                        
                    # Unpack filename_len and extra_len
                    filename_len = struct.unpack('<H', lfh_data[26:28])[0]
                    extra_len = struct.unpack('<H', lfh_data[28:30])[0]
                    
                    data_start = header_offset + 30 + filename_len + extra_len
                    file_size = info.file_size
                    data_end = data_start + file_size - 1 # Inclusive
                    
                    # Store relative path as filename to maintain folder structure
                    results.append({
                        "filename": info.filename,
                        "data_start": data_start,
                        "data_end": data_end,
                        "file_size": file_size,
                        "compression_method": compression,
                        "is_audio": is_audio,
                        "needs_repack": needs_repack
                    })
                    
        return results
                    
        return results

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python zip_indexer.py <path_to_zip>")
        sys.exit(1)
        
    path = sys.argv[1]
    try:
        index = ZipIndexer.get_index(path)
        print(json.dumps(index, indent=2))
    except Exception as e:
        print(f"Error: {e}")
