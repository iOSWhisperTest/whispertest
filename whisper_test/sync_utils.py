from os.path import join, getmtime, basename
from glob import glob
from shutil import copy2

def copy_last_modified_file(ios_mounted_dir, out_dir, file_pattern="*.MP4"):
    """Copy the last modified file from the mounted iOS device to the output directory.

    Screen recordings are saved in folders ending with "APPLE" (100APPLE, 101APPLE, ...)
    under the DCIM folder. This is also where all the photos and videos are stored.
    """
    # First find the last APPLE folder
    apple_dirs = glob(join(ios_mounted_dir, "DCIM", "*APPLE"))
    if not apple_dirs:
        return None
    latest_apple_dir = max(apple_dirs, key=getmtime)

    # Find the last modified MP4 file
    all_videos = glob(join(latest_apple_dir, file_pattern))
    if not all_videos:
        return None
    last_mp4 = max(all_videos, key=getmtime)
    # print(f"Last APPLE folder: {latest_apple_dir}; Latest MP4: {last_mp4}")
    # Copy the file to the output directory
    copy2(last_mp4, join(out_dir, basename(last_mp4)))
    return last_mp4

# USAGE:
# To copy the last screen recording, we first mount the iPhone filesystem using `iFuse`,
#    `ifuse /tmp/ios`
# Make sure the output directory exists and iPhone is mounted at /tmp/ios
# copy_last_modified_file("/tmp/ios/", "/tmp/ios_videos/")
