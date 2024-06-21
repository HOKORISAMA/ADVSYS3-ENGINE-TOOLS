import argparse
import os
import struct
from PIL import Image
import numpy as np

class BitStream:
    def __init__(self, stream):
        self.stream = stream
        self.buffer = 0
        self.buffer_size = 0

    def get_bits(self, num_bits):
        while self.buffer_size < num_bits:
            new_byte = self.stream.read(1)
            if not new_byte:
                raise EOFError("End of stream")
            self.buffer = (self.buffer << 8) | ord(new_byte)
            self.buffer_size += 8

        result = self.buffer >> (self.buffer_size - num_bits)
        self.buffer_size -= num_bits
        self.buffer &= (1 << self.buffer_size) - 1  # Clear used bits
        return result

    def get_next_bit(self):
        return self.get_bits(1)

class GwdMetaData:
    def __init__(self, width, height, bpp, data_size):
        self.width = width
        self.height = height
        self.bpp = bpp
        self.data_size = data_size

def read_metadata(stream):
    header = stream.read(12)
    if len(header) != 12:
        return None
    if header[4:7].decode('ascii') != 'GWD':
        return None
    width = struct.unpack('>H', header[7:9])[0]
    height = struct.unpack('>H', header[9:11])[0]
    bpp = header[11]
    data_size = struct.unpack('<I', header[0:4])[0]
    return GwdMetaData(width, height, bpp, data_size)

def unpack(stream, meta):
    stream.seek(12)
    width, height, bpp = meta.width, meta.height, meta.bpp
    stride = width * bpp // 8
    output = np.zeros((height, width, 3 if bpp == 24 else 1), dtype=np.uint8)

    bit_stream = BitStream(stream)
    if bpp == 8:
        for y in range(height):
            output[y, :, 0] = fill_line(bit_stream, width)
    else:
        for y in range(height):
            for c in range(3):
                line = fill_line(bit_stream, width)
                output[y, :, c] = line

    if bpp == 24:
        stream.seek(4 + meta.data_size)
        if stream.read(1) == b'\x01':
            alpha_meta = read_metadata(stream)
            if alpha_meta and alpha_meta.bpp == 8 and alpha_meta.width == width and alpha_meta.height == height:
                alpha_stream = BitStream(stream)
                alpha_output = np.zeros((height, width), dtype=np.uint8)
                for y in range(height):
                    alpha_output[y, :] = fill_line(alpha_stream, width)
                alpha_output = 255 - alpha_output  # Invert alpha channel
                output = np.dstack((output, alpha_output))

    return output

def fill_line(bit_stream, width):
    line = np.zeros(width, dtype=np.uint8)
    dst = 0
    while dst < width:
        length = bit_stream.get_bits(3)
        if length == -1:
            raise EOFError("End of stream")
        count = get_count(bit_stream) + 1
        if length != 0:
            for _ in range(count):
                line[dst] = bit_stream.get_bits(length + 1)
                dst += 1
        else:
            dst += count

    for i in range(1, width):
        line[i] = delta_table(line[i], line[i-1])
    return line

# Precompute the delta table
DELTA_TABLE = []
for j in range(256):
    row = []
    for i in range(256):
        prev = i if i < 128 else 255 - i
        if 2 * prev < j:
            v = j
        elif j & 1:
            v = prev + ((j + 1) >> 1)
        else:
            v = prev - (j >> 1)
        row.append(v if i < 128 else 255 - v)
    DELTA_TABLE.append(row)

def delta_table(curr, prev):
    return DELTA_TABLE[curr][prev]

def get_count(bit_stream):
    n = 1
    while bit_stream.get_next_bit() == 0:
        n += 1
    return bit_stream.get_bits(n) + (1 << n) - 2

def save_image(image_data, width, height, bpp, output_file):
    if bpp == 8:
        image = Image.fromarray(image_data.reshape((height, width)), 'L')
    elif bpp == 24:
        image_data = image_data[:, :, ::-1]  # Convert BGR to RGB
        image = Image.fromarray(image_data, 'RGB')
    elif bpp == 32:
        image_data = image_data[:, :, [2, 1, 0, 3]]  # Convert BGRA to RGBA
        image = Image.fromarray(image_data, 'RGBA')
    else:
        raise ValueError(f"Unsupported bpp value: {bpp}")

    image.save(output_file)


def process_directory(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for filename in os.listdir(input_dir):
        if filename.endswith('.gwd'):
            input_file = os.path.join(input_dir, filename)
            output_file = os.path.join(output_dir, os.path.splitext(filename)[0] + '.png')

            try:
                with open(input_file, 'rb') as stream:
                    meta = read_metadata(stream)
                    if not meta:
                        print(f"Invalid GWD file: {filename}")
                        continue

                    image_data = unpack(stream, meta)
                    print(f"Saving image with width={meta.width}, height={meta.height}, bpp={meta.bpp}")
                    save_image(image_data, meta.width, meta.height, meta.bpp, output_file)
                    print(f"Converted {filename} to {output_file}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert GWD images to PNG")
    parser.add_argument("input_dir", help="Input directory containing GWD files")
    parser.add_argument("output_dir", help="Output directory for PNG files")
    args = parser.parse_args()

    process_directory(args.input_dir, args.output_dir)
