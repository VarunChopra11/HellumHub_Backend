import semver


def parse_version(value: str) -> semver.Version:
    return semver.Version.parse(value)


def is_greater(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)
