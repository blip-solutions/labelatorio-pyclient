import setuptools
#from src.labelatorio.version import Version


setuptools.setup(name='labelatorio',
                version='0.1.0',
                description='labelator.io client',
                long_description=open('README.md').read().strip(),
                author='Juraj Bezdek',
                author_email='juraj.bezdek@gmail.com',
                url='http://www.labelator.io',
                package_dir={"": "src"},
                packages=setuptools.find_packages(where="src"),
                license='MIT License',
                zip_safe=False,
                keywords='client labelator-io',

                classifiers=[
                    'Development Status :: 2 - Pre-Alpha'
                ],
                python_requires='>=3.8',
                install_requires=[
                    "pandas",
                    "requests",
                    "dataclasses-json",
                    "marshmallow",
                    "tqdm"
                ]
                )
