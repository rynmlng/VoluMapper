#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import

from collections import namedtuple, OrderedDict
from tabulate import tabulate
import argparse
import boto.ec2
import cPickle
import datetime
import logging
import os
import sys

import utils


__version__ = "1.0.0"


ALL_REGIONS = ("us-east-1", "us-west-1", "us-west-2", "eu-west-1", "eu-central-1",
               "ap-northeast-1", "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
               "sa-east-1"
              )

AWS_ACCESS_KEY_ID_ENV_VAR = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY_ENV_VAR = "AWS_SECRET_ACCESS_KEY"

LOGGING_FORMAT = "%(asctime)s %(levelname)s: %(message)s"

logging.basicConfig(format=LOGGING_FORMAT)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Represents an EBS volume, size is given in GB
EBSVolume = namedtuple("EBSVolume", ("id", "status", "size", "type", "instance_id"))

# Represents an EC2 instance
EC2Instance = namedtuple("EC2Instance", ("id", "state", "type"))


def output_to_table(ebs_volumes, ec2_instances):
    """ Output EBS Volumes mapped to EC2 Instances in a tabular format to stdout.

        Table header is...
          EC2 Instance ID | EC2 Instance State | EBS Volume ID | EBS Volume Status | EBS Volume Size

    :param volumes: EBS Volumes to be outputted
    :type volume: list<EBSVolume>

    :param volumes: EC2 Instances to be outputted w/EBS Volumes
    :type volume: list<EC2Instance>
    """
    TABLE_FORMAT = "psql" # see tabulate docs for different formats
    MISSING_TEXT = "NOT FOUND"

    logger.info("Outputting EBS Volumes and their EC2 Instances")

    instance_dict = {inst.id: inst for inst in ec2_instances}

    table = [] # build a 2-D list to port over to tabulate

    for volume in ebs_volumes:
        row = OrderedDict()

        instance = instance_dict.get(volume.instance_id)
        if instance is not None:
            row["Instance ID"] = instance.id
            row["Instance Type"] = instance.type
            row["Instance State"] = instance.state
        else:
            row["Instance ID"] = MISSING_TEXT
            row["Instance Type"] = MISSING_TEXT
            row["Instance State"] = MISSING_TEXT

        row["Volume ID"] = volume.id
        row["Volume Status"] = volume.status
        row["Volume Size"] = "%.1fGB" % volume.size

        table.append(row)

    print(tabulate(table, headers="keys", tablefmt=TABLE_FORMAT))


def track_results(data_dir, freshness):
    """ AWSPoller methods can be decorated with this function to save API results.

        This prevents APIs from being hit too many times when we know our AWS configurations
          do not change that often.

    :param data_dir: Data directory containing the data
    :type data_dir: str

    :param freshness: We do not need any fresher data if it's less than this many seconds old
    :type freshness: int
    """
    def track_results_decorator(method):
        def wrapper(self, *args, **kwargs):
            results_dir = os.path.join(self.results_dir, data_dir)

            last_timestamp = utils.get_last_file_timestamp(results_dir)
            last_file_path = os.path.join(results_dir, "{}.pkl".format(last_timestamp))

            epoch_secs = int(datetime.datetime.utcnow().strftime("%s"))

            results = None
            if self.force_grab or last_timestamp is None or (epoch_secs - last_timestamp) > freshness:
                logger.debug("Getting a fresh new batch of results from the API")
                try:
                    results = method(self, *args, **kwargs)
                except Exception as ex:
                    logger.exception("Errored out trying to poll for %s data", data_dir)
                    results = []

                if results:
                    filename = "{}.pkl".format(epoch_secs)
                    file_path = os.path.join(results_dir, filename)

                    logger.debug("Pickling result and writing to %s", file_path)

                    if os.path.exists(file_path):
                        logger.warning("Overwriting, already exists")

                    with open(file_path, "wb") as out_file:
                        cPickle.dump(results, out_file)
            else:
                logger.debug("Loading pickled results from %s", last_file_path)
                with open(last_file_path) as in_file:
                    results = cPickle.load(in_file)

            return results

        return wrapper
    return track_results_decorator


class AWSRegionPollerFactory(object):
    """ Factory class that creates AWS Account API pollers based on regions """

    INSTANCE_DATA_DIR = "instances"
    VOLUME_DATA_DIR = "volumes"

    def __init__(self, access_key_id, secret_access_key, regions=None,
                 include_rogue_volumes=False, force_grab=False):
        """ Configures our AWS region poller factory to pull information from APIs.

        :param access_key_id: AWS Access Key ID (sometimes public)
        :type access_key_id: str

        :param secret_access_key: AWS Secret Access Key (very secret)
        :type secret_access_key: str

        :param regions: AWS region identifiers
        :type regions: tuple

        :param include_rogue_volumes: Whether or not to include EBS volumes lacking an assooc. instance
        :type include_rogue_volumes: bool

        :param force_grab: Forcefully poll the AWS account's API for the freshest data
        :type force_grab: bool
        """
        self.access_key_id = access_key_id
        self.__secret_access_key = secret_access_key

        if regions is None:
            self.regions = ALL_REGIONS
        else:
            self.regions = regions

        self.include_rogue_volumes = include_rogue_volumes
        self.force_grab = force_grab

        logger.info("Setting up the file-tree to store API data")
        utils.setup_env(self.access_key_id)

    def get_region_poller(self, region):
        """ Build an AWSRegionPoller based on the region provided.

        :param region: Region to build a poller for
        :type region: str

        :returns: AWS Region instance ready to poll an API
        :rtype: AWSRegionPoller
        """
        logger.debug("Establishing connection to AWS region %s", region)
        conn = boto.ec2.connect_to_region(region, aws_access_key_id=self.access_key_id,
                                          aws_secret_access_key=self.__secret_access_key)

        return AWSRegionPoller(self.access_key_id, conn, region, self.force_grab)

    def run(self):
        """ Run the AWS region poller with the initialized configuration from the constructor.

        :returns: Two lists of EBS Volumes and EC2 Instances
        :rtype: tuple
        """
        logger.info("Running AWS region poller")

        all_instances = []
        all_volumes = []

        # Get all instances & volumes across all regions
        for region in self.regions:
            logger.info("Obtaining instance & volume data for region %s", region)
            region_poller = self.get_region_poller(region)

            all_instances.extend(region_poller.get_instances())
            all_volumes.extend(region_poller.get_volumes())

        return all_volumes, all_instances


