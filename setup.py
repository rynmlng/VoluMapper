from setuptools import setup

VERSION = "0.0.1"

setup(name="VoluMapper",
      version=VERSION,
      descripton="Maps EBS Volumes to EC2 Instances in a table",
      packages=["aws_poller"],
      url="https://github.com/rynmlng/VolumMapper",
      author="Ryan Miling",
      author_email="ryanmiling@gmail.com",
      license="MIT",
      entry_points={
          "console_scripts": ["volumapper=__main__:main",
                              "volumapper_utils=utils.__main__:main",
                             ]
      }
)
