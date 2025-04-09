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
from collections import defaultdict

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

# Function to group tracks into songs based on start and end points
def group_tracks_into_songs(root):
    songs = defaultdict(list)
    tolerance = 0.1  # Allow 0.1 seconds tolerance for start/end points
    track_id = 0

    for track_type in ["AudioTrack", "MidiTrack"]:
        for track in root.findall(f".//{track_type}"):
            name_elem = track.find(".//Name/EffectiveName")
            track_name = name_elem.get("Value") if name_elem is not None else None
            if not track_name:
                continue

            clips = track.findall(".//AudioClip") if track_type == "AudioTrack" else track.findall(".//MidiClip")
            if not clips:
                continue

            clip = clips[0]
            start_elem = clip.find(".//LomId[@Value='0']/CurrentStart")
            end_elem = clip.find(".//LomId[@Value='0']/CurrentEnd")
            if start_elem is None or end_elem is None:
                continue

            start = float(start_elem.get("Value"))
            end = float(end_elem.get("Value"))

            found_group = False
            for song_key, tracks in songs.items():
                song_start, song_end = song_key
                if (abs(song_start - start) <= tolerance and abs(song_end - end) <= tolerance):
                    tracks.append((track_id, track, track_name))
                    found_group = True
                    break

            if not found_group:
                songs[(start, end)].append((track_id, track, track_name))

            track_id += 1

    return songs

# Function to calculate semitone difference (shortest distance)
def calculate_semitone_difference(original_key, target_key):
    keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    original_idx = keys.index(original_key)
    target_idx = keys.index(target_key)
    diff1 = target_idx - original_idx
    diff2 = diff1 - 12 if diff1 > 0 else diff1 + 12
    return diff1 if abs(diff1) <= abs(diff2) else diff2

