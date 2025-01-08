from setuptools import setup, find_packages

setup(
    name="robotengine",
    version="0.1",
    packages=find_packages(),  # 自动发现所有的包和子包
    install_requires=[
        "serial>=0.0.97",
        "inputs>=0.5"
    ],
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
