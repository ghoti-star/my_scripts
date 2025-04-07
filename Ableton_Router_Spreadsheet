import gzip
import xml.etree.ElementTree as ET
import os
import tempfile
import math
import streamlit as st
from io import BytesIO
import pandas as pd

# Function to read the Google Sheet via CSV export
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_spreadsheet_data_csv():
    try:
        url = "https://docs.google.com/spreadsheets/d/1v-ijfylVlbJB3qLJu-dXbFgdbeuWgJjOIj2umhcE9Q8/export?format=csv&gid=0"
        df = pd.read_csv(url)
        return df
    except Exception as e:
        st.error(f"Failed to load spreadsheet data: {str(e)}")
        return None

# Function to map output channels to Ableton Live targets
def map_channel_to_target(channel):
    channel_map = {
        "1": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "2": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "3/4": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "5/6": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "7/8": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "7/0": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"}  # Assuming "7/0" is a typo for "7/8"
    }
    return channel_map.get(channel, {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"})  # Default to channel 1

# Function to process an .als file based on the selected campus
def process_als(input_file_bytes, original_filename, selected_campus, df):
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

                    # Look up the track in the DataFrame
                    track_row = df[df["Track Name"].str.upper() == track_name.upper()]
                    if track_row.empty:
                        continue  # Skip if track not found in spreadsheet

                    # Get the routing settings for the selected campus
                    settings = track_row.iloc[0][selected_campus]
                    if not settings:
                        continue  # Skip if no settings for this campus

                    # Parse the settings (e.g., "5/6 Mute", "5/6 Turn down", "1")
                    settings_parts = settings.split()
                    channel = settings_parts[0]  # e.g., "5/6"
                    mute = "Mute" in settings_parts
                    turn_down = "Turn down" in settings_parts or "Turn Down" in settings_parts

                    # Map the channel to Ableton Live target
                    routing_dict = map_channel_to_target(channel)

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

                    target_elem.set("Value", routing_dict["Target"])
                    upper_elem.set("Value", "Ext. Out")
                    lower_elem.set("Value", routing_dict["LowerDisplayString"])
                    if not mpe_settings.text and not list(mpe_settings):
                        pass
                    else:
                        mpe_settings.text = None
                        mpe_settings.clear()

                    # --- Mute Logic ---
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

                    if mute:
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

                    if turn_down:
                        current_volume = float(manual_volume.get("Value"))
                        # Convert current volume to dB
                        current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                        # Reduce by 10 dB
                        new_db = current_db - 10  # Assuming -10 dB as before
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

            # Generate output filename with campus name
            base_name = os.path.splitext(original_filename)[0]
            # Replace spaces and special characters in campus name for filename
            campus_for_filename = selected_campus.replace(" ", "").replace("ñ", "n")
            output_filename = f"{base_name}_{campus_for_filename}_routed.als"

            return output_buffer.getvalue(), output_filename

    except Exception as e:
        st.error(f"Error: Failed to process {original_filename}: {str(e)}")
        return None, None

# Streamlit app
def main():
    st.title("Ableton Live Router (Spreadsheet)")
    st.write("Select a campus and upload your Ableton Live (.als) files to route tracks according to the spreadsheet rules.")

    # Load spreadsheet data
    df = load_spreadsheet_data_csv()
    if df is None:
        st.error("Cannot proceed without spreadsheet data. Please ensure the spreadsheet is publicly viewable and the URL is correct.")
        return

    # Extract campus names from the spreadsheet (excluding "Track Name" column)
    CAMPUSES = df.columns[1:].tolist()  # Dynamically get campus names
    if not CAMPUSES:
        st.error("No campuses found in the spreadsheet. Please ensure the spreadsheet has campus columns.")
        return

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
                output_bytes, output_filename = process_als(file_bytes, original_filename, selected_campus, df)

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
