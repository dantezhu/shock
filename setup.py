from setuptools import setup

setup(
    name="shock",
    version='0.1.25',
    zip_safe=False,
    platforms='any',
    packages=['shock'],
    install_requires=['netkit', 'click'],
    scripts=['shock/bin/shock'],
    url="https://github.com/dantezhu/shock",
    license="BSD",
    author="dantezhu",
    author_email="zny2008@gmail.com",
    description="tool for server load performance testing",
)
