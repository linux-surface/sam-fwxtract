#!/usr/bin/env python3
import ctypes
import sys


class Guid(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('data_1', ctypes.c_uint32),
        ('data_2', ctypes.c_uint16),
        ('data_3', ctypes.c_uint16),
        ('data_4', ctypes.c_uint8 * 8),
    ]

    def __str__(self):
        return "{:08x}-{:04x}-{:04x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}" \
            .format(self.data_1, self.data_2, self.data_3, *self.data_4)

    def __eq__(self, other):
        return self.data_1 == other.data_1 and self.data_2 == other.data_2 and \
               self.data_3 == other.data_3 and \
               all(x == y for x, y in zip(self.data_4, other.data_4))


class EfiCapsuleHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('guid', Guid),
        ('header_size', ctypes.c_uint32),
        ('flags', ctypes.c_uint32),
        ('image_size', ctypes.c_uint32),
    ]


class EfiFirmwareManagementCapsuleHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('version', ctypes.c_uint32),
        ('embedded_driver_count', ctypes.c_uint16),
        ('payload_item_count', ctypes.c_uint16),
    ]


class EfiFirmwareManagementCapsuleImageHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('version', ctypes.c_uint32),
        ('update_image_type_id', Guid),
        ('update_image_index', ctypes.c_uint8),
        ('reserved', ctypes.c_uint8 * 3),
        ('update_image_size', ctypes.c_uint32),
        ('update_vendor_code_size', ctypes.c_uint32),
        ('update_hardware_instance', ctypes.c_uint64),
    ]


class WinCertificate(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('length', ctypes.c_uint32),
        ('revision', ctypes.c_uint16),
        ('certificate_type', ctypes.c_uint16),
    ]


class WinCertificateUefiGuid(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('hdr', WinCertificate),
        ('cert_type', Guid),
    ]


class EfiFirmwareImageAuthentication(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('monotonic_count', ctypes.c_uint64),
        ('auth_info', WinCertificateUefiGuid),
    ]


class SurfaceFirmwareVersion(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('c', ctypes.c_uint8),
        ('b', ctypes.c_uint16),
        ('a', ctypes.c_uint8),
    ]

    def __str__(self):
        return f"{self.a}.{self.b}.{self.c}"


class SurfaceFirmwareHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('unknown', ctypes.c_uint8 * 7),
        ('num_chunks', ctypes.c_uint16),
        ('payload_size', ctypes.c_uint32),
        ('firmware_version', SurfaceFirmwareVersion)
    ]


class SurfaceFirmwareImageHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('unknown', ctypes.c_uint8 * 16),
    ]


class ChunkHeader(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ('address', ctypes.c_uint32),
        ('size', ctypes.c_uint8),
    ]


EFI_FIRMWARE_MANAGEMENT_CAPSULE_GUID = Guid(0x6dcbd5ed, 0xe82d, 0x4c44,
                                            (0xbd, 0xa1, 0x71, 0x94, 0x19, 0x9a, 0xd9, 0x2a))


def index_file_name(basename, index):
    parts = basename.split('.')

    if len(parts) > 1:
        return f"{'.'.join(parts[:-1])}.{index}.{parts[-1]}"
    else:
        return f"{basename}.{index}"


