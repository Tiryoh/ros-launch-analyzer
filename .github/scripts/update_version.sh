#!/bin/bash -eu

VERSION=$1

sed -i -E 's/version = "[0-9\.]*"/version = "'$VERSION'"/g' pyproject.toml
sed -i -E 's/__version__ = "[0-9\.]*"/__version__ = "'$VERSION'"/g' ros_launch_analyzer/_version.py
