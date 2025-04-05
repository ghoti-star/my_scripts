import logging

# Configure logging to a file
logging.basicConfig(filename='ableton_router.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def process_als(input_file_bytes, original_filename):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_xml = os.path.join(temp_dir, "temp.xml")
            temp_modified_xml = os.path.join(temp_dir, "temp_modified.xml")

            with gzip.open(input_file_bytes, "rb") as f_in:
                with open(temp_xml, "wb") as f_out:
                    f_out.write(f_in.read())

            tree = ET.parse(temp_xml)
            root = tree.getroot()

            for track_type in ["AudioTrack", "MidiTrack", "GroupTrack"]:
                for track in root.findall(f".//{track_type}"):
                    name_elem = track.find(".//Name/EffectiveName")
                    track_name = name_elem.get("Value") if name_elem is not None else None

                    if not track_name or track_name.strip() == "":
                        logging.info(f"Skipping track with no name or empty name, XML Path: {track.tag}")
                        continue

                    device_chain = track.find("DeviceChain")
                    if device_chain is None:
                        logging.info(f"No DeviceChain found for {track_name}, creating one, XML Path: {track.tag}")
                        device_chain = ET.SubElement(track, "DeviceChain")

                    output_elem = device_chain.find("AudioOutputRouting")
                    if output_elem is None:
                        logging.info(f"No AudioOutputRouting found for {track_name}, creating one, XML Path: {track.tag}")
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

                    current_target = target_elem.get("Value", "None") if target_elem is not None else "None"
                    current_upper = upper_elem.get("Value", "None") if upper_elem is not None else "None"
                    current_lower = lower_elem.get("Value", "None") if lower_elem is not None else "None"
                    current_routing = f"Target: {current_target}, Upper: {current_upper}, Lower: {current_lower}"
                    logging.info(f"Track: {track_name}, Current Routing: {current_routing}, XML Path: {track.tag}")

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
                            logging.info(f"Updated Routing: {track_name} → {routing_dict['Target']} ({routing_dict['LowerDisplayString']})")
                            logging.info(f"Final AudioOutputRouting for {track_name}:")
                            logging.info(ET.tostring(output_elem, encoding='unicode').strip())
                            logging.info(f"Parent DeviceChain for {track_name}:")
                            logging.info(ET.tostring(device_chain, encoding='unicode').strip())
                            found_match = True
                            break

                    if not found_match:
                        logging.info(f"No matching routing for {track_name}—keeping current routing: {current_routing}")

                    mixer = device_chain.find("Mixer")
                    if mixer is None:
                        logging.info(f"No Mixer found for {track_name}, creating one, XML Path: {track.tag}")
                        mixer = ET.SubElement(device_chain, "Mixer")

                    speaker = mixer.find("Speaker")
                    if speaker is None:
                        logging.info(f"No Speaker found for {track_name}, creating one, XML Path: {track.tag}")
                        speaker = ET.SubElement(mixer, "Speaker")
                        manual_speaker = ET.SubElement(speaker, "Manual")
                        manual_speaker.set("Value", "true")
                    else:
                        manual_speaker = speaker.find("Manual")
                        if manual_speaker is None:
                            manual_speaker = ET.SubElement(speaker, "Manual")
                            manual_speaker.set("Value", "true")

                    current_speaker_state = manual_speaker.get("Value")
                    if track_name.upper() in MUTE_TRACKS:
                        manual_speaker.set("Value", "false")
                        logging.info(f"Muted track: {track_name} (Speaker was {current_speaker_state})")

                    volume = mixer.find("Volume")
                    if volume is None:
                        logging.info(f"No Volume found for {track_name}, creating one, XML Path: {track.tag}")
                        volume = ET.SubElement(mixer, "Volume")
                        manual_volume = ET.SubElement(volume, "Manual")
                        manual_volume.set("Value", "0.794328")
                    else:
                        manual_volume = volume.find("Manual")
                        if manual_volume is None:
                            manual_volume = ET.SubElement(volume, "Manual")
                            manual_volume.set("Value", "0.794328")

                    current_volume = float(manual_volume.get("Value"))
                    if track_name.upper() in TURN_DOWN_TRACKS:
                        current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                        new_db = current_db + VOLUME_REDUCTION_DB
                        new_volume = 10 ** (new_db / 20) if new_db > -float('inf') else 0.0
                        manual_volume.set("Value", str(new_volume))
                        logging.info(f"Adjusted volume for {track_name}: {current_volume} ({current_db:.2f} dB) → {new_volume} ({new_db:.2f} dB)")

            tree.write(temp_modified_xml, encoding="utf-8", xml_declaration=True)

            output_buffer = BytesIO()
            with open(temp_modified_xml, "rb") as f_in:
                with gzip.open(output_buffer, "wb") as f_out:
                    f_out.write(f_in.read())

            base_name = os.path.splitext(original_filename)[0]
            output_filename = f"{base_name}_routed.als"

            return output_buffer.getvalue(), output_filename

    except Exception as e:
        st.error(f"Error: Failed to process {original_filename}: {str(e)}")
        return None, None
