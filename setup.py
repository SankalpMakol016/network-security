from pathlib import Path

from setuptools import find_packages, setup


PROJECT_ROOT = Path(__file__).parent


def get_requirements(file_path: str) -> list[str]:
    requirements_path = PROJECT_ROOT / file_path

    try:
        with requirements_path.open("r", encoding="utf-8") as file:
            requirements = file.readlines()
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Requirements file not found: {requirements_path}") from error
    except OSError as error:
        raise OSError(f"Unable to read requirements file: {requirements_path}") from error

    requirements = [
        requirement.strip()
        for requirement in requirements
        if requirement.strip() and not requirement.startswith("#")
    ]

    if "-e ." in requirements:
        requirements.remove("-e .")

    return requirements


setup(
    name="networksecurity",
    version="0.1.0",
    author="Sankalp Makol",
    description="End-to-end network security project with ETL, ML, MongoDB, and MLOps.",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=get_requirements("requirements.txt"),
    python_requires=">=3.11",
)
