import gzip
import xml.etree.ElementTree as ET
import os
import tempfile
import math
import streamlit as st
from io import BytesIO

# Routing rules mapping track names to routing values (same for all campuses)
ROUTING_MAP = {
    "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
    "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
    "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
    "CLICK TRACK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
    "GUIDE TRACK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
    "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
    "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
    "SYNTH BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
    "SUB": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
    "HOOKS": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
    "AG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "CHOIR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "BGV": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "BGVS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITARS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 1": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 2": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 3": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 4": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 5": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 6": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 7": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 8": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 9": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 10": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "E GUITAR 11": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 1": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 2": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 3": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 4": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 5": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 6": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 7": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 8": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 9": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 10": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GUITAR 11": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 1": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 2": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 3": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 4": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 5": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 6": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 7": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 8": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 9": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "EG 10": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS 1": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS 2": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS 3": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS 4": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "KEYS 5": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "SYNTH": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "ACOUSTIC": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "ACOUSTIC GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "PIANO": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "PIANO LINE": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GANG VOCALS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "VOCALS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "CHOIR 1": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "CHOIR 2": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "LOOP": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "LOOP 2": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "TAMBO": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "TAMBORINE": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "FX": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "SYNTH FX": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "HITS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "PERC HITS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    "ORGAN": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
    "GANG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
}

# Define tracks to mute and turn down (same for all campuses)
MUTE_TRACKS = {"BASS", "DRUMS", "AG", "ACOUSTIC", "ACOUSTIC GUITAR", "PIANO"}
TURN_DOWN_TRACKS = {"CHOIR", "BGV", "BGVS", "GANG VOCALS", "VOCALS", "CHOIR 1", "CHOIR 2", "GANG"}
VOLUME_REDUCTION_DB = -10  # Reduce volume by 10 dB

# List of campuses (replace with your actual campus names if needed)
CAMPUSES = [
    "Main Campus",
    "North Campus",
    "South Campus",
    "East Campus",
    "West Campus",
    "Central Campus"
]

