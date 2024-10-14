import argparse
import os
import struct
from PIL import Image
import numpy as np

class BitStreamWriter:
    def __init__(self, stream):
        self.stream = stream
        self.buffer = 0
        self.buffer_size = 0

    def write_bits(self, value, num_bits):
        self.buffer = (self.buffer << num_bits) | value
        self.buffer_size += num_bits

        while self.buffer_size >= 8:
            self.buffer_size -= 8
            byte = (self.buffer >> self.buffer_size) & 0xFF
            self.stream.write(bytes([byte]))

    def flush(self):
        if self.buffer_size > 0:
            byte = (self.buffer << (8 - self.buffer_size)) & 0xFF
            self.stream.write(bytes([byte]))
            self.buffer = 0
            self.buffer_size = 0

def write_metadata(stream, width, height, bpp, data_size):
    header = struct.pack('<I', data_size)
    header += b'GWD'
    header += struct.pack('>HHB', width, height, bpp)
    stream.write(header)

def pack(stream, image_data, width, height, bpp):
    bit_stream = BitStreamWriter(stream)

    for y in range(height):
        for c in range(3 if bpp == 24 else 1):
            line = image_data[y, :, c]
            encoded_line = delta_encode_line(line)
            write_line(bit_stream, encoded_line)

    bit_stream.flush()

def delta_encode_line(line):
    encoded_line = np.zeros_like(line)
    encoded_line[0] = line[0]

    for i in range(1, len(line)):
        encoded_line[i] = encode_delta(line[i], line[i - 1])

    return encoded_line

def encode_delta(curr, prev):
    prev = prev if prev < 128 else 255 - prev
    if 2 * prev < curr:
        v = curr
    elif curr & 1:
        v = prev + ((curr + 1) >> 1)
    else:
        v = prev - (curr >> 1)
    return v if prev < 128 else 255 - v

def write_line(bit_stream, line):
    width = len(line)
    dst = 0
    while dst < width:
        count = get_run_length(line, dst)
        if count > 1:
            bit_stream.write_bits(0, 3)  # length = 0 for runs
            write_count(bit_stream, count - 1)
            dst += count
        else:
            bit_length = get_bit_length(line[dst])
            bit_stream.write_bits(bit_length, 3)
            bit_stream.write_bits(line[dst], bit_length + 1)
            dst += 1

def get_run_length(line, pos):
    length = 1
    while pos + length < len(line) and line[pos] == line[pos + length] and length < 255:
        length += 1
    return length

def get_bit_length(value):
    length = 0
    while value > 0:
        value >>= 1
        length += 1
    return length - 1

def write_count(bit_stream, count):
    n = 1
    while count > (1 << n) - 2:
        n += 1
    bit_stream.write_bits(n - 1, 3)  # 3-bit count
    bit_stream.write_bits(count - ((1 << n) - 2), n)

def process_directory(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith('.png'):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, os.path.splitext(filename)[0] + '.gwd')

            try:
                with Image.open(input_file) as img:
                    img = img.convert('RGB')
                    image_data = np.array(img)
                    height, width, _ = image_data.shape
                    bpp = 24
                    data_size = height * width * (bpp // 8)

                    with open(output_file, 'wb') as stream:
                        write_metadata(stream, width, height, bpp, data_size)
                        pack(stream, image_data, width, height, bpp)
                        print(f"Converted {filename} to {output_file}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PNG images to GWD")
    parser.add_argument("input_dir", help="Input directory containing PNG files")
    parser.add_argument("output_dir", help="Output directory for GWD files")
    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)
