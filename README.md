# Firmware extraction scripts for Surface SAM firmware

Firmware extraction and unpacking scripts for Surface System Aggregator Module (SAM) firmware UEFI capsules.

## Usage

1. Extract UEFI capsule via:
   ```bash
   ./uefi-unwrap.py SurfaceSAM_1.108.139.bin SurfaceSAM_1.108.139.fwimg
   ```
   This may generate multiple firmware image files.
2. Extract (one) Firmware Image via:
   ```bash
   ./uefi-unwrap.py SurfaceSAM_1.108.139.0.fwimg SurfaceSAM_1.108.139.img
   ```
3. Open image with ghidra, have fun...
