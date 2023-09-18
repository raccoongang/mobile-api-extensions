from os import environ

from utils import check_version


if __name__ == "__main__":
    if tag_name := environ.get("CI_COMMIT_TAG"):
        check_version(tag_name)
    else:
        exit(1)
