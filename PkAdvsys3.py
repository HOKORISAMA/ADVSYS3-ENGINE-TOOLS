# You can use this to pack advsys3 archives like arc.dat arca.dat but you'll need to change counter for arca.dat from 10000, alternatively you can check the file in a hex viewer for the counter 
import os
import struct
import argparse
import json

class ArcPacker:
    def __init__(self, output_file):
        self.output_file = output_file
        self.entries = []

    def add_entry(self, name, data, counter):
        size = len(data)
        entry = struct.pack('<I', size)  # pack size as uint32 little endian | These are the first 4 bytes of 10 bytes before each file name in the archive which denotes the size of file.
        entry += struct.pack('<I', counter)  # pack the counter as uint32 little endian | These 4 bytes works as index starting from 0 with increment of + 1 with each file.
        entry += struct.pack('<H', len(name))  # pack name length as uint16 little endian
        entry += name.encode('utf-8')  # encode name as utf-8
        entry += data
        self.entries.append(entry)

    def write_archive(self):
        with open(self.output_file, 'wb') as f:
            for entry in self.entries:
                f.write(entry)
            # Add 4 bytes indicating end of archive
            f.write(b'\x00\x00\x00\x00')
        print(f"Archive '{self.output_file}' created successfully.")

def pack_directory(input_dir, output_file, order_file):
    packer = ArcPacker(output_file)
    
    with open(order_file, 'r') as json_file:
        order_data = json.load(json_file)
    
    counter = 0
    special_file_found = False
    
    for i, entry in enumerate(order_data):
        file_name = entry['name']
        file_path = os.path.join(input_dir, file_name)
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        if file_name == "system_setup_ss":
            counter = 10000  # From this file counter changes to 10000.
            special_file_found = True
        
        packer.add_entry(file_name, data, counter)
        
        if special_file_found:
            counter += 1
        else:
            counter = i + 1
    
    packer.write_archive()

def main():
    parser = argparse.ArgumentParser(description='Pack files in a directory into an AdvSys3 engine resource archive based on a specified order in a JSON file.')
    parser.add_argument('input_dir', help='Input directory containing files to pack')
    parser.add_argument('output_file', help='Output archive file path')
    parser.add_argument('order_file', help='JSON file specifying the order of files to pack')
    args = parser.parse_args()

    pack_directory(args.input_dir, args.output_file, args.order_file)

if __name__ == "__main__":
    main()