class AWSRegionPoller(object):
    """ AWS Account API poller that pulls information from one specified region """

    def __init__(self, ident, connection, region_name, force_grab=False):
        """ Configures our AWS region poller to pull information from this API.

        :param ident: Identifier for this poller used to store data. This is most likely the Access Key ID.
        :type ident: str

        :param connection: EC2 connection allowing API access
        :type connection: boto.ec2.conncetion.EC2Connection

        :param region_name: Name of the region to access the API
        :type region_name: str

        :param force_grab: Forcefully poll the regional AWS account's API for the freshest data
        :type force_grab: bool
        """
        self.connection = connection
        self.region_name = region_name
        self.force_grab = force_grab

        env_path = os.path.join(utils.BASE_RESULTS_DIR, ident, region_name)

        utils.setup_dir(env_path, AWSRegionPollerFactory.INSTANCE_DATA_DIR,
                        AWSRegionPollerFactory.VOLUME_DATA_DIR
                       )

        self.results_dir = env_path

    @track_results(data_dir=AWSRegionPollerFactory.VOLUME_DATA_DIR, freshness=24*60*60)
    def get_volumes(self):
        """ Get all the EBS volumes for this AWS account's connection

        :returns: EBS volumes and related info
        :rtype: list
        """
        all_volumes = []

        logger.debug("Polling API for all volumes")
        for volume in self.connection.get_all_volumes():
            if volume.attach_data and volume.attach_data.instance_id:
                new_volume = EBSVolume(volume.id, volume.status, volume.size, volume.type,
                                       volume.attach_data.instance_id
                                      )
            elif self.include_rogue_volumes:
                new_volume = EBSVolume(volume.id, volume.status, volume.size, volume.type, "")

            all_volumes.append(new_volume)

        return all_volumes

    @track_results(data_dir=AWSRegionPollerFactory.INSTANCE_DATA_DIR, freshness=24*60*60)
    def get_instances(self):
        """ Get all the EC2 instances for this AWS account's connection

        :returns: EC2 instances and related info
        :rtype: list
        """
        all_instances = []

        logger.debug("Polling API for all instances")
        for instance in self.connection.get_only_instances():
            new_instance = EC2Instance(instance.id, instance.state, instance.instance_type)

            all_instances.append(new_instance)

        return all_instances


def main(args=None):
    parser = argparse.ArgumentParser(description="Map Amazon EBS Volumes to EC2 Instances and output"
                                                 " into a table, v{}\nNOTE: {} and {} must be"
                                                 " defined".format(__version__, AWS_ACCESS_KEY_ID_ENV_VAR,
                                                                   AWS_SECRET_ACCESS_KEY_ENV_VAR
                                                                  ),
                                     formatter_class=argparse.RawTextHelpFormatter
                                    )

    parser.add_argument("-r", "--region", action="append", required=False,
                        help="Specify the region(s) EC2 instances are located on"
                       )

    parser.add_argument("-f", "--force", action="store_true", required=False,
                        help="Forcefully poll the API for the freshest data"
                       )

    parser.add_argument("--include-rogue-volumes", action="store_true",
                        help="Include volumes that are disattached from instances"
                       )

    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Provide debugging information"
                       )

    def get_os_env_var(var_name):
        """ Get the required environment variable specified.

        :param var_name: Environment variable on the system
        :type var_name: str

        :returns: Environmental variable's value
        :rtype: str

        :raises OSError: If the environmment variable is not defined
        """
        val = os.getenv(var_name)
        if not val:
            raise OSError("Environmental var {} must be defined".format(var_name))

        return val

    args = parser.parse_args()

    access_key_id = get_os_env_var(AWS_ACCESS_KEY_ID_ENV_VAR)
    secret_access_key = get_os_env_var(AWS_SECRET_ACCESS_KEY_ENV_VAR)

    regions = args.region
    if regions is not None:
        regions = tuple(set(args.region))

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    poller_factory = AWSRegionPollerFactory(access_key_id,
                                            secret_access_key,
                                            regions=regions,
                                            include_rogue_volumes=bool(args.include_rogue_volumes),
                                            force_grab=args.force
                                           )

    ebs_volumes, ec2_instances = poller_factory.run()
    if ebs_volumes: # no volumes means we have nothing to map
        output_to_table(ebs_volumes, ec2_instances)
    else:
        logger.info("No EBS Volumes were found, nothing to output")


if __name__ == "__main__":
    main()
