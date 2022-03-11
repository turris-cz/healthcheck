#!/usr/bin/env python3
import pathlib
import subprocess

from setuptools import setup
from setuptools.command.install import install


class InstallWithCompiledMessages(install):
    def run(self):
        subprocess.run(["make", "-C", pathlib.Path(__file__).parent], check=True)
        super().run()


setup(
    name="healthcheck",
    version="0.1",
    description="Turris router health checking tool",
    long_description="Turris router health checking tool.",
    url="https://gitlab.labs.nic.cz/turris/healthcheck",
    author="CZ.NIC, z. s. p. o.",
    author_email="karel.koci@nic.cz",
    license="GPLv3.0-or-later",
    packages=[
        "healthcheck",
        "healthcheck_setup",
        "healthcheck_system",
    ],
    entry_points={
        "console_scripts": ["healthcheck = healthcheck.__main__:main"],
        "healthcheck.plugins": [
            "setup = healthcheck_setup:SetupPlugin",
            "system = healthcheck_system:SystemPlugin",
        ],
    },
    package_data={
        "healthcheck": ["locale/*/*.mo"],
        "healthcheck_setup": ["locale/*/*.mo"],
        "healthcheck_system": ["locale/*/*.mo"],
    },
    install_requires=[
        "humanize",
        "rich",
        "crontab",
        "pyuci >=0.9.0",
    ],
    setup_requires=["babel"],
    cmdclass={"install": InstallWithCompiledMessages},
)
