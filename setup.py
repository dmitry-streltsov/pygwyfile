from setuptools import setup


setup(name="pygwyfile",
      version="0.1.0a",
      author="Dmitry Streltsov",
      author_email="streltsov.dmitry@gmail.com",
      description=("A pythonic interface for reading and "
                   "writing of Gwyddion GWY files"),
      license="MIT",
      packages=["pygwyfile"],
      url="https://github.com/dmitry-streltsov/pygwyfile",
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Intended Audience :: Science/Research",
          "Topic :: Scientific/Engineering :: Physics",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3.4",
          "Operating System :: POSIX :: Linux"],
      setup_requires=["cffi>=1.0.0"],
      cffi_modules=["pygwyfile/libgwyfile_build.py:ffibuilder"],
      install_requires=["cffi>=1.0.0", "numpy"]
      )
