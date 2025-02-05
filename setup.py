from setuptools import setup

setup(
    name='pipbrew-clearner',
    version='0.1.0',
    description='Interactive CLI tool to list and uninstall pip and Homebrew packages',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/pipbrew-clearner',
    py_modules=['main', 'pip_manager', 'brew_manager'],
    entry_points={
        'console_scripts': [
            'pipbrew-clearner = main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: MacOS :: MacOS X',
        'License :: OSI Approved :: MIT License',
    ],
    python_requires='>=3.6',
)
