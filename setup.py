from setuptools import setup, find_packages

setup(
    name="robotengine",
    version="0.1",
    packages=find_packages(),  # 自动发现所有的包和子包
    install_requires=[
        # 如果有依赖库，列在这里
    ],
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python package with multiple modules",
    url="https://github.com/yourusername/my_package",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
