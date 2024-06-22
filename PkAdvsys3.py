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
        entry = struct.pack('<I', size)  # pack size as uint32 little endian
        entry += struct.pack('<I', counter)  # pack the counter as uint32 little endian
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

    counter = 0 # This is to pack arc.dat
   # counter = 100000 remove the # to pack arca.dat
    special_file_found = False
    
    for i, entry in enumerate(order_data):
        file_name = entry['name']
        file_path = os.path.join(input_dir, file_name)
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Remove the file extension
        file_name_no_ext = os.path.splitext(file_name)[0]
        
        if file_name == "system_setup_ss":
            counter = 1000
            special_file_found = True
        
        packer.add_entry(file_name_no_ext, data, counter)
        
        if special_file_found:
            counter += 1
        else:
            counter += 1  # Increment counter by 1 for each file

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
