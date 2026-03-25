import subprocess
import os
import json
import logging

def generate_preview(input_path, output_path, bitrate='128k'):
    """Converts audio to MP3 preview using ffmpeg"""
    try:
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-vn', '-ar', '44100', '-ac', '2',
            '-b:a', bitrate, output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg conversion failed for {input_path}: {e.stderr.decode()}")
        return False

def generate_waveform(input_path, output_path):
    """Generates JSON peak data using audiowaveform"""
    try:
        cmd = [
            'audiowaveform', '-i', input_path,
            '-o', output_path,
            '--pixels-per-second', '20', '--bits', '8'
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Audiowaveform failed for {input_path}: {e.stderr.decode()}")
        # Check if audiowaveform is installed
        return False
    except FileNotFoundError:
        logging.error("audiowaveform not found in PATH")
        return False
