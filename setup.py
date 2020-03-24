from setuptools import setup
from babel.messages import frontend as babel


setup(
    name='healthcheck',
    version='0.1',
    description="Turris router health checking tool",
    long_description="Turris router health checking tool.",
    url="https://gitlab.labs.nic.cz/turris/healthcheck",
    author="CZ.NIC, z. s. p. o.",
    author_email="karel.koci@nic.cz",
    license="GPLv3",

    packages=[
        'healthcheck',
        'healthcheck_setup',
        'healthcheck_system',
    ],

    entry_points={
        'console_scripts': [
            'healthcheck=healthcheck.__main__:main'
        ],
        'healthcheck.plugins': [
            'setup = healthcheck_system.SetupPlugin',
            'system = healthcheck_system.SystemPlugin',
        ]
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
        "pyuci @ git+https://gitlab.nic.cz/turris/pyuci.git",
    ],
    setup_requires=["babel"],
    cmdclass={"install": InstallWithCompiledMessages},
)