# Function to process an .als file
def process_als(input_file_bytes, original_filename, selected_campus, df, campus_columns, channel_map, song_tuning_info):
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

            # Group tracks into songs
            songs = group_tracks_into_songs(root)

            # Apply tuning adjustments
            for song_idx, (song_key, song_tracks) in enumerate(songs.items()):
                song_start, song_end = song_key
                tuning_info = song_tuning_info.get(song_idx, {})
                original_key = tuning_info.get("original_key")
                target_key = tuning_info.get("target_key")
                if not original_key or not target_key:
                    continue  # Skip if tuning info is incomplete

                # Calculate semitone difference
                semitone_diff = calculate_semitone_difference(original_key, target_key)
                if semitone_diff == 0:
                    continue  # No transposition needed

                # Process each track in the song
                for track_id, track, track_name in song_tracks:
                    # Skip non-tonal tracks
                    if "perc" in track_name.lower() or "drums" in track_name.lower():
                        continue

                    # Find all audio clips in the track
                    clips = track.findall(".//AudioClip")
                    for clip in clips:
                        # Get clip duration
                        start_elem = clip.find(".//LomId[@Value='0']/CurrentStart")
                        end_elem = clip.find(".//LomId[@Value='0']/CurrentEnd")
                        if start_elem is None or end_elem is None:
                            continue
                        start = float(start_elem.get("Value"))
                        end = float(end_elem.get("Value"))
                        duration = end - start

                        # Enable Complex Warp mode
                        warp_mode = clip.find(".//WarpMode")
                        if warp_mode is None:
                            warp_mode = ET.SubElement(clip, "WarpMode")
                        warp_mode.set("Value", "4")  # 4 = Complex Warp

                        # Add warp markers
                        warp_elem = clip.find(".//WarpMarkers")
                        if warp_elem is None:
                            warp_elem = ET.SubElement(clip, "WarpMarkers")
                        warp_elem.clear()  # Clear existing warp markers
                        start_marker = ET.SubElement(warp_elem, "WarpMarker")
                        start_marker.set("SecTime", "0.0")
                        start_marker.set("BeatTime", "0.0")
                        end_marker = ET.SubElement(warp_elem, "WarpMarker")
                        end_marker.set("SecTime", str(duration / 4))  # Approximate seconds (assuming 120 BPM, 4 beats per second)
                        end_marker.set("BeatTime", str(duration))

                        # Set pitch adjustment
                        pitch_adjust = clip.find(".//PitchCoarse")
                        if pitch_adjust is None:
                            pitch_adjust = ET.SubElement(clip, "PitchCoarse")
                        pitch_adjust.set("Value", str(semitone_diff))

            # Process routing, muting, and volume adjustments
            routing_col, instruction_col = campus_columns[selected_campus]
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
                        st.warning(f"Invalid dB value '{instruction}' for track '{track_name}' in campus '{selected_campus}'. Skipping volume adjustment.")

                routing_dict = map_channel_to_target(channel, channel_map)
                if routing_dict is None:
                    continue

                # Routing Logic
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

                # Mute Logic
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

                # Volume Adjustment Logic
                if db_reduction is not None and db_reduction != 0.0:
                    volume = mixer.find("Volume")
                    if volume is None:
                        volume = ET.SubElement(mixer, "Volume")
                        manual_volume = ET.SubElement(volume, "Manual")
                        manual_volume.set("Value", "0.794328")
                    else:
                        manual_volume = volume.find("Manual")
                        if manual_volume is None:
                            manual_volume = ET.SubElement(volume, "Manual")
                            manual_volume.set("Value", "0.794328")

                    current_volume = float(manual_volume.get("Value"))
                    current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                    new_db = current_db + db_reduction
                    new_volume = 10 ** (new_db / 20) if new_db > -float('inf') else 0.0
                    manual_volume.set("Value", str(new_volume))

            # Save modified XML
            tree.write(temp_modified_xml, encoding="utf-8", xml_declaration=True)

            # Recompress to .als
            output_buffer = BytesIO()
            with open(temp_modified_xml, "rb") as f_in:
                with gzip.open(output_buffer, "wb") as f_out:
                    f_out.write(f_in.read())

            base_name = os.path.splitext(original_filename)[0]
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

    # Extract campus names and their corresponding routing/instruction columns
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

    # Generate the channel map dynamically
    channel_map = generate_channel_map(df, campus_columns)

    # Campus selection dropdown
    selected_campus = st.selectbox("Select Campus", CAMPUSES)

    # File uploader
    uploaded_files = st.file_uploader(f"Select Ableton Live (.als) Files for {selected_campus}", type=["als"], accept_multiple_files=True)

    if uploaded_files:
        song_tuning_info = {}
        keys = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        for uploaded_file in uploaded_files:
            # Decompress to XML to group tracks into songs
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_xml = os.path.join(temp_dir, "temp.xml")
                file_bytes = BytesIO(uploaded_file.read())
                with gzip.open(file_bytes, "rb") as f_in:
                    with open(temp_xml, "wb") as f_out:
                        f_out.write(f_in.read())
                tree = ET.parse(temp_xml)
                root = tree.getroot()
                songs = group_tracks_into_songs(root)

            # Display dropdowns for each song to select original and target keys
            st.subheader(f"Set Tuning for Songs in {uploaded_file.name}")
            for song_idx, (song_key, song_tracks) in enumerate(songs.items()):
                song_start, song_end = song_key
                track_names = [track_name for _, _, track_name in song_tracks]
                st.write(f"Song {song_idx + 1} (Tracks: {', '.join(track_names)})")
                original_key = st.selectbox(
                    f"Select original key for Song {song_idx + 1}",
                    [""] + keys,
                    key=f"original_key_{uploaded_file.name}_{song_idx}"
                )
                target_key = st.selectbox(
                    f"Select target key for Song {song_idx + 1}",
                    [""] + keys,
                    key=f"target_key_{uploaded_file.name}_{song_idx}"
                )
                if original_key and target_key:
                    song_tuning_info[song_idx] = {
                        "original_key": original_key,
                        "target_key": target_key
                    }

        # Process each file
        processed_count = 0
        for uploaded_file in uploaded_files:
            file_bytes = BytesIO(uploaded_file.read())
            original_filename = uploaded_file.name

            if not original_filename.lower().endswith(".als"):
                st.warning(f"Skipping {original_filename}: Not an .als file.")
                continue

            with st.spinner(f"Processing {original_filename} for {selected_campus}..."):
                output_bytes, output_filename = process_als(
                    file_bytes, original_filename, selected_campus, df, campus_columns, channel_map, song_tuning_info
                )

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
