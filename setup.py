from setuptools import setup, find_packages

setup(
    name="robotengine",
    version="0.15",
    packages=find_packages(),  # 自动发现所有的包和子包
    install_requires=[
        "pyserial>=0.5",
        "inputs>=0.5",
        "requests>=2.32.3",
        "aiohttp>=3.10.11",
    ],
    entry_points={
        "console_scripts": [
            "robotengine = robotengine.cli:main",
        ],
    },
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    author="EricSanchez",
    author_email="niexiaohangeric@163.com",
    description="A easy-to-use robot framework",
    url="https://github.com/EricSanchezok/robotengine",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
