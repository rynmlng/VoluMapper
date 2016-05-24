from setuptools import setup

VERSION = "1.0.0"

setup(name="VoluMapper",
      version=VERSION,
      descripton="Maps EBS Volumes to EC2 Instances in a table",
      packages=["volumapper"],
      url="https://github.com/rynmlng/VolumMapper",
      author="Ryan Miling",
      author_email="ryanmiling@gmail.com",
      license="MIT",
      entry_points={
          "console_scripts": ["volumapper=volumapper.aws_poller:main",
                              "volumapper_utils=volmapper.utils:main",
                             ]
      }
)
