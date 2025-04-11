import gzip
import xml.etree.ElementTree as ET
import os
import streamlit as st
from io import BytesIO

def decompress_als_to_xml(als_file_bytes):
    """Decompress an .als file to XML and return the root element."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_xml = os.path.join(temp_dir, "temp.xml")
        with gzip.open(als_file_bytes, "rb") as f_in:
            with open(temp_xml, "wb") as f_out:
                f_out.write(f_in.read())
        tree = ET.parse(temp_xml)
        return tree.getroot()

def find_audio_files_in_als(root, als_file_path):
    """Find all audio files in the .als file and map them to tracks."""
    # Get the directory of the .als file
    project_dir = os.path.dirname(als_file_path) if als_file_path else None

    # Dictionary to store track-to-file mappings
    track_to_files = {}

    # Find all audio tracks
    for track in root.findall(".//AudioTrack"):
        # Get the track name
        name_elem = track.find(".//Name/EffectiveName")
        track_name = name_elem.get("Value") if name_elem is not None else "Unnamed Track"

        # Find all clips in the track
        clips = track.findall(".//MainSequencer/ClipSlotList/ClipSlot/Clip/Sample")
        audio_files = []

        for clip in clips:
            # Get the file reference
            file_ref = clip.find("FileRef")
            if file_ref is None:
                continue

            # Extract the file path
            path_elem = file_ref.find("RelativePath") or file_ref.find("Path")
            if path_elem is None:
                continue

            relative_path = path_elem.get("Value", "")
            if not relative_path:
                continue

            # Construct the full path
            if project_dir:
                # Assume the file is relative to the project directory
                full_path = os.path.join(project_dir, relative_path)
                full_path = os.path.normpath(full_path)  # Normalize path for the OS
            else:
                full_path = relative_path  # Fallback if we don't have the project dir

            audio_files.append(full_path)

        if audio_files:
            track_to_files[track_name] = audio_files

    return track_to_files

# Streamlit app for Phase 1
def main():
    st.title("Ableton Audio File Locator (Phase 1)")
    st.write("Upload an Ableton Live (.als) file to locate its audio files and map them to tracks.")

    uploaded_file = st.file_uploader("Select an Ableton Live (.als) File", type=["als"])
    als_file_path = st.text_input("Enter the full path to the .als file (optional, for accurate file paths):", "")

    if uploaded_file:
        file_bytes = BytesIO(uploaded_file.read())
        original_filename = uploaded_file.name

        if not original_filename.lower().endswith(".als"):
            st.warning(f"Skipping {original_filename}: Not an .als file.")
            return

        with st.spinner(f"Processing {original_filename}..."):
            # Decompress and parse the .als file
            root = decompress_als_to_xml(file_bytes)

            # Find audio files and map them to tracks
            track_to_files = find_audio_files_in_als(root, als_file_path)

            # Display the results
            st.subheader("Track to Audio File Mapping")
            if track_to_files:
                for track_name, audio_files in track_to_files.items():
                    st.write(f"**Track: {track_name}**")
                    for audio_file in audio_files:
                        st.write(f"- {audio_file}")
            else:
                st.write("No audio files found in the project.")

if __name__ == "__main__":
    main()
