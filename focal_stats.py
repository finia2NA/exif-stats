import os
import argparse
from PIL import Image
import matplotlib.pyplot as plt
from numpy import asarray, logspace, log10

# Register HEIF/HEIC support
HEIF_SUPPORTED = False
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    pass  # pillow-heif not installed, HEIF/HEIC support disabled

def is_supported_image(filename):
    """Check if a file is a supported image format (JPEG or HEIF/HEIC)."""
    lower_name = filename.lower()

    # Always support JPEG formats
    if lower_name.endswith(('.jpg', '.jpeg', '.jpe', '.jfif')):
        return True

    # Only support HEIF/HEIC if library is available
    if HEIF_SUPPORTED and lower_name.endswith(('.heic', '.heif')):
        return True

    return False

def list_cameras(path):
    """Scan directory and return all unique camera models found in EXIF data."""
    cameras = set()

    for root, dirs, files in os.walk(path):
        for file in files:
            if is_supported_image(file):
                filename = os.path.join(root, file)

                try:
                    with Image.open(filename, 'r') as img:
                        exif_data = img.getexif()

                        if exif_data:
                            make = exif_data.get(271)  # Make (manufacturer)
                            model = exif_data.get(272)  # Model

                            # Combine make and model for full camera name
                            if make and model:
                                camera_name = f"{make} {model}".strip()
                                cameras.add(camera_name)
                            elif model:
                                cameras.add(model)
                            elif make:
                                cameras.add(make)
                except (IOError, OSError):
                    pass  # Skip files that can't be opened

    return sorted(cameras)

def get_camera_order(camera_data):
    """
    Return list of camera names sorted by total photo count (most photos first).
    The camera with the most photos will be placed at the bottom of stacked histograms.
    """
    camera_counts = {}
    for camera, data in camera_data.items():
        # Use 't' (shutter time) as the canonical count since all valid photos have it
        count = len(data['t'])
        camera_counts[camera] = count

    # Sort by count descending (most photos first = bottom of stack)
    return sorted(camera_counts.keys(), key=lambda c: camera_counts[c], reverse=True)

def get_camera_colors(cameras):
    """Generate distinct colors for each camera using matplotlib colormap."""
    import matplotlib

    if len(cameras) <= 10:
        cmap = matplotlib.colormaps.get_cmap('tab10')
        return [cmap(i) for i in range(len(cameras))]
    else:
        cmap = matplotlib.colormaps.get_cmap('tab20')
        return [cmap(i / len(cameras)) for i in range(len(cameras))]

