from setuptools import setup


setup(name="gwydb",
      version="0.1.0a",
      author="Dmitry Streltsov",
      author_email="streltsov.dmitry@gmail.com",
      description=("Project for organizing AFM data files "
                   "in Postgresql database."),
      license="MIT",
      packages=["gwydb"],
      url="https://github.com/dmitry-streltsov/gwy-postgresql",
      classifiers=[
          "Development Status :: 2 - Pre-Alpha",
          "Intended Audience :: Science/Research",
          "Topic :: Scientific/Engineering :: Physics",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3.4",
          "Operating System :: POSIX :: Linux"],
      setup_requires=["cffi>=1.0.0"],
      cffi_modules=["gwydb/gwy/libgwyfile_build.py:ffibuilder"],
      install_requires=["cffi>=1.0.0", "numpy"]
      )
