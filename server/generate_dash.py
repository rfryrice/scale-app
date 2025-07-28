import os
import subprocess

def generate_dash(mp4_path, segment_duration=4000):
    """
    Generate DASH (MPD + segments) for the given MP4 file using MP4Box.
    Args:
        mp4_path (str): Path to the input MP4 file.
        segment_duration (int): Segment duration in milliseconds (default: 4000ms = 4s).
    Returns:
        dash_dir (str): Path to the directory containing the DASH files, or None if failed.
    """
    if not os.path.isfile(mp4_path):
        raise FileNotFoundError(f"Input file not found: {mp4_path}")
    base = os.path.splitext(os.path.basename(mp4_path))[0]
    dash_dir = os.path.join(os.path.dirname(mp4_path), f"{base}_dash")
    os.makedirs(dash_dir, exist_ok=True)
    manifest_path = os.path.join(dash_dir, "manifest.mpd")
    # MP4Box command
    cmd = [
        "MP4Box",
        "-dash", str(segment_duration),
        "-frag", str(segment_duration),
        "-rap",
        "-profile", "dashavc264:onDemand",
        "-out", manifest_path,
        mp4_path
    ]
    try:
        subprocess.check_call(cmd)
        return dash_dir
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] MP4Box failed: {e}")
        return None
