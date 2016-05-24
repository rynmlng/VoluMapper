# VoluMapper
This project provides an interface to understand and display Amazon Web Services (AWS) Elastic Block Storage (EBS) Volumes and their relationship with Elastic Computer Cloud (EC2) instances.

This project will work on Python 2.7.x and greater. Try it on Linux Ubuntu or Mac OS X.

## Setup
The first thing you will need to do is obtain the source code for this project onto your machine:

1. `cd` into the installation directory of your choosing
2. `git clone https://github.com/rynmlng/VoluMapper.git`
3. `cd volumapper`

At this point you will see 2 executable Python scripts with the following functions:
* `aws_poller.py` - Maps EBS Volumes to EC2 Instances and outputs them to a table
* `utils.py` - Manages the file-tree produced from the `aws_poller.py`

## Requirements
In order to use `aws_poller.py` you will need to set two environment variables:
```
export AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY_ID>
export AWS_SECRET_ACCESS_KEY=<YOUR_SUPER_SECRET_ACCESS_KEY>
```
To learn how to get these variables from your AWS Account, [read this article](https://aws.amazon.com/developers/access-keys/).

## Usage
Interact with either of these scripts by calling them directly. (e.g. `./aws_poller.py` or `python2 aws_poller.py`) Pass in the `--help` flag to learn about their functionality.
