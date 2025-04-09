import gzip
import xml.etree.ElementTree as ET
import os
import tempfile
import math
import streamlit as st
from io import BytesIO
import pandas as pd
import requests
from io import StringIO

# Function to read the Google Sheet via CSV export
@st.cache_data(ttl=600)  # Cache for 10 minutes
def load_spreadsheet_data_csv():
    try:
        url = "https://docs.google.com/spreadsheets/d/1v-ijfylVlbJB3qLJu-dXbFgdbeuWgJjOIj2umhcE9Q8/export?format=csv&gid=0"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = StringIO(response.text)
        df = pd.read_csv(data)
        return df
    except requests.Timeout:
        st.error("Error: Timed out while fetching the spreadsheet. Please try again later.")
        return None
    except requests.RequestException as e:
        st.error(f"Error: Failed to fetch spreadsheet data: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error: Failed to load spreadsheet data: {str(e)}")
        return None

# Function to dynamically generate the channel map based on routing values in the spreadsheet
def generate_channel_map(df, campus_columns):
    channel_map = {}
    all_channels = set()
    for campus, (routing_col, _) in campus_columns.items():
        if routing_col in df.columns:
            channels = df[routing_col].dropna().astype(str).unique()
            all_channels.update(channels)

    stereo_count = 1
    for channel in sorted(all_channels):
        channel = channel.strip()
        if not channel:
            continue
        if "/" in channel:
            channel_map[channel] = {
                "Target": f"AudioOut/External/S{stereo_count}",
                "LowerDisplayString": channel
            }
            stereo_count += 1
        else:
            try:
                channel_num = int(channel) - 1
                channel_map[channel] = {
                    "Target": f"AudioOut/External/M{channel_num}",
                    "LowerDisplayString": channel
                }
            except ValueError:
                st.warning(f"Invalid channel format '{channel}' in spreadsheet. Skipping this channel.")
                continue
    return channel_map

# Function to map output channels to Ableton Live targets using the dynamic channel map
def map_channel_to_target(channel, channel_map):
    if channel not in channel_map:
        st.warning(f"Unknown channel '{channel}' in spreadsheet. Skipping track.")
        return None
    return channel_map[channel]

