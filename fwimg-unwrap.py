#!/usr/bin/env python3
import ctypes
import sys


class ImageFileHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('file_header_size', ctypes.c_uint32),
        ('unknown', ctypes.c_uint32 * 2),
        ('header_offset', ctypes.c_uint32),
        ('image_offset', ctypes.c_uint32),
    ]


class ImageHeader1(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('header_size', ctypes.c_uint32),
        ('unknown1', ctypes.c_uint32 * 7),
        ('header2_offset', ctypes.c_uint32),
        ('unknown2', ctypes.c_uint32 * 2),
        ('header3_offset', ctypes.c_uint32),
    ]


class ImageHeader2(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('header_size', ctypes.c_uint32),
        ('unknown1', ctypes.c_uint32 * 5),
        ('image_offset', ctypes.c_uint32),
        ('unknown2', ctypes.c_uint32),
        ('image_size', ctypes.c_uint32),
    ]


class ImageHeader3(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('header_size', ctypes.c_uint32),
        ('unknown1', ctypes.c_uint32 * 5),
    ]


def main():
    file_in = sys.argv[1]
    file_out = sys.argv[2]

    with open(file_in, 'rb') as fd:
        data = bytes(fd.read())

    header = ImageFileHeader.from_buffer_copy(data)
    print(f"IMAGE_FILE_HEADER:")
    print(f"  FileHeaderSize:         {header.file_header_size}")
    print(f"  HeaderStart:            {header.header_offset}")
    print(f"  ImageStart:             {header.image_offset}")
    print()

    pdata = data[header.header_offset:]

    header1 = ImageHeader1.from_buffer_copy(pdata)
    print(f"IMAGE_HEADER1:")
    print(f"  HeaderSize:             {header1.header_size}")
    print(f"  Header2Offset:          {header1.header2_offset}")
    print(f"  Header3Offset:          {header1.header3_offset}")
    print()

    if header1.header_size < ctypes.sizeof(ImageHeader1):
        print("Error: Invalid header size (1)")
        sys.exit(1)

    pdata = pdata[header1.header_size:]

    header2 = ImageHeader2.from_buffer_copy(pdata)
    print(f"IMAGE_HEADER2:")
    print(f"  HeaderSize:             {header2.header_size}")
    print(f"  ImageOffset:            {header2.image_offset}")
    print(f"  ImageSize:              {header2.image_size}")
    print()

    if header2.header_size < ctypes.sizeof(ImageHeader2):
        print("Error: Invalid header size (2)")
        sys.exit(1)

    pdata = pdata[header2.header_size:]

    header3 = ImageHeader3.from_buffer_copy(pdata)
    print(f"IMAGE_HEADER3:")
    print(f"  HeaderSize:             {header3.header_size}")
    print()

    if header3.header_size < ctypes.sizeof(ImageHeader3):
        print("Error: Invalid header size (3)")
        sys.exit(1)

    if header2.image_offset + header2.image_size != len(data):
        print("Error: Invalid image data size")
        sys.exit(1)

    imgdata = data[header2.image_offset:header2.image_offset+header2.image_size]
    with open(file_out, 'wb') as fd:
        fd.write(imgdata)


if __name__ == '__main__':
    main()
