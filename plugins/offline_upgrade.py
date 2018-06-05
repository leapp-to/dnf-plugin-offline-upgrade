from __future__ import absolute_import
from __future__ import unicode_literals
from dnfpluginscore import logger

import dnf
import json
import logging
import os

CMDS = ['download', 'clean', 'upgrade']
DEFAULT_DATADIR = '/var/lib/dnf/offline-upgrade'
DEFAULT_DESTDIR = '/tmp/offline-upgrade'


class State(object):
    statefile = '/var/lib/dnf/offline-upgrade.json'

    def __init__(self):
        self._data = {}
        self._read()

    def _read(self):
        try:
            with open(self.statefile) as fp:
                self._data = json.load(fp)
        except IOError:
            self._data = {}

    def write(self):
        dnf.util.ensure_dir(os.path.dirname(self.statefile))
        with open(self.statefile, 'w') as outf:
            json.dump(self._data, outf)

    def clear(self):
        if os.path.exists(self.statefile):
            os.unlink(self.statefile)
        self._read()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.write()

    def _prop(option):
        def setprop(self, value):
            self._data[option] = value

        def getprop(self):
            return self._data.get(option)
        return property(getprop, setprop)

    allow_erasing = _prop("allow_erasing")
    best = _prop("best")
    destdir = _prop("destdir")
    distro_sync = _prop("distro_sync")
    download_status = _prop("download_status")
    enable_disable_repos = _prop("enable_disable_repos")
    exclude = _prop("exclude")
    gpgcheck = _prop("gpgcheck")
    install_packages = _prop("install_packages")
    system_releasever = _prop("system_releasever")
    target_releasever = _prop("target_releasever")
    upgrade_status = _prop("upgrade_status")