# Function to process an .als file based on the selected campus
def process_als(input_file_bytes, original_filename, selected_campus, df, campus_columns, channel_map):
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

            routing_col, instruction_col = campus_columns[selected_campus]

            # Process each track
            for track in root.findall(".//AudioTrack") + root.findall(".//MidiTrack") + root.findall(".//GroupTrack"):
                name_elem = track.find(".//Name/EffectiveName")
                track_name = name_elem.get("Value") if name_elem is not None else None

                if not track_name or track_name.strip() == "":
                    continue

                track_row = df[df["Track Name"].str.upper() == track_name.upper()]
                if track_row.empty:
                    continue

                routing = track_row.iloc[0][routing_col]
                instruction = track_row.iloc[0][instruction_col] if instruction_col in track_row else ""

                if not routing:
                    continue

                channel = str(routing).strip()
                instruction = str(instruction).strip() if instruction else ""
                mute = instruction.lower() == "mute"
                db_reduction = None
                if instruction and not mute:
                    try:
                        db_reduction = float(instruction)
                    except ValueError:
                        st.warning(f"Invalid dB value '{instruction}' for track '{track_name}'.")

                routing_dict = map_channel_to_target(channel, channel_map)
                if routing_dict is None:
                    continue

                # --- Routing Logic ---
                device_chain = track.find("DeviceChain") or ET.SubElement(track, "DeviceChain")

                # Remove any existing AudioOutputRouting to start fresh
                existing_output = device_chain.find("AudioOutputRouting")
                if existing_output is not None:
                    device_chain.remove(existing_output)

                # Create a new AudioOutputRouting element
                output_elem = ET.SubElement(device_chain, "AudioOutputRouting")
                target_elem = ET.SubElement(output_elem, "Target")
                upper_elem = ET.SubElement(output_elem, "UpperDisplayString")
                lower_elem = ET.SubElement(output_elem, "LowerDisplayString")
                mpe_settings = ET.SubElement(output_elem, "MpeSettings")

                target_elem.set("Value", routing_dict["Target"])
                upper_elem.set("Value", "Ext. Out")
                lower_elem.set("Value", routing_dict["LowerDisplayString"])
                mpe_settings.text = None

                # Debug: Log the routing for this track
                st.write(f"Track: {track_name}, Target: {routing_dict['Target']}, Lower: {routing_dict['LowerDisplayString']}")

                # --- Mute Logic ---
                mixer = device_chain.find("Mixer") or ET.SubElement(device_chain, "Mixer")
                speaker = mixer.find("Speaker") or ET.SubElement(mixer, "Speaker")
                manual_speaker = speaker.find("Manual") or ET.SubElement(speaker, "Manual")
                manual_speaker.set("Value", "false" if mute else "true")

                # --- Volume Adjustment Logic ---
                if db_reduction is not None and db_reduction != 0.0:
                    volume = mixer.find("Volume") or ET.SubElement(mixer, "Volume")
                    manual_volume = volume.find("Manual") or ET.SubElement(volume, "Manual")
                    if manual_volume.get("Value") is None:
                        manual_volume.set("Value", "0.794328")

                    current_volume = float(manual_volume.get("Value"))
                    current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                    new_db = current_db + db_reduction
                    new_volume = 10 ** (new_db / 20) if new_db > -float('inf') else 0.0
                    manual_volume.set("Value", str(new_volume))

            # Save modified XML with explicit encoding
            tree.write(temp_modified_xml, encoding="utf-8", xml_declaration=True)

            # Debug: Save the intermediate XML for inspection
            with open(temp_modified_xml, "r", encoding="utf-8") as f:
                xml_content = f.read()
            st.download_button(
                label=f"Download Intermediate XML for {original_filename}",
                data=xml_content,
                file_name=f"{os.path.splitext(original_filename)[0]}_modified.xml",
                mime="text/xml"
            )

            # Recompress to .als
            output_buffer = BytesIO()
            with open(temp_modified_xml, "rb") as f_in:
                with gzip.GzipFile(fileobj=output_buffer, mode="wb") as f_out:
                    f_out.write(f_in.read())
            output_bytes = output_buffer.getvalue()

            base_name = os.path.splitext(original_filename)[0]
            campus_for_filename = selected_campus.replace(" ", "").replace("ñ", "n")
            output_filename = f"{base_name}_{campus_for_filename}_routed (with spreadsheet).als"

            return output_bytes, output_filename

    except Exception as e:
        st.error(f"Error: Failed to process {original_filename}: {str(e)}")
        return None, None

# Streamlit app
def main():
    st.title("Ableton Live Router (Spreadsheet)")
    st.write("Select a campus and upload your Ableton Live (.als) files to route tracks according to the spreadsheet rules.")

    df = load_spreadsheet_data_csv()
    if df is None:
        st.error("Cannot proceed without spreadsheet data. Please ensure the spreadsheet is publicly viewable and the URL is correct.")
        return

    all_columns = df.columns[1:]
    CAMPUSES = []
    campus_columns = {}
    for i in range(0, len(all_columns), 2):
        routing_col = all_columns[i]
        if "Unnamed" not in routing_col:
            CAMPUSES.append(routing_col)
            instruction_col = all_columns[i + 1] if i + 1 < len(all_columns) else None
            campus_columns[routing_col] = (routing_col, instruction_col)

    if not CAMPUSES:
        st.error("No campuses found in the spreadsheet. Please ensure the spreadsheet has campus columns.")
        return

    channel_map = generate_channel_map(df, campus_columns)

    selected_campus = st.selectbox("Select Campus", CAMPUSES)
    uploaded_files = st.file_uploader(f"Select Ableton Live (.als) Files for {selected_campus}", type=["als"], accept_multiple_files=True)

    if uploaded_files:
        processed_count = 0
        for uploaded_file in uploaded_files:
            file_bytes = BytesIO(uploaded_file.read())
            original_filename = uploaded_file.name

            if not original_filename.lower().endswith(".als"):
                st.warning(f"Skipping {original_filename}: Not an .als file.")
                continue

            with st.spinner(f"Processing {original_filename} for {selected_campus}..."):
                output_bytes, output_filename = process_als(file_bytes, original_filename, selected_campus, df, campus_columns, channel_map)

            if output_bytes and output_filename:
                processed_count += 1
                st.success(f"Processed {original_filename} → {output_filename} for {selected_campus}")
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
