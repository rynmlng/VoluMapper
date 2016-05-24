#!/usr/bin/python2
# -*- coding: utf-8 -*-

from __future__ import absolute_import

import argparse
import datetime
import os


"""
Here is an example file-tree for 2 data-dirs 'volume' and 'instance'
  categorized by Access Key ID and regions.

results
  |-022QF06E7MXBSH9DHM02 (Access Key ID)
  |   |-us-east-1 (Region)
  |   |   |-volume
  |   |   |   |-1463965087.pkl
  |   |   |
  |   |   |-instance
  |   |   |   |-1463965087.pkl
  .   .   .   .
  .   .   .   .
"""

DEFAULT_ROOT_RESULTS_DIR = "results"

def setup_dir(path, *sub_dirs):
    """ Creates dir at path if it does not exist.

    :param path: Path on the file-system to create the dir
    :type path: str

    :param sub_dirs: Sub-directories we need created on the path
    :type sub_dirs: list
    """
    if not os.path.exists(path):
        os.mkdir(path)

    for sub_dir in sub_dirs:
        setup_dir(os.path.join(path, sub_dir))


def setup_env(ident, results_dir=None):
    """ Sets up the file-tree of this file-system to record data from the API

    :param ident: Identifier for the AWS Account we're working with, most likely the Access Key ID
    :type ident: str

    :param results_dir: Root directory where results are found
    :type results_dir: str
    """
    if results_dir is None:
        results_dir = DEFAULT_ROOT_RESULTS_DIR

    setup_dir(results_dir, ident)


def get_last_file_timestamp(path):
    """ Scans through all files in the path with names representing timestamps
          (UTC seconds since epoch) and returns the most recent timestamp.

    :param path: Directory path to scan files in
    :type path: str

    :returns: Most recent timestamp in filename
    :rtype: int
    """
    last_timestamp = None
    for filename in os.listdir(path):
        try:
            timestamp = int(filename.split(".")[0])
        except ValueError:
            continue # ignore bad files

        if last_timestamp is None or timestamp > last_timestamp:
            last_timestamp = timestamp

    return last_timestamp


def cleanup_old_data(results_dir=None):
    """ Clean up old data files that have been saved over time.

    :param results_dir: Root directory where results are found
    :type results_dir: str
    """
    if results_dir is None:
        results_dir = DEFAULT_ROOT_RESULTS_DIR

    print("Walking through '{}' cleaning up old data-files...".format(results_dir))

    for ident_dir in os.listdir(results_dir):
        ident_dir_path = os.path.join(results_dir, ident_dir)

        for region_dir in os.listdir(ident_dir_path):
            region_dir_path = os.path.join(ident_dir_path, region_dir)

            for data_dir in os.listdir(region_dir_path):
                data_dir_path = os.path.join(region_dir_path, data_dir)

                last_timestamp = None
                last_filename = None
                to_delete_files = set()

                for filename in os.listdir(data_dir_path):
                    try:
                        timestamp = int(filename.split(".")[0])
                    except ValueError:
                        continue # ignore bad files

                    if last_timestamp is None:
                        last_timestamp = timestamp
                        last_filename = filename
                    elif timestamp > last_timestamp:
                        to_delete_files.add(last_filename)

                        last_timestamp = timestamp
                        last_filename = filename
                    else:
                        to_delete_files.add(filename)

                for filename in to_delete_files:
                    file_path = os.path.join(data_dir_path, filename)
                    os.remove(file_path)

                    print("  Deleting {}".format(file_path))


def main():
    parser = argparse.ArgumentParser(description="File-tree util to manage our poller file system")

    parser.add_argument("-c", "--cleanup", action="store_true", required=False,
                        help="Clean up stale data files"
                       )

    parser.add_argument("-r", "--results-dir", required=False,
                        help="Use this results dir, otherwise default ({}/) is used".format(DEFAULT_ROOT_RESULTS_DIR)
                       )

    args = parser.parse_args()

    if args.cleanup:
        cleanup_old_data(args.results_dir)


if __name__ == "__main__":
    main()
