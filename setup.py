from setuptools import setup

VERSION = "1.0.0"

setup(name="VoluMapper",
      version=VERSION,
      descripton="Maps EBS Volumes to EC2 Instances in a table",
      packages=["pollers"],
      url="https://github.com/rynmlng/VolumMapper",
      author="Ryan Miling",
      author_email="ryanmiling@gmail.com",
      license="MIT",
      entry_points={
          "console_scripts": ["volumapper=pollers.aws_poller:main",
                              "volumapper_utils=pollers.utils:main",
                             ]
      }
)
