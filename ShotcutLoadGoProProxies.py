#!/usr/bin/env python3

import hashlib
import os
import shutil
import sys
import argparse
import logging
import xml.etree.ElementTree
from os import path, stat, mkdir

lowres_ext = '.LRV'
highres_ext = '.MP4'
shotcut_project_ext = '.MLT'
proxies_ext = '.mp4'
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)


def get_file_hash(file_path):
    file_size = stat(file_path).st_size
    if file_size <= 2000000:
        raise ValueError("File {} too small for hash algorithm".format(file_path))
    with open(file_path, 'rb') as f:
        file_data = f.read(1000000)
        f.seek(file_size - 1000000)
        file_data += f.read(1000000)
        return hashlib.md5(file_data).hexdigest()


def lowres_filename(highres_file):
    filenames = []
    file_no_ext = path.splitext(highres_file)[0]
    filenames.append(file_no_ext + lowres_ext)  # GOPRxxxx.MP4 -> GOPRxxxx.LRV
    filenames.append(file_no_ext.replace('H', 'L') + lowres_ext)  # GH01xxxx.mp4 -> GL01xxxx.LRV
    filenames.append(file_no_ext.replace('X', 'L') + lowres_ext)  # GX01xxxx.mp4 -> GL01xxxx.LRV
    return filenames


# parse arguments
parser = argparse.ArgumentParser()
parser.add_argument('--shotcut-path', required=True, help="Path to Shotcut project directory (containing .mlt file)")
args = parser.parse_args()

# Input Validation
if not path.isdir(args.shotcut_path):
    logging.error('Shotcut project path {} does not exist!'.format(args.shotcut_path))
    sys.exit(1)

# get high resolution files from Shotcut project file
logging.info('Retrieving original video files from Shotcut project...')
project_highres_files = set()
for file in os.listdir(args.shotcut_path):
    if path.splitext(file)[1].upper() == shotcut_project_ext:
        xml_tree = xml.etree.ElementTree.parse(path.join(args.shotcut_path, file))
        xml_root = xml_tree.getroot()
        for resource in xml_root.findall("./producer/property[@name='resource']"):
            file_name = resource.text
            if path.isfile(file_name) and path.splitext(file_name)[1].upper() == highres_ext:
                project_highres_files.add(file_name)

# find low resolution versions of files
logging.info('Searching for low resolution versions of video files (.LRV)...')
project_lowres_files = dict.fromkeys(project_highres_files)
for file in project_highres_files:
    directory, filename = path.split(file)
    lowres_filenames = lowres_filename(filename)
    for lowres_file in lowres_filenames:
        lowres_file_path = path.join(directory, lowres_file)
        if path.isfile(lowres_file_path):
            project_lowres_files[file] = lowres_file_path
    if project_lowres_files[file] is None:
        logging.warning('No low resolution version found for {}'.format(file))

# Copy low resolution versions to Shotcut proxies directory
logging.info('Copying low resolution files to Shotcut proxies directory...')
shotcut_proxies_path = path.join(args.shotcut_path, 'proxies')
for highres_file, lowres_file in project_lowres_files.items():
    try:
        file_hash = get_file_hash(highres_file)
    except Exception as e:
        logging.warning(e)
        continue
    proxy_file_path = path.join(shotcut_proxies_path, file_hash + proxies_ext)
    if not path.isdir(shotcut_proxies_path):
        mkdir(shotcut_proxies_path)
        logging.info('Created proxies directory')
    if path.isfile(proxy_file_path):
        logging.info('Proxy file for {} already exists. Skipping...'.format(highres_file))
        continue
    try:
        shutil.copyfile(lowres_file, proxy_file_path)
    except IOError as e:
        logging.warning(e)
        continue
    logging.info('Copied {} to {}'.format(path.basename(lowres_file), path.basename(proxy_file_path)))
