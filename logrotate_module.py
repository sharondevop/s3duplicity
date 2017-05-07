#!/usr/bin/env python
#######################################################################
#    s3duplicity backup program for duplicity
#    Copyright (C) 2017 Sharon Mafgaoker.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
##########################################################################
# Create function to create logrotate file.
def logrotate_file():
    """
    Create logrotate file for s3duplicity-backup program.
    """
# Check if script run with root
    if not os.geteuid() == 0:
        logger.error("Can't create logrotate file %s : must be run as root" % LOGROTATE_FILE)
        sys.exit("ERROR: Can't create logrotate file %s : must be run as root" % LOGROTATE_FILE)

    logger.info("Trying to create logrotate file: %s " % LOGROTATE_FILE)
    try:
        f = open(LOGROTATE_FILE, 'w+')
        f.write('''/var/log/s3duplicity-backup.log {
    daily
    rotate 7
    missingok
    notifempty
    dateext
    create 0600 root root
    copytruncate
}\n''')
        f.close()
        logger.info("Successfully created logrotate file: %s " % LOGROTATE_FILE)
    except Exception as e:
        logger.error(str(e))
        print(str(e))
    log_enable = subprocess.check_output(['logrotate', LOGROTATE_FILE])
    print log_enable

# Create function to create rsyslog configuration file.
def rsyslog_file():
    """
    Create rsyslog configuration file for backup-duplicity program.
    """
# Check if script run with root
    if not os.geteuid() == 0:
        logger.error("Can't create rsyslog file %s : must be run as root" % RSYSLOG_FILE)
        sys.exit("ERROR: Can't create rsyslog file %s : must be run as root" % RSYSLOG_FILE)

    logger.info("Trying to create rsyslog file: %s " % RSYSLOG_FILE)
    try:
        f = open(RSYSLOG_FILE, 'w+')
        f.write('''# Log backup-duplicity generated log messages to file
:programname, isequal, "s3duplicity-backup" /var/log/s3duplicity-backup.log

# comment out the following line to allow BACKUP-DUPLICITY messages through.
# Doing so means you'll also get S3DUPLICITY BACKUP messages in /var/log/syslog
& ~
\n''')
        f.close()
        logger.info("Successfully created rsyslog file: %s " % RSYSLOG_FILE)
    except Exception as e:
        logger.error(str(e))
        print(str(e))
    rsyslog_restart = subprocess.check_output(['service', 'rsyslog', 'restart'])
    print syslog_restart

# Create function - asking user for action
