#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    print("Turret needs setuptools in order to build. Install it using"
            " your package manager (usually python-setuptools) or via pip (pip"
            " install setuptools).")
    sys.exit(1)

setup(name='turret',
      version='0.2.1',
      description='Ansible inventory in MongoDB',
      author='Vincent van Gelder',
      author_email='vincent@ixlhosting.nl',
      url='http://ixlhosting.nl/',
      license='Apache Software License',
      install_requires=["pymongo", "PyYAML", 'setuptools', 'scapy', 'prompter','logging','requests','netaddr'],
      dependency_links = ['https://github.com/vvgelder/py-solusvm-api.git#egg=py-solusvm-api'],
      package_dir={ '': 'lib' },
      packages=find_packages('lib'),
      package_data={
         '': [],
      },
      classifiers=[
          'Development Status :: 5 - Production/Stable',
          'Environment :: Console',
          'Intended Audience :: Developers',
          'Intended Audience :: Information Technology',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: Apache Software License',
          'Natural Language :: English',
          'Operating System :: POSIX',
          'Programming Language :: Python :: 2.6',
          'Programming Language :: Python :: 2.7',
          'Topic :: System :: Installation/Setup',
          'Topic :: System :: Systems Administration',
          'Topic :: Utilities',
      ],
      scripts=[
         'bin/turret',
         'bin/turret-ansible',
         'bin/subnets',
         'bin/subnets-discovery',
      ],
      data_files=[],
)
