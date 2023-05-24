import setuptools
#from .src.labelatorio import __version__
with open("src/labelatorio/__init__.py","rt") as f:
        for line in f.readlines():
            if line.startswith("__version__"):
                __version__ = line.split("=")[1].strip(" \n\"")

setuptools.setup(name='labelatorio',
                version=__version__,
                description='Labelator.io python client',
                long_description=open('README.md').read(),
                long_description_content_type='text/markdown',
                author='Juraj Bezdek',
                author_email='juraj.bezdek@blip.solutions',
                url='https://github.com/blip-solutions/labelatorio-pyclient',
                package_dir={"": "src"},
                packages=setuptools.find_packages(where="src"),
                license='MIT License',
                zip_safe=False,
                keywords='client labelator-io',

                classifiers=[
                ],
                python_requires='>=3.8',
                install_requires=[
                    "pandas",
                    "requests",
                    "dataclasses-json",
                    "marshmallow",
                    "tqdm",
                    "pydantic",
                    "aiohttp"
                ]
                )
