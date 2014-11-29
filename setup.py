from setuptools import setup

setup(
    name="flood",
    version='0.1.1',
    zip_safe=False,
    platforms='any',
    packages=['flood'],
    install_requires=['netkit'],
    scripts=['flood/bin/flood.py'],
    url="https://github.com/dantezhu/flood",
    license="BSD",
    author="dantezhu",
    author_email="zny2008@gmail.com",
    description="server load test",
)
