#!/usr/bin/env python3

# The logfile.
dflt_logfile = '/var/log/optools/optools.log'

# The default log level. Can be one of (in increasing levels of output):
# critical
# error
# warning
# info
# debug
# "debug" may log sensitive information! Do *not* use it unless ABSOLUTELY
# NECESSARY.
dflt_loglevel = 'warning'

# stdlib
import datetime
import logging
import logging.handlers
import os

class log(object):
    def __init__(self, loglvl = dflt_loglevel, logfile = dflt_logfile,
                 logname = 'optools'):
        # Loglevel mappings.
        self.loglvls = {'critical': logging.CRITICAL,
                        'error': logging.ERROR,
                        'warning': logging.WARNING,
                        'info': logging.INFO,
                        'debug': logging.DEBUG}
        self.loglvl = loglvl.lower()
        if self.loglvl not in self.loglvls:
            raise ValueError(('{0} is not one of: ' +
                              '{1}').format(loglvl,
                                            ', '.join(self.loglvls.keys())))
        self.Logger = logging.getLogger(logname)
        self.logfile = os.path.abspath(os.path.expanduser(logfile))
        try:
            os.makedirs(os.path.dirname(self.logfile),
                        exist_ok = True,
                        mode = 0o700)
        except Exception as e:
            # Make this non-fatal since we also log to journal for systemd?
            raise e
        self.chkSystemd()
        self.journald()
        self.Logger.setLevel(self.loglvls[self.loglvl])
        self.log_handlers()

    def chkSystemd(self):
        # Add journald support if we're on systemd.
        # We probably are since we're most likely on Arch, but we don't want to
        # make assumptions.
        self.systemd = False
        _sysd_chk = ['/run/systemd/system',
                     '/dev/.run/systemd',
                     '/dev/.systemd']
        for _ in _sysd_chk:
            if os.path.isdir(_):
                self.systemd = True
                break
        return()

    def journald(self):
        if not self.systemd:
            return()
        try:
            from systemd import journal
        except ImportError:
            try:
                import pip
                pip.main(['install', '--user', 'systemd'])
                from systemd import journal
            except Exception as e:
                # Build failed. Missing gcc, disk too full, whatever.
                self.systemd = False
        return()

    def log_handlers(self):
        # Log formats
        if self.systemd:
            _jrnlfmt = logging.Formatter(fmt = ('{levelname}: {message} ' +
                                                '({filename}:{lineno})'),
                                         style = '{',
                                         datefmt = '%Y-%m-%d %H:%M:%S')
        _logfmt = logging.Formatter(fmt = ('{asctime}:{levelname}: {message} (' +
                                           '{filename}:{lineno})'),
                                    style = '{',
                                    datefmt = '%Y-%m-%d %H:%M:%S')
        # Add handlers
        _dflthandler = logging.handlers.RotatingFileHandler(self.logfile,
                                                            encoding = 'utf8',
                                                            # 1GB
                                                            maxBytes = 1073741824,
                                                            backupCount = 5)
        _dflthandler.setFormatter(_logfmt)
        _dflthandler.setLevel(self.loglvls[self.loglvl])
        if self.systemd:
            from systemd import journal
            try:
                h = journal.JournaldLogHandler()
            except AttributeError:  # Uses the other version
                h = journal.JournalHandler()
            h.setFormatter(_jrnlfmt)
            h.setLevel(self.loglvls[self.loglvl])
            self.Logger.addHandler(h)
        self.Logger.addHandler(_dflthandler)
        self.Logger.info('Logging initialized')
        return()