def main():
    file_in = sys.argv[1]
    file_out = sys.argv[2]

    with open(file_in, 'rb') as fd:
        data = bytes(fd.read())

    header = EfiCapsuleHeader.from_buffer_copy(data)
    print(f"EFI_CAPSULE_HEADER:")
    print(f"  CapsuleGuid:            {header.guid}")
    print(f"  HeaderSize:             {header.header_size}")
    print(f"  Flags:                  {header.flags:08x}h")
    print(f"  CapsuleImageSize:       {header.image_size}")
    print()

    if header.image_size != len(data):
        print(f"Error: Invalid image size, expected {header.image_size}, got {len(data)}")
        sys.exit(1)

    if header.header_size < ctypes.sizeof(EfiCapsuleHeader):
        print(f"Error: Invalid header size, expected at least {ctypes.sizeof(EfiCapsuleHeader)}, "
              f"got {header.size}")
        sys.exit(1)

    if header.guid != EFI_FIRMWARE_MANAGEMENT_CAPSULE_GUID:
        print(f"Error: Unsupported GUID, expected {EFI_FIRMWARE_MANAGEMENT_CAPSULE_GUID}, "
              f"got {header.guid}")
        sys.exit(1)

    data = data[header.header_size:]

    header2 = EfiFirmwareManagementCapsuleHeader.from_buffer_copy(data)
    print(f"EFI_FIRMWARE_MANAGEMENT_CAPSULE_HEADER:")
    print(f"  Version:                {header2.version}")
    print(f"  EmbeddedDriverCount:    {header2.embedded_driver_count}")
    print(f"  PayloadItemCount:       {header2.payload_item_count}")
    print()

    if header2.version != 1:
        print(f"Error: Unsupported version, expected 1, got {header2.version}")
        sys.exit(1)

    min_offset = ctypes.sizeof(EfiFirmwareManagementCapsuleHeader) \
        + (header2.embedded_driver_count + header2.payload_item_count) \
        * ctypes.sizeof(ctypes.c_uint64)

    for i in range(header2.payload_item_count):
        offset = ctypes.sizeof(EfiFirmwareManagementCapsuleHeader) \
            + (header2.embedded_driver_count + i) * ctypes.sizeof(ctypes.c_uint64)

        payload_offset = ctypes.c_uint64.from_buffer_copy(data[offset:]).value

        if payload_offset < min_offset:
            print(f"Error: Invalid offset, expected minimum {min_offset}, got {payload_offset}")
            sys.exit(1)

        pdata = data[payload_offset:]

        header3 = EfiFirmwareManagementCapsuleImageHeader.from_buffer_copy(pdata)
        print(f"EFI_FIRMWARE_MANAGEMENT_CAPSULE_IMAGE_HEADER:")
        print(f"  Version:                {header3.version}")
        print(f"  UpdateImageTypeId:      {header3.update_image_type_id}")
        print(f"  UpdateImageIndex:       {header3.update_image_index}")
        print(f"  UpdateImageSize:        {header3.update_image_size}")
        print(f"  UpdateVendorCodeSize:   {header3.update_vendor_code_size}")
        print(f"  UpdateHardwareInstance: {header3.update_hardware_instance}")
        print()

        if header3.version != 2:
            print(f"Warning: Unsupported version, expected 2, got {header3.version}, skipping")
            continue

        hdr_len = ctypes.sizeof(EfiFirmwareManagementCapsuleImageHeader)
        if header3.update_image_size > len(pdata) - hdr_len:
            print(f"Error: UpdateImageSize larger than available data, "
                  f"expected at most {len(pdata)}, got {header3.update_image_size}")
            sys.exit(1)

        pdata = pdata[ctypes.sizeof(EfiFirmwareManagementCapsuleImageHeader):]
        pdata = pdata[:header3.update_image_size]

        header4 = EfiFirmwareImageAuthentication.from_buffer_copy(pdata)
        print(f"EFI_FIRMWARE_IMAGE_AUTHENTICATION:")
        print(f"  MonotonicCount:         {header4.monotonic_count}")
        print(f"  AuthInfo:")
        print(f"    Hdr:")
        print(f"      dwLength:           {header4.auth_info.hdr.length}")
        print(f"      wRevision:          {header4.auth_info.hdr.revision}")
        print(f"      wCertificateType:   {header4.auth_info.hdr.certificate_type}")
        print(f"    CertType:             {header4.auth_info.cert_type}")
        print()

        pdata = pdata[ctypes.sizeof(EfiFirmwareImageAuthentication):]
        pdata = pdata[header4.auth_info.hdr.length:]

        header5 = SurfaceFirmwareHeader.from_buffer_copy(pdata)
        print(f"SURFACE_FIRMWARE_HEADER:")
        print(f"  <unknown data>")
        print(f"  NumChunks:              {header5.num_chunks}")
        print(f"  PayloadSize:            {header5.payload_size}")
        print(f"  FirmwareVersion:        {header5.firmware_version}")
        print()

        hdr_len = ctypes.sizeof(SurfaceFirmwareHeader)
        if header5.payload_size > len(pdata) - hdr_len:
            print(f"Error: PayloadSize larger than available data, "
                  f"expected at most {len(pdata)}, got {header3.update_image_size}")
            sys.exit(1)

        pdata = pdata[hdr_len:]

        images = []
        while len(pdata):
            header6 = SurfaceFirmwareImageHeader.from_buffer_copy(pdata)
            print(f"SURFACE_FIRMWARE_IMAGE_HEADER:")
            print(f"  <unknown data>")

            pdata = pdata[ctypes.sizeof(SurfaceFirmwareImageHeader):]

            imgdata = bytes()
            for c in range(header5.num_chunks):
                chunk_hdr = ChunkHeader.from_buffer_copy(pdata)
                chunk_pld = pdata[ctypes.sizeof(ChunkHeader):chunk_hdr.size]

                if len(imgdata) != chunk_hdr.address:
                    print(f"Error: Images with non-consecutive chunks are not supported yet")
                    sys.exit(1)

                pdata = pdata[ctypes.sizeof(ChunkHeader):]

                imgdata += pdata[:chunk_hdr.size]

                pdata = pdata[chunk_hdr.size:]

            print(f"  Image of size:          {len(imgdata)}")
            print()
            images.append(imgdata)

        for i, img in enumerate(images):
            with open(index_file_name(file_out, i), 'wb') as fd:
                fd.write(img)


if __name__ == '__main__':
    main()
