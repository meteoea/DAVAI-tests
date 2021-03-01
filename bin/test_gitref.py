#!/usr/bin/env python3
# -*- coding:Utf-8 -*-
"""
Create a Davai experiment based on a **gitref**.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import os
import shutil
import io
import argparse
import re
import configparser
import getpass
import socket

DAVAI_THIS_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAVAI_XP_DIRECTORY = os.environ.get('DAVAI_XP_DIRECTORY',
                                    os.path.join(os.environ.get('WORKDIR'), 'davai'))
DAVAI_IAL_REPOSITORY = os.environ.get('DAVAI_IAL_REPOSITORY',
                                      os.path.join(os.environ.get('HOME'), 'repositories', 'arpifs'))


def guess_host():
    DAVAI_HOSTS_CONFIG = os.path.join(DAVAI_THIS_REPO, 'conf', 'hosts.ini')
    DAVAI_LOCAL_HOSTS_CONFIG = os.path.join(os.environ['HOME'], '.davairc', 'hosts.ini')
    hostnames = configparser.ConfigParser()
    socket_hostname = socket.gethostname()
    host = os.environ.get('DAVAI_HOST', None)
    if not host:
        if os.path.exists(DAVAI_LOCAL_HOSTS_CONFIG):
            print("(hosts config read from local: {})".format(DAVAI_LOCAL_HOSTS_CONFIG))
            hostnames.read(DAVAI_LOCAL_HOSTS_CONFIG)
        else:
            print("(hosts config read from: {})".format(DAVAI_HOSTS_CONFIG))
            hostnames.read(DAVAI_HOSTS_CONFIG)
        for h in hostnames.sections():
            if re.match(hostnames[h]['re_pattern'], socket_hostname):
                host = h
                break
    return host

DAVAI_HOST = guess_host()


class AnXP(object):
    """Setup an XP."""
    DAVAI_PACKAGES_CONFIG = os.path.join(DAVAI_THIS_REPO, 'conf', 'packages.ini')
    DAVAI_LOCAL_PACKAGES_CONFIG = os.path.join(os.environ['HOME'], '.davairc', 'packages.ini')

    def __init__(self, IAL_git_ref,
                 usecase='NRV',
                 IAL_repository=DAVAI_IAL_REPOSITORY,
                 comment=None,
                 hostname=None):
        # initialisations
        self.xpid = '{}.{}@{}'.format(IAL_git_ref, usecase, getpass.getuser())
        self.usecase = usecase
        self.IAL_git_ref = IAL_git_ref
        self.IAL_repository = IAL_repository
        self.comment = comment if comment is not None else IAL_git_ref
        self.vconf = usecase.lower()
        self.xp_path = os.path.join(DAVAI_XP_DIRECTORY, self.xpid, 'davai', self.vconf)
        # packages
        self.default_hostname = hostname
        self._read_packages_config()
        self._read_packages_local_config()
        # prints
        print("* XPID:", self.xpid)
        print("* XP path:", self.xp_path)

    def setup(self, hostname=None, dev_mode=False):
        # dev mode links tasks/runs/conf to modify them easily
        self.dev_mode = dev_mode
        # assert to resolve hostname
        if hostname is None:
            hostname = self.default_hostname
        if hostname not in self.packages:
            msg = "hostname: {} not found in packages config files: cannot setup packages !".format(hostname)
            print(msg)
            self.packages_print()
            raise ValueError(msg)
        self._set_XP_directory()
        os.chdir(self.xp_path)
        self._get_tasks()
        self._set_conf()
        self._get_runs()
        self._link_packages()
        print("DAVAI xp has been successfully setup.")
        print("------------------------------------")

    def _get(self, source, target):
        if self.dev_mode:
            os.symlink(source, target)
        else:
            if os.path.isfile(source):
                shutil.copy(source, target)
            else:
                shutil.copytree(source, target)

    def _set_XP_directory(self):
        if os.path.exists(self.xp_path):
            raise FileExistsError('XP directory: {} already exists'.format(self.xp_path))
        else:
            os.makedirs(self.xp_path)

    def _get_tasks(self):
        self._get(os.path.join(DAVAI_THIS_REPO, 'tasks'),
                  'tasks')

    def _set_conf(self):
        # initialize
        os.makedirs('conf')
        config_file = os.path.join('conf', 'davai_{}.ini'.format(self.vconf))
        self._get(os.path.join(DAVAI_THIS_REPO, config_file),
                  config_file)
        to_set_in_config = {k:getattr(self, k)
                            for k in
                            ('IAL_git_ref', 'IAL_repository', 'usecase', 'comment')}
        # and replace:
        # (here we do not use ConfigParser to keep the comments)
        with io.open(config_file, 'r') as f:
            config = f.readlines()
        for i, line in enumerate(config):
            if line[0] not in (' ', '#', '['):  # special lines
                for k, v in to_set_in_config.items():
                    pattern = '(?P<k>{}\s*=).*\n'.format(k)
                    match = re.match(pattern, line)
                    if match:
                        config[i] = match.group('k') + ' {}\n'.format(v)
                        print(" -> set in config: {}".format(config[i].strip()))
        with io.open(config_file, 'w') as f:
            f.writelines(config)

    def _get_runs(self):
        for r in ('run.sh', 'setup_ciboulai.sh', 'packbuild.sh',
                  '{}_tests.sh'.format(self.usecase)):
            self._get(os.path.join(DAVAI_THIS_REPO, 'runs', r), r)
        os.symlink('{}_tests.sh'.format(self.usecase), 'tests.sh')

    def _link_packages(self):
        for package in self.packages_list():
            os.symlink(self.package_path(package), package)

    def _read_packages_config(self):
        self.packages = configparser.ConfigParser()
        print("(packages config read from: {})".format(self.DAVAI_PACKAGES_CONFIG))
        self.packages.read(self.DAVAI_PACKAGES_CONFIG)

    def _read_packages_local_config(self):
        if not hasattr(self, 'packages'):
            self.packages = configparser.ConfigParser()
        loc = configparser.ConfigParser()
        if os.path.exists(self.DAVAI_LOCAL_PACKAGES_CONFIG):
            print("(packages config read from: {})".format(self.DAVAI_LOCAL_PACKAGES_CONFIG))
            loc.read(self.DAVAI_LOCAL_PACKAGES_CONFIG)
        else:
            print("(ignore local packages config (absent): {})".format(self.DAVAI_LOCAL_PACKAGES_CONFIG))
        for section in loc.sections():
            if not self.packages.has_section(section):
                self.packages.add_section(section)
            for k in loc[section]:
                self.packages[section][k] = loc[section][k]

    def packages_print(self):
        for h in self.packages.sections():
            print('[{}]'.format(h))
            for p in self.packages_list():
                print('{} = {}'.format(p, self.package_path))

    def package_path(self, package, hostname=None):
        if hostname is None:
            hostname = self.default_hostname
        if not self.packages.has_section(hostname):
            raise ValueError("hostname unknown in config packages.ini: " + hostname)
        return self.packages[hostname][package]

    def packages_list(self, hostname=None):
        if hostname is None:
            hostname = self.default_hostname
        if not self.packages.has_section(hostname):
            raise ValueError("hostname unknown in config packages.ini: " + hostname)
        return [package for package in self.packages[hostname]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a Davai experiment based on a Git reference.')
    parser.add_argument('IAL_git_ref',
                        help="IFS-Arpege-LAM Git reference to be tested")
    parser.add_argument('-u', '--usecase',
                        default='NRV',
                        help="Usecase: NRV (default, restrained set of canonical tests) or ELP (extended elementary tests)")
    parser.add_argument('-c', '--comment',
                        default=None,
                        help="Comment about experiment. Defaults to IAL_git_ref.")
    parser.add_argument('-r', '--IAL_repository',
                        default=DAVAI_IAL_REPOSITORY,
                        help="Path to IFS-Arpege-LAM Git repository. " +
                             "Default ({}) can be set through $DAVAI_IAL_REPOSITORY".format(DAVAI_IAL_REPOSITORY))
    parser.add_argument('--host',
                        default=DAVAI_HOST,
                        help="Generic name of host machine, in order to find paths to necessary packages. " +
                             "Default is guessed ({}), or can be set through $DAVAI_HOST".format(DAVAI_HOST))
    parser.add_argument('-d', '--dev_mode',
                        default=False,
                        action='store_true',
                        help="to link tasks sources rather than to copy them")
    args = parser.parse_args()

    XP = AnXP(args.IAL_git_ref,
              usecase=args.usecase,
              comment=args.comment,
              IAL_repository=args.IAL_repository,
              hostname=args.host)
    XP.setup(dev_mode=args.dev_mode)

