import gzip
import xml.etree.ElementTree as ET
import os
import tempfile
import math
from AppKit import NSOpenPanel, NSOKButton, NSApplication, NSAlert, NSInformationalAlertStyle
from PyQt5.QtWidgets import QApplication, QDialog, QVBoxLayout, QLabel, QComboBox, QPushButton
import sys

# Routing maps for each campus (placeholders—adjust as needed)
ROUTING_MAPS = {
    "Apollo Beach Campus": {
        "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "HOOKS": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "AG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "BGV": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    },
    "Apollo Beach Español Campus": {
        "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "HOOKS": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "AG": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "BGV": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    },
    "Brandon Campus": {
        "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "HOOKS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "AG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "GUITAR": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "BGV": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    },
    "Brandon Español Campus": {
        "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "HOOKS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "AG": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "GUITAR": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "BGV": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    },
    "Riverview Campus": {
        "GUIDE": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CUES": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "CLICK": {"Target": "AudioOut/External/M0", "LowerDisplayString": "1"},
        "SUB BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "BASS": {"Target": "AudioOut/External/M1", "LowerDisplayString": "2"},
        "HOOKS": {"Target": "AudioOut/External/S1", "LowerDisplayString": "3/4"},
        "AG": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "GUITAR": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "BGV": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "KEYS": {"Target": "AudioOut/External/S2", "LowerDisplayString": "5/6"},
        "DRUMS": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
        "PERC": {"Target": "AudioOut/External/S3", "LowerDisplayString": "7/8"},
    }
}

MUTE_TRACKS = {"BASS", "DRUMS", "AG", "ACOUSTIC", "ACOUSTIC GUITAR", "PIANO"}
TURN_DOWN_TRACKS = {"CHOIR", "BGV", "BGVS", "GANG VOCALS", "VOCALS", "CHOIR 1", "CHOIR 2", "GANG"}
VOLUME_REDUCTION_DB = -10

class CampusSelectionDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Select Campus")
        self.setFixedSize(300, 100)
        layout = QVBoxLayout()

        label = QLabel("Please select your campus:")
        layout.addWidget(label)

        self.campus_combo = QComboBox()
        self.campus_combo.addItems(ROUTING_MAPS.keys())
        layout.addWidget(self.campus_combo)

        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        layout.addWidget(ok_button)

        self.setLayout(layout)

    def get_selected_campus(self):
        return self.campus_combo.currentText()

def select_campus():
    app = QApplication(sys.argv)
    dialog = CampusSelectionDialog()
    if dialog.exec_():
        return dialog.get_selected_campus()
    else:
        print("Campus selection cancelled.")
        return None

def process_als(input_file, output_file, routing_map):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_xml = os.path.join(temp_dir, "temp.xml")
            temp_modified_xml = os.path.join(temp_dir, "temp_modified.xml")

            with gzip.open(input_file, "rb") as f_in:
                with open(temp_xml, "wb") as f_out:
                    f_out.write(f_in.read())

            tree = ET.parse(temp_xml)
            root = tree.getroot()

            for track_type in ["AudioTrack", "MidiTrack", "GroupTrack"]:
                for track in root.findall(f".//{track_type}"):
                    name_elem = track.find(".//Name/EffectiveName")
                    track_name = name_elem.get("Value") if name_elem is not None else None

                    if not track_name or track_name.strip() == "":
                        print(f"Skipping track with no name or empty name")
                        continue

                    device_chain = track.find("DeviceChain") or ET.SubElement(track, "DeviceChain")
                    output_elem = device_chain.find("AudioOutputRouting") or ET.SubElement(device_chain, "AudioOutputRouting")
                    target_elem = output_elem.find("Target") or ET.SubElement(output_elem, "Target")
                    upper_elem = output_elem.find("UpperDisplayString") or ET.SubElement(output_elem, "UpperDisplayString")
                    lower_elem = output_elem.find("LowerDisplayString") or ET.SubElement(output_elem, "LowerDisplayString")
                    mpe_settings = output_elem.find("MpeSettings") or ET.SubElement(output_elem, "MpeSettings")

                    for keyword, routing_dict in routing_map.items():
                        if keyword.upper() == track_name.upper():
                            target_elem.set("Value", routing_dict["Target"])
                            upper_elem.set("Value", "Ext. Out")
                            lower_elem.set("Value", routing_dict["LowerDisplayString"])
                            mpe_settings.clear()
                            print(f"Updated Routing: {track_name} → {routing_dict['Target']} ({routing_dict['LowerDisplayString']})")
                            break

                    mixer = device_chain.find("Mixer") or ET.SubElement(device_chain, "Mixer")
                    speaker = mixer.find("Speaker") or ET.SubElement(mixer, "Speaker")
                    manual_speaker = speaker.find("Manual") or ET.SubElement(speaker, "Manual", {"Value": "true"})
                    if track_name.upper() in MUTE_TRACKS:
                        manual_speaker.set("Value", "false")
                        print(f"Muted track: {track_name}")

                    volume = mixer.find("Volume") or ET.SubElement(mixer, "Volume")
                    manual_volume = volume.find("Manual") or ET.SubElement(volume, "Manual", {"Value": "0.794328"})
                    current_volume = float(manual_volume.get("Value"))
                    if track_name.upper() in TURN_DOWN_TRACKS:
                        current_db = 20 * math.log10(current_volume) if current_volume > 0 else -float('inf')
                        new_db = current_db + VOLUME_REDUCTION_DB
                        new_volume = 10 ** (new_db / 20) if new_db > -float('inf') else 0.0
                        manual_volume.set("Value", str(new_volume))
                        print(f"Adjusted volume for {track_name}: {current_db:.2f} dB → {new_db:.2f} dB")

            tree.write(temp_modified_xml, encoding="utf-8", xml_declaration=True)
            with open(temp_modified_xml, "rb") as f_in:
                with gzip.open(output_file, "wb") as f_out:
                    f_out.write(f_in.read())
        return True

    except Exception as e:
        print(f"Error: Failed to process {input_file}: {str(e)}")
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Error Processing File")
        alert.setInformativeText_(f"Failed to process {input_file}: {str(e)}")
        alert.setAlertStyle_(NSInformationalAlertStyle)
        alert.runModal()
        return False

def select_and_process_files():
    selected_campus = select_campus()
    if not selected_campus:
        return

    routing_map = ROUTING_MAPS[selected_campus]
    print(f"Using routing map for {selected_campus}")

    app = NSApplication.sharedApplication()
    open_panel = NSOpenPanel.openPanel()
    open_panel.setTitle_("Select Ableton Live (.als) Files")
    open_panel.setAllowsMultipleSelection_(True)
    open_panel.setCanChooseDirectories_(False)
    open_panel.setCanChooseFiles_(True)
    open_panel.setAllowedFileTypes_(["als"])
    
    if open_panel.runModal() != NSOKButton:
        print("No files selected. Exiting.")
        return

    files = [url.path() for url in open_panel.URLs()]
    if not files:
        print("No files selected. Exiting.")
        return

    processed_count = 0
    for input_file in files:
        if not input_file.lower().endswith(".als"):
            print(f"Skipping {input_file}: Not an .als file.")
            continue

        base_name = os.path.splitext(input_file)[0]
        output_filename = f"{base_name}_routed_for_{selected_campus.replace(' ', '_')}.als"
        counter = 1
        while os.path.exists(output_filename):
            output_filename = f"{base_name}_routed_for_{selected_campus.replace(' ', '_')}_{counter}.als"
            counter += 1

        if process_als(input_file, output_filename, routing_map):
            processed_count += 1
            print(f"Processed {input_file} -> {output_filename}")
        else:
            print(f"Failed to process {input_file}")

    alert = NSAlert.alloc().init()
    alert.setMessageText_("Processing Complete")
    alert.setInformativeText_(f"Processed {processed_count} files successfully using {selected_campus} routing.")
    alert.setAlertStyle_(NSInformationalAlertStyle)
    alert.runModal()

if __name__ == "__main__":
    try:
        select_and_process_files()
    except Exception as e:
        print(f"Fatal Error: {str(e)}")
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Fatal Error")
        alert.setInformativeText_(f"An unexpected error occurred: {str(e)}")
        alert.setAlertStyle_(NSInformationalAlertStyle)
        alert.runModal()