@dnf.plugin.register_command
class OfflineUpgrade(dnf.cli.Command):

    name = 'offline-upgrade'
    aliases = ('offline-upgrade',)
    summary = 'Prepare system for an offline upgrade to a new release'

    def __init__(self, cli):
        super(OfflineUpgrade, self).__init__(cli)
        self.logger = logging.getLogger('dnf.plugin.offline_upgrade')
        self.state = State()

    @staticmethod
    def set_argparser(parser):
        parser.add_argument('subcommand',
                            nargs=1,
                            choices=CMDS,
                            metavar="[%s]" % "|".join(CMDS))
    
    def _check_release_ver(self, conf, target=None):
        if dnf.rpm.detect_releasever(conf.installroot) == conf.releasever:
            raise dnf.cli.CliError("Need a --releasever greater than the current system version")
        if target and target != conf.releasever:
            # it's too late to set releasever here, so this can't work.
            # (see https://bugzilla.redhat.com/show_bug.cgi?id=1212341)
            raise dnf.cli.CliError("Sorry, you need to use 'download --releasever' instead of '--network'")

    def _clear_dir(self, path):
        if not os.path.isdir(path):
            return
        
        for entry in os.listdir(path):
            fullpath = os.path.join(path, entry)
            try:
                if os.path.isdir(fullpath):
                    dnf.util.rm_rf(fullpath)
                else:
                    os.unlink(fullpath)
            except OSError:
                pass

    def pre_configure(self):
        self._call_sub("pre_configure")

    def configure(self):
        self._call_sub("configure")
        self._call_sub("check")

    def run(self):
        self._call_sub("run")

    def run_transaction(self):
        self._call_sub("transaction")

    def _call_sub(self, name):
        subfunc = getattr(self, name + '_' + self.opts.subcommand[0], None)
        if callable(subfunc):
            subfunc()

    def pre_configure_download(self):
        self.base.conf.cachedir = DEFAULT_DATADIR
        self.base.conf.destdir = DEFAULT_DESTDIR

    def pre_configure_clean(self):
        self.base.conf.cachedir = DEFAULT_DATADIR
        self.base.conf.destdir = self.state.destdir if self.state.destdir else None

    def pre_configure_upgrade(self):
        self.base.conf.cachedir = DEFAULT_DATADIR
        self.base.conf.destdir = self.state.destdir if self.state.destdir else None

        if self.state.enable_disable_repos:
            self.opts.repos_ed = self.state.enable_disable_repos

        self.base.conf.releasever = self.state.target_releasever

    def configure_download(self):
        self.cli.demands.available_repos = True
        self.cli.demands.freshest_metadata = True
        self.cli.demands.resolving = True
        self.cli.demands.root_user = True
        self.cli.demands.sack_activation = True
        # We want to do the depsolve / download / transaction-test, but *not*
        # run the actual RPM transaction to install the downloaded packages.
        # Setting the "test" flag makes the RPM transaction a test transaction,
        # so nothing actually gets installed.
        # (It also means that we run two test transactions in a row, which is
        # kind of silly, but that's something for DNF to fix...)
        self.base.conf.tsflags += ["test"]
        # and don't ask any questions
        self.base.conf.assumeyes = True

    def configure_clean(self):
        self.cli.demands.root_user = True

    def configure_upgrade(self):
        # same as the download, but offline and non-interactive. so...
        self.cli.demands.available_repos = True
        self.cli.demands.resolving = True
        self.cli.demands.root_user = True
        self.cli.demands.sack_activation = True
        self.opts.distro_sync = True

        # use the saved value for --allowerasing, etc.
        self.base.conf.best = self.state.best
        self.base.conf.exclude = self.state.exclude
        self.base.conf.gpgcheck = self.state.gpgcheck
        self.cli.demands.allow_erasing = self.state.allow_erasing

        # don't try to get new metadata, 'cuz we're offline
        self.cli.demands.cacheonly = True

        # and don't ask any questions (we confirmed all this beforehand)
        self.base.conf.assumeyes = True

    def check_download(self):
        self._check_release_ver(self.base.conf, target=self.opts.releasever)

        dnf.util.ensure_dir(self.base.conf.cachedir)
        if self.base.conf.destdir:
            dnf.util.ensure_dir(self.base.conf.destdir)

    def check_upgrade(self):
        if not self.state.upgrade_status == 'ready':
            raise dnf.cli.CliError("use 'dnf offline-upgrade download' to begin the upgrade")

    def run_download(self):
        self.base.distro_sync()

        with self.state as state:
            state.destdir = self.base.conf.destdir
            state.download_status = 'downloading'
            state.exclude = self.base.conf.exclude
            state.target_releasever = self.base.conf.releasever

    def run_clean(self):
        self.logger.info("Cleaning up downloaded data...")
        self._clear_dir(self.base.conf.cachedir)
        if self.base.conf.destdir:
            self._clear_dir(self.base.conf.destdir)
        with self.state as state:
            state.destdir = None
            state.download_status = None
            state.install_packages = {}
            state.upgrade_status = None

    def run_upgrade(self):
        # Change the upgrade status (so we can detect crashed upgrades later)
        with self.state as state:
            state.upgrade_status = 'incomplete'

        self.logger.info("Starting system upgrade. This will take a while.")

        # NOTE: We *assume* that depsolving here will yield the same
        # transaction as it did during the download, but we aren't doing
        # anything to *ensure* that; if the metadata changed, or if depsolving
        # is non-deterministic in some way, we could end up with a different
        # transaction and then the upgrade will fail due to missing packages.
        #
        # One way to *guarantee* that we have the same transaction would be
        # to save & restore the Transaction object, but there's no documented
        # way to save a Transaction to disk.
        #
        # So far, though, the above assumption seems to hold. So... onward!
        # Add the downloaded RPMs to the sack
        errs = []

        for repo_id, pkg_spec_list in self.state.install_packages.items():
            for pkgspec in pkg_spec_list:
                try:
                    self.base.install(pkgspec, reponame=repo_id)
                except dnf.exceptions.MarkingError:
                    self.logger.info("Unable to match package: %s", pkgspec + " " + repo_id)
                    errs.append(pkgspec)
        if errs:
            raise dnf.exceptions.MarkingError("Unable to match some of packages")

    def transaction_download(self):
        downloads = self.cli.base.transaction.install_set
        install_packages = {}
        for pkg in downloads:
            install_packages.setdefault(pkg.repo.id, []).append(str(pkg))

        # Okay! Write out the state so the upgrade can use it.
        system_ver = dnf.rpm.detect_releasever(self.base.conf.installroot)
        with self.state as state:
            state.allow_erasing = self.cli.demands.allow_erasing
            state.best = self.base.conf.best
            state.destdir = self.base.conf.destdir
            state.distro_sync = True
            state.download_status = 'complete'
            state.enable_disable_repos = self.opts.repos_ed
            state.gpgcheck = self.base.conf.gpgcheck
            state.install_packages = install_packages
            state.system_releasever = system_ver
            state.target_releasever = self.base.conf.releasever
            state.upgrade_status = 'ready'

        self.logger.info("Download complete! Use 'dnf offline-upgrade upgrade' to start the upgrade")
        self.logger.info("To remove cached metadata and transaction use 'dnf offline-upgrade clean'")

    def transaction_upgrade(self):
        self.logger.info("Upgrade complete! Cleaning up...")
        self.run_clean()
