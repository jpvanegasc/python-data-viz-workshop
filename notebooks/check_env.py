"""Check the setup for the workshop."""

from packaging.version import Version
import importlib
import json
import os
import sys
import yaml


def run_env_check(raise_exc=False):
    """Check that the packages we need are installed and the Python version is correct."""
    
    failures = []

    def _print_version_ok(item):
        """Print an OK message for version check."""
        print('\x1b[42m[ OK ]\x1b[0m', '%s' % item)

    def _print_version_failure(item, req_version, version):
        """Print a failure message for version check."""
        failures.append(item)
        if version:
            msg = '%s version %s is required, but %s installed.'
            values = (item, req_version, version)
        else:
            msg = '%s is not installed.'
            values = item
        print('\x1b[41m[FAIL]\x1b[0m', msg % values)

    # read in the environment file and process versions
    with open('../environment.yml', 'r') as file:
        env = yaml.safe_load(file)

    requirements = {}
    for line in env['dependencies']:
        try:
            if '>=' in line:
                pkg, versions = line.split('>=')
                if ',<=' in versions:
                    version = versions.split(',<=')
                else:
                    version = [versions, None]
            else:
                pkg, version = line.split('=')
        except ValueError:
            pkg, version = line, None
        if '-' in pkg:
            continue
        requirements[pkg.split('::')[-1]] = version

    # check the python version, if provided
    try:
        required_version = requirements.pop('python')
        python_version = sys.version_info
        for component, value in zip(['major', 'minor', 'micro'], required_version.split('.')):
            if getattr(python_version, component) != int(value):
                print(f'Using Python at {sys.prefix}:\n-> {sys.version}')
                _print_version_failure(
                    'Python',
                    required_version,
                    f'{python_version.major}.{python_version.minor}'
                )
                break
        else:
            _print_version_ok('Python')
    except KeyError:
        pass

    for pkg, req_version in requirements.items():
        try:
            mod = importlib.import_module(pkg)
            if req_version:
                version = mod.__version__
                installed_version = Version(version).base_version
                if isinstance(req_version, list):
                    min_version, max_version = req_version
                    if (
                        installed_version < Version(min_version).base_version
                        or (max_version and installed_version > Version(max_version).base_version)
                    ):
                        _print_version_failure(
                            pkg, f'>= {min_version}{f" and <= {max_version}" if max_version else ""}', version
                        )
                        continue
                elif Version(version).base_version != Version(req_version).base_version:
                    _print_version_failure(pkg, req_version, version)
                    continue
            _print_version_ok(pkg)
        except ImportError:
            if pkg == 'ffmpeg':
                try:
                    pkg_info = json.loads(os.popen('conda list -f ffmpeg --json').read())[0]
                    if pkg_info:
                        if req_version:
                            if isinstance(req_version, list):
                                min_version, max_version = req_version
                                installed_version = Version(pkg_info['version'])
                                if (
                                    installed_version < Version(min_version)
                                    or (max_version and installed_version > Version(max_version))
                                ):
                                    _print_version_failure(
                                        pkg,
                                        f'>= {min_version}{f" and <= {max_version}" if max_version else ""}',
                                        pkg_info['version']
                                    )
                                    continue
                            elif pkg_info['version'] != req_version:
                                _print_version_failure(pkg, req_version, pkg_info['version'])
                                continue
                        _print_version_ok(pkg)
                        continue
                except IndexError:
                    pass
            _print_version_failure(pkg, req_version, None)

    if failures and raise_exc:
        raise Exception('Environment failed inspection.')

if __name__ == '__main__':
    print(f'Using Python at {sys.prefix}:\n-> {sys.version}')
    run_env_check(raise_exc=True)
