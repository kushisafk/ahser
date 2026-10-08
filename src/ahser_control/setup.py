import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'ahser_control'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='kushal',
    maintainer_email='kushal@todo.todo',
    description='AHSER robot control logic and controller interfaces',
    license='TODO: License declaration',
    extras_require={
        'test': ['pytest'],
    },
    entry_points={
        'console_scripts': [
            'controller = ahser_control.controller:main',
        ],
    },
)
