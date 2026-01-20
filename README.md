# exif-stats
Get focal length and shutter speed distribution from photos

## Summary
This script analyzes JPEG photos from a specified folder, reads their EXIF data, and generates histogram visualizations showing the distribution of:
- Focal length (mm)
- Aperture (f-number)
- Shutter speed (seconds)

The generated diagrams are saved as PNG images in the `output/` directory.

## Features
- **Camera Discovery**: List all unique camera models found in a directory
- **Camera Filtering**: Analyze photos from specific camera models only
- **Recursive Scanning**: Automatically scans subdirectories
- **Multiple Image Formats**: Supports .jpg, .jpeg, .jpe, .jfif, .heic, and .heif files
- **Smart EXIF Parsing**: Combines manufacturer and model names for accurate camera identification

## Installation

1. Clone the repository:
```bash
git clone https://github.com/t-bence/exif-stats.git
cd exif-stats
```

2. Create and activate a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Show help and available options:
```bash
python focal_stats.py
```

List all camera models in a directory:
```bash
python focal_stats.py -l -p /path/to/photos
```

Generate histograms for all photos:
```bash
python focal_stats.py -p /path/to/photos
```

Filter by camera model:
```bash
python focal_stats.py -p /path/to/photos -t "Sony"
```

### Options
- `-p, --path DIR`: Directory to scan for JPEG files (required)
- `-t, --type CAMERA`: Filter photos by camera model (case-insensitive substring match)
- `-l, --list-cameras`: Scan directory and list all camera models, then exit
- `-h, --help`: Show help message and exit

### Output
The script generates three histogram PNG files in the `output/` directory:
- `focal_distance.png` - Distribution of focal lengths used
- `f_number.png` - Distribution of aperture values
- `shutter_speed.png` - Distribution of shutter speeds (logarithmic scale)

## Requirements
- Python 3.10+
- Pillow >= 9.0.0
- matplotlib >= 3.5.0
- numpy >= 1.21.0
- pillow-heif >= 0.16.0 (for HEIF/HEIC support)
