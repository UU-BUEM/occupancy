from setuptools import find_packages, setup


if __name__ == "__main__":
    setup(
        name="occupancy",
        package_dir={"": "src"},
        packages=find_packages(where="src"),
    )