def process_images(path, camera_type):
    camera_data = {}  # {camera_name: {'f': [], 't': [], 'focus': []}}

    # Create output directory if it doesn't exist
    output_dir = 'output'
    os.makedirs(output_dir, exist_ok=True)

    for root, dirs, files in os.walk(path):
        for file in files:

            if is_supported_image(file):
                filename = os.path.join(root, file)

                try:
                    with Image.open(filename, 'r') as img:
                        exif_data = img.getexif()

                        if exif_data:
                            try:
                                make = exif_data.get(271)  # Make (manufacturer)
                                model = exif_data.get(272)  # Model

                                # Build full camera name
                                if make and model:
                                    camera_name = f"{make} {model}".strip()
                                elif model:
                                    camera_name = model
                                elif make:
                                    camera_name = make
                                else:
                                    camera_name = None

                                # Check if camera matches filter
                                if camera_name and ((camera_type is None) or (camera_type.lower() in camera_name.lower())):
                                    # Get Exif IFD for camera settings
                                    exif_ifd = exif_data.get_ifd(34665) if 34665 in exif_data else {}

                                    # Read camera settings from Exif IFD
                                    time = exif_ifd.get(33434)  # ExposureTime
                                    stop = exif_ifd.get(33437)  # FNumber
                                    fd = exif_ifd.get(37386)    # FocalLength

                                    if time and stop and fd:
                                        # Initialize camera entry if needed
                                        if camera_name not in camera_data:
                                            camera_data[camera_name] = {'f': [], 't': [], 'focus': []}

                                        # Handle both rational tuples and float values
                                        if isinstance(stop, tuple):
                                            camera_data[camera_name]['f'].append(stop[0]/float(stop[1]))
                                        else:
                                            camera_data[camera_name]['f'].append(float(stop))

                                        if isinstance(time, tuple):
                                            camera_data[camera_name]['t'].append(time[0]/float(time[1]))
                                        else:
                                            camera_data[camera_name]['t'].append(float(time))

                                        if isinstance(fd, tuple):
                                            camera_data[camera_name]['focus'].append(fd[0]/float(fd[1]))
                                        else:
                                            camera_data[camera_name]['focus'].append(float(fd))
                            except (KeyError, TypeError, ZeroDivisionError):
                                print('Error while reading EXIF data in image {}'.format(filename))
                except (IOError, OSError) as e:
                    print('Error opening image {}: {}'.format(filename, e))


    total_photos = sum(len(data['t']) for data in camera_data.values())
    print('Number of photos: {}'.format(total_photos))

    # Generate stacked histograms broken down by camera
    if camera_data:
        cameras = get_camera_order(camera_data)
        colors = get_camera_colors(cameras)

        # Focal distance histogram
        focal_data = [asarray(camera_data[cam]['focus']) for cam in cameras if camera_data[cam]['focus']]
        if focal_data:
            plt.figure(figsize=(10, 6))
            labels = [cam for cam in cameras if camera_data[cam]['focus']]
            plt.hist(focal_data, bins=30, stacked=True, label=labels, color=colors[:len(labels)])
            plt.ylabel('Number of photos')
            plt.xlabel('Focal distance, mm')
            plt.legend(loc='upper right')
            plt.savefig(os.path.join(output_dir, 'focal_distance.png'))

        # F-number histogram
        f_data = [asarray(camera_data[cam]['f']) for cam in cameras if camera_data[cam]['f']]
        if f_data:
            plt.figure(figsize=(10, 6))
            labels = [cam for cam in cameras if camera_data[cam]['f']]
            plt.hist(f_data, bins=30, stacked=True, label=labels, color=colors[:len(labels)])
            plt.ylabel('Number of photos')
            plt.xlabel('f number')
            plt.legend(loc='upper right')
            plt.savefig(os.path.join(output_dir, 'f_number.png'))

        # Shutter speed histogram (logarithmic base-2 with photography notation)
        all_times = []
        for cam_data in camera_data.values():
            all_times.extend(cam_data['t'])

        if all_times:
            import numpy as np
            from matplotlib.ticker import FuncFormatter

            plt.figure(figsize=(10, 6))

            # Use log base-2 bins for shutter speed (doubles/halves are standard in photography)
            min_time = min(all_times)
            max_time = max(all_times)
            min_exp = np.floor(np.log2(min_time))
            max_exp = np.ceil(np.log2(max_time))
            bins = 2 ** np.linspace(min_exp - 1, max_exp, 30)

            t_data = [asarray(camera_data[cam]['t']) for cam in cameras if camera_data[cam]['t']]
            labels = [cam for cam in cameras if camera_data[cam]['t']]

            plt.hist(t_data, bins=bins, stacked=True, label=labels, color=colors[:len(labels)])
            plt.ylabel('Number of photos')
            plt.xlabel('Shutter speed')
            plt.gca().set_xscale("log", base=2)

            # Custom formatter for photography notation
            def shutter_speed_format(x, pos):
                if x >= 1:
                    # Seconds: 1", 2", 4", etc.
                    return f'{int(x)}"' if x == int(x) else f'{x:.1f}"'
                else:
                    # Fractions: show just denominator (250, 500, etc.)
                    denominator = 1 / x
                    return f'{int(round(denominator))}'

            # Use standard photography full-stop shutter speeds
            standard_speeds = [1/8000, 1/4000, 1/2000, 1/1000, 1/500, 1/250, 1/125, 1/60, 1/30, 1/15, 1/8, 1/4, 1/2, 1, 2, 4, 8, 16, 30]
            # Filter to only include speeds within data range
            valid_ticks = [s for s in standard_speeds if min_time/2 <= s <= max_time*2]
            if valid_ticks:
                plt.gca().set_xticks(valid_ticks)

            plt.gca().xaxis.set_major_formatter(FuncFormatter(shutter_speed_format))
            plt.legend(loc='upper right')
            plt.savefig(os.path.join(output_dir, 'shutter_speed.png'))

    return camera_data


if __name__ == '__main__':
    import sys

    parser = argparse.ArgumentParser(
        description='Analyze EXIF data from JPEG photos and generate histograms for focal length, aperture, and shutter speed.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s -l -p /Users/username/Pictures
  %(prog)s -p /Users/username/Pictures
  %(prog)s -p ~/Photos -t Canon
  %(prog)s --path /Users/username/Pictures --type "Nikon D850"
        '''
    )

    parser.add_argument(
        '-p', '--path',
        required=False,
        metavar='DIR',
        help='directory to scan for JPEG and HEIF/HEIC files'
    )

    parser.add_argument(
        '-t', '--type',
        default=None,
        metavar='CAMERA',
        help='filter photos by camera model (case-insensitive substring match)'
    )

    parser.add_argument(
        '-l', '--list-cameras',
        action='store_true',
        help='scan directory and list all camera models found, then exit'
    )

    args = parser.parse_args()

    # Show help if no path provided
    if args.path is None:
        parser.print_help()
        sys.exit(0)

    # List cameras mode
    if args.list_cameras:
        print('Scanning {} for camera models...'.format(args.path))
        cameras = list_cameras(args.path)

        if cameras:
            print('\nFound {} unique camera model(s):\n'.format(len(cameras)))
            for camera in cameras:
                print('  - {}'.format(camera))
        else:
            print('\nNo camera models found in EXIF data.')

        sys.exit(0)

    process_images(args.path, args.type)
    
    


