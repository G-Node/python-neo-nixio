try:
    from setuptools import setup
except:
    from distutils.core import setup
import re

__author__ = "Achilleas Koutsou"

with open("README.md") as f:
    description_text = f.read()

with open("LICENSE") as f:
    license_text = f.read()

with open("info.py") as f:
    info = f.read()

VERSION         = re.search(r"VERSION\s*=\s*'([^']*)'", info).group(1)
AUTHOR          = re.search(r"AUTHOR\s*=\s*'([^']*)'", info).group(1)
CONTACT         = re.search(r"CONTACT\s*=\s*'([^']*)'", info).group(1)
BRIEF           = re.search(r"BRIEF\s*=\s*'([^']*)'", info).group(1)
HOMEPAGE        = re.search(r"HOMEPAGE\s*=\s*'([^']*)'", info).group(1)


setup(name             = 'neonix',
      version          = VERSION,
      author           = AUTHOR,
      author_email     = CONTACT,
      url              = HOMEPAGE,
      description      = BRIEF,
      long_description = description_text,
      license          = 'BSD',
      packages         = ['neonix', 'neonix.io'],
      tests_require    = ['nose'],
      test_suite       = 'nose.collector',
      install_requires = ['nix', 'neo'],
      package_data     = {'neonix': [license_text, description_text]},
      include_package_data = True,
      zip_safe         = False,
      )
