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

def process_images(path, camera_type):
    f = []
    t = []
    focus = []

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
                                        # Handle both rational tuples and float values
                                        if isinstance(stop, tuple):
                                            f.append(stop[0]/float(stop[1]))
                                        else:
                                            f.append(float(stop))

                                        if isinstance(time, tuple):
                                            t.append(time[0]/float(time[1]))
                                        else:
                                            t.append(float(time))

                                        if isinstance(fd, tuple):
                                            focus.append(fd[0]/float(fd[1]))
                                        else:
                                            focus.append(float(fd))
                            except (KeyError, TypeError, ZeroDivisionError):
                                print('Error while reading EXIF data in image {}'.format(filename))
                except (IOError, OSError) as e:
                    print('Error opening image {}: {}'.format(filename, e))


    print('Number of photos: {}'.format(len(t)))

    if focus:
        # x = np.asarray([f for f in focus if f <= 55])
        plt.figure()
        plt.hist(asarray(focus), bins=30)
        plt.ylabel('Number of photos');
        plt.xlabel('Focal distance, mm');
        plt.savefig(os.path.join(output_dir, 'focal_distance.png'))

    if f:
        plt.figure()
        plt.hist(asarray(f), bins=30)
        plt.ylabel('Number of photos');
        plt.xlabel('f number');
        plt.savefig(os.path.join(output_dir, 'f_number.png'))

    if t:
        plt.figure()
        plt.hist(asarray(t), bins=logspace(log10(min(t))-1, log10(max(t)), 30))
        plt.ylabel('Number of photos');
        plt.xlabel('Shutter speed, s');
        plt.gca().set_xscale("log")
        plt.savefig(os.path.join(output_dir, 'shutter_speed.png'))
        
    return (f, t, focus)


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
    
    