def process_als(input_file_bytes, original_filename):
    """
    Process an .als file and return the processed file as bytes along with the output filename.
    input_file_bytes: Bytes of the input .als file
    original_filename: Original filename for naming the output file
    """
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_xml = os.path.join(temp_dir, "temp.xml")
            temp_modified_xml = os.path.join(temp_dir, "temp_modified.xml")

            # Decompress .als file to XML
            with gzip.open(input_file_bytes, "rb") as f_in:
                with open(temp_xml, "wb") as f_out:
                    f_out.write(f_in.read())

            # Parse XML
            tree = ET.parse(temp_xml)
            root = tree.getroot()

            # Process each track
            for track_type in ["AudioTrack", "MidiTrack", "GroupTrack"]:
                for track in root.findall(f".//{track_type}"):
                    name_elem = track.find(".//Name/EffectiveName")
                    track_name = name_elem.get("Value") if name_elem is not None else None

                    if not track_name or track_name.strip() == "":
                        continue  # Skip silently

                    # --- Routing Logic ---
                    device_chain = track.find("DeviceChain")
                    if device_chain is None:
                        device_chain = ET.SubElement(track, "DeviceChain")

                    output_elem = device_chain.find("AudioOutputRouting")
                    if output_elem is None:
                        output_elem = ET.SubElement(device_chain, "AudioOutputRouting")
                        target_elem = ET.SubElement(output_elem, "Target")
                        upper_elem = ET.SubElement(output_elem, "UpperDisplayString")
                        lower_elem = ET.SubElement(output_elem, "LowerDisplayString")
                        mpe_settings = ET.SubElement(output_elem, "MpeSettings")
                    else:
                        target_elem = output_elem.find("Target")
                        if target_elem is None:
                            target_elem = ET.SubElement(output_elem, "Target")
                        upper_elem = output_elem.find("UpperDisplayString")
                        if upper_elem is None:
                            upper_elem = ET.SubElement(output_elem, "UpperDisplayString")
                        lower_elem = output_elem.find("LowerDisplayString")
                        if lower_elem is None:
                            lower_elem = ET.SubElement(output_elem, "LowerDisplayString")
                        mpe_settings = output_elem.find("MpeSettings")
                        if mpe_settings is None:
                            mpe_settings = ET.SubElement(output_elem, "MpeSettings")

                    found_match = False
                    for keyword, routing_dict in ROUTING_MAP.items():
                        if keyword.upper() == track_name.upper():
                            target_elem.set("Value", routing_dict["Target"])
                            upper_elem.set("Value", "Ext. Out")
                            lower_elem.set("Value", routing_dict["LowerDisplayString"])
                            if not mpe_settings.text and not list(mpe_settings):
                                pass
                            else:
                                mpe_settings.text = None
                                mpe_settings.clear()
                            found_match = True
                            break

                    # --- Mute Logic (Updated to use Speaker) ---
                    mixer = device_chain.find("Mixer")
                    if mixer is None:
                        mixer = ET.SubElement(device_chain, "Mixer")

                    speaker = mixer.find("Speaker")
                    if speaker is None:
                        speaker = ET.SubElement(mixer, "Speaker")
                        manual_speaker = ET.SubElement(speaker, "Manual")
                        manual_speaker.set("Value", "true")
                    else:
                        manual_speaker = speaker.find("Manual")
                        if manual_speaker is None:
                            manual_speaker = ET.SubElement(speaker, "Manual")
                            manual_speaker.set("Value", "true")

                    if track_name.upper() in MUTE_TRACKS:
                        manual_speaker.set("Value", "false")

                    # --- Volume Adjustment Logic ---
                    volume = mixer.find("Volume")
                    if volume is None:
                        volume = ET.SubElement(mixer, "Volume")
                        manual_volume = ET.SubElement(volume, "Manual")
                        manual_volume.set("Value", "0.794328")  # Default to 0 dB
                    else:
                        manual_volume = volume.find("Manual")
                        if manual_volume is None:
                            manual_volume = ET.SubElement(volume, "Manual")
                            manual_volume.set("Value", "0.794328")

                    current_volume = float(manual_volume.get("Value"))
                    if track_name.upper() in TURN_DOWN_TRACKS:
                        # Convert current volume to dB
                        current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                        # Reduce by 10 dB
                        new_db = current_db + VOLUME_REDUCTION_DB
                        # Convert back to linear
                        new_volume = 10 ** (new_db / 20) if new_db > -float('inf') else 0.0
                        manual_volume.set("Value", str(new_volume))

            # Save modified XML
            tree.write(temp_modified_xml, encoding="utf-8", xml_declaration=True)

            # Recompress to .als
            output_buffer = BytesIO()
            with open(temp_modified_xml, "rb") as f_in:
                with gzip.open(output_buffer, "wb") as f_out:
                    f_out.write(f_in.read())

            # Generate output filename
            base_name = os.path.splitext(original_filename)[0]
            output_filename = f"{base_name}_routed.als"

            return output_buffer.getvalue(), output_filename

    except Exception as e:
        st.error(f"Error: Failed to process {original_filename}: {str(e)}")
        return None, None

# Streamlit app
def main():
    st.title("Ableton Live Router")
    st.write("Select a campus and upload your Ableton Live (.als) files to route tracks according to predefined rules.")

    # Campus selection dropdown
    selected_campus = st.selectbox("Select Campus", CAMPUSES)

    # File uploader
    uploaded_files = st.file_uploader(f"Select Ableton Live (.als) Files for {selected_campus}", type=["als"], accept_multiple_files=True)

    if uploaded_files:
        processed_count = 0
        for uploaded_file in uploaded_files:
            # Read the uploaded file
            file_bytes = BytesIO(uploaded_file.read())
            original_filename = uploaded_file.name

            if not original_filename.lower().endswith(".als"):
                st.warning(f"Skipping {original_filename}: Not an .als file.")
                continue

            # Process the file
            with st.spinner(f"Processing {original_filename} for {selected_campus}..."):
                output_bytes, output_filename = process_als(file_bytes, original_filename)

            if output_bytes and output_filename:
                processed_count += 1
                st.success(f"Processed {original_filename} → {output_filename} for {selected_campus}")

                # Provide a download button for the processed file
                st.download_button(
                    label=f"Download {output_filename}",
                    data=output_bytes,
                    file_name=output_filename,
                    mime="application/octet-stream"
                )
            else:
                st.error(f"Failed to process {original_filename} for {selected_campus}.")

        if processed_count > 0:
            st.success(f"Processed {processed_count} files successfully for {selected_campus}.")
        else:
            st.warning(f"No files were processed successfully for {selected_campus}.")

if __name__ == "__main__":
    main()
