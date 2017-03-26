#!/usr/bin/python
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
import boto3
import logging
import logging.handlers
from logging.handlers import SysLogHandler
import subprocess
import argparse
import ConfigParser
import os
import sys

# logrotate file location
LOGROTATE_FILE = '/etc/logrotate.d/s3duplicity-backup'
# rsyslog configuration file location
RSYSLOG_FILE = '/etc/rsyslog.d/22-s3duplicity-backup.conf'

# Create SysLogHandler
sysl = SysLogHandler(address='/dev/log', facility=SysLogHandler.LOG_USER) 
sysl.setFormatter(logging.Formatter('%(name)s: %(lineno)d - %(levelname)s - %(message)s'))
# Create logger with desired output level
logger = logging.getLogger('s3duplicity-backup')
logger.setLevel(logging.DEBUG)
# Add handler to logger
logger.addHandler(sysl)


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
def yes_or_no(question):
    """
    simple python function for getting a yes or no answer.
    """
    reply = str(raw_input(question+' (y/n): ')).lower().strip()
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return yes_or_no("Uhhhh... please enter ")

# Check if rsyslog file exists, if not ask to create it.
if not os.path.exists(RSYSLOG_FILE):
     logger.error("Can't find rsyslog file: %s " % RSYSLOG_FILE)
     print("ERROR: Can't find rsyslog file: %s \n" % RSYSLOG_FILE)
     answer = yes_or_no("Do you want to create %s file ? " % RSYSLOG_FILE)
     if answer:
	rsyslog_file()

# Check if logrotate file exists, if not ask user to create it.
if not os.path.exists(LOGROTATE_FILE):
     logger.error("Can't find logrotate file: %s " % LOGROTATE_FILE)
     print("ERROR: Can't find logrotate file: %s \n" % LOGROTATE_FILE)
     answer = yes_or_no("Do you want to create %s file ? " % LOGROTATE_FILE)
     if answer:
	logrotate_file()

#----------------------------------------------------------------------

# File configuration path
path = "/opt/s3duplicity/s3duplicity-settings.ini"
if not os.path.exists(path):
     logger.error("Can't find config file: %s exit.." % path)
     sys.exit("ERROR: Can't find config file: %s exit.." % path)

config = ConfigParser.ConfigParser()
config.read(path)

# Read values from configuration file
source_directory = config.get("Global", "source-directory")
target_url = config.get("Global", "target-url")
restore_dir = config.get("Global", "restore-dir")
aws_region = config.get("Global", "region")
full_if_older_than = config.get("Options", "full-if-older-than")
remove_time = config.get("Options", "remove-time")
restore_time = config.get("Options", "restore-time")
file_prefix = config.get("Options", "file-prefix")
volsize = config.get("Options", "volsize")
log_file = config.get("Options", "logfile")
arn_sns = config.get("Options", "arnsns")


# Define AWS SNS message service.
client = boto3.client('sns',region_name=aws_region)

def send_sns(text):
    """
    Send mail if backup faild , using AWS SNS service.
    """
    response = client.publish(
    TopicArn=arn_sns,
    Message= text,
    Subject='Duplicity backup Error.'
       )
#    print("Response: {}".format(response))


# Define backup to s3 function
def backup_tos3(extra):
    """
    Backup directory to the to the s3 bucket location.
    """
    # Command to run
    try:
        prog = '/usr/bin/duplicity'
	param = ['--full-if-older-than '+full_if_older_than,
		'--no-encryption',
		'--file-prefix '+file_prefix,
		'--s3-european-buckets',
		'--s3-use-new-style',
		'--volsize '+volsize,
		source_directory,
		's3+http://'+target_url
		]
	param[0:0] = extra
	logger.info("Start duplicity")
	# Join cmd list, and run it as a command
	cmd = "%s %s" % (prog,(' '.join(param)))
	# run a command and PIPE output and error backup to subprocess
	p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(out,err) = p.communicate()

	if p.returncode == 0:
	    print ("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	    send_sns(out)
	    logger.info("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	elif p.returncode <= 125:
	    print ("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	    logger.error("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	    send_sns(err)
	elif p.returncode == 127:
	    logger.error("program '%s' not found: %s" % (prog, str(err)))
	    send_sns(err)
	else:
	    # Things get hairy and unportable - different shells return
	    # different values for coredumps, signals, etc.
	    send_sns("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
	    sys.exit("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
    except OSError as e:
    # unlikely, but still possible: the system failed to execute the shell
    # itself (out-of-memory, out-of-file-descriptors, and other extreme cases).
	send_sns("failed to run shell: '%s'" % (str(e)))
	sys.exit("failed to run shell: '%s'" % (str(e)))
	
#----------------------------------------------------------------------


# Define remove from s3 function
def remove_froms3(extra):
    """
    Delete all backup sets older than the given time.
    Old backup sets will not be deleted if backup sets newer than time depend on them.
    """
    # Command to run
    try:
        prog = '/usr/bin/duplicity'
	param = ['remove-older-than '+remove_time,
	    '--no-encryption',
	    '--file-prefix '+file_prefix,
	    '--s3-european-buckets',
	    '--s3-use-new-style',
	    's3+http://'+target_url,
	    '--force'
               ]
        param[0:0] = extra
	logger.info("Start duplicity")
	# Join cmd list, and run it as a command
	cmd = "%s %s" % (prog,(' '.join(param)))
	# run a command and PIPE output and error backup to subprocess
	p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(out,err) = p.communicate()

	if p.returncode == 0:
	    print ("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	    logger.info("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	elif p.returncode <= 125:
	    print ("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	    logger.error("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	elif p.returncode == 127:
	    logger.error("program '%s' not found: %s" % (prog, str(err)))
	else:
	    # Things get hairy and unportable - different shells return
	    # different values for coredumps, signals, etc.
	    sys.exit("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
    except OSError as e:
    # unlikely, but still possible: the system failed to execute the shell
    # itself (out-of-memory, out-of-file-descriptors, and other extreme cases).
	sys.exit("failed to run shell: '%s'" % (str(e)))

#-------------------------------------------------------------------------------------------------

# Define restore from s3 function
def restore_froms3(extra):
    """
    You can restore the full monty or selected folders/files from a specific time.
    """
    # Command to run
    try:
        prog = '/usr/bin/duplicity'
	param = ['-t '+restore_time,
	    '--no-encryption',
	    '--file-prefix '+file_prefix,
	    '--s3-european-buckets',
	    '--s3-use-new-style',
	    's3+http://'+target_url,
            restore_dir,
               ]
	param[0:0] = extra
	logger.info("Start duplicity")
	# Join cmd list, and run it as a command
	cmd = "%s %s" % (prog,(' '.join(param)))
	# run a command and PIPE output and error backup to subprocess
	p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(out,err) = p.communicate()

	if p.returncode == 0:
	    print ("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	    logger.info("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	elif p.returncode <= 125:
	    print ("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	    logger.error("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	elif p.returncode == 127:
	    logger.error("program '%s' not found: %s" % (prog, str(err)))
	else:
	    # Things get hairy and unportable - different shells return
	    # different values for coredumps, signals, etc.
	    sys.exit("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
    except OSError as e:
    # unlikely, but still possible: the system failed to execute the shell
    # itself (out-of-memory, out-of-file-descriptors, and other extreme cases).
	sys.exit("failed to run shell: '%s'" % (str(e)))


# ----------------------------------------------------------------------------------------------------

# Define list files from s3 function
def lists3_file():
    """
    Lists the files contained in the most current backup or backup at time.
    """
    # Command to run
    try:
        prog = '/usr/bin/duplicity'
	param = ['list-current-files',
	    '--no-encryption',
	    '--file-prefix '+file_prefix,
	    '--s3-european-buckets',
	    '--s3-use-new-style',
	    's3+http://'+target_url,
               ]
	logger.info("Start duplicity")
	# Join cmd list, and run it as a command
	cmd = "%s %s" % (prog,(' '.join(param)))
	# run a command and PIPE output and error backup to subprocess
	p = subprocess.Popen(cmd,shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(out,err) = p.communicate()

	if p.returncode == 0:
	    print ("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	    logger.info("command '%s' succeeded, returned: %s" \
		   % (cmd, str(out)))
	elif p.returncode <= 125:
	    print ("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	    logger.error("command '%s' failed, exit-code=%d error = %s" \
		   % (cmd, p.returncode, str(err)))
	elif p.returncode == 127:
	    logger.error("program '%s' not found: %s" % (prog, str(err)))
	else:
	    # Things get hairy and unportable - different shells return
	    # different values for coredumps, signals, etc.
	    sys.exit("'%s' likely crashed, shell retruned code %d" % (cmd,e.returncode))
    except OSError as e:
    # unlikely, but still possible: the system failed to execute the shell
    # itself (out-of-memory, out-of-file-descriptors, and other extreme cases).
	sys.exit("failed to run shell: '%s'" % (str(e)))

# Get argument from command line
def get_args():
    """
    Parses the command line.
    """

    # Assign description
    parser = argparse.ArgumentParser(description='Wrapper for scripting duplicity.',epilog='Example of use:')
   
    # Run default backup if True
    parser.add_argument('--restore', action='store_true', default=False, help='You can restore the full monty or selected folders/files from a specific\
										 time. Use the relative path as it is printed by list-current-files..')
    parser.add_argument('--lists3', action='store_true', default=False, help='Lists the files contained in the most current backup or backup at time.')
    parser.add_argument('--s3backup', action='store_true', default=False, help='Run a backup to the s3 bucket location')
    parser.add_argument('--remove', action='store_true', default=False, help='Delete all backup sets older than the given \
                                                                              time stored ini file configuration.')
    parser.add_argument('--dry-run', action='append_const', dest='const_collection',
                        const='--dry-run',
                        default=[ ],
                        help='Calculate what would be done, but do not perform any backend actions'
                       )
    
    parser.add_argument('--incr', action='append_const', dest='const_collection',
                        const='incr',
                        default=[ ],
                        help='If this is requested an incremental backup will be performed.'
		       )
    
    args =  parser.parse_args()
# Add argument not in config file
    extra = args.const_collection
    number = 0
    if args.lists3:
	number += 10
    if args.s3backup:
	number += 20
    if args.remove:
	number += 50
    if args.restore:
	number += 90

# Check no conflict args given
    if number == 0:
	sys.exit("No args given")
    elif number == 10:
	lists3_file()
	logger.info("lists3_file argument parses: %s " % args)
    elif number == 20:
	backup_tos3(extra)
	logger.info("s3backup argument parses: %s " % args)
    elif number == 50:
	remove_froms3(extra)
	logger.info("remove_froms3 argument parses: %s " % args)
    elif number == 90:
	restore_froms3(extra)
	logger.info("restore_froms3 argument parses: %s " % args)
    else:
	sys.exit("Command line error: Enter '--help' for help screen")

#----------------------------------------------------------------------
if __name__ == "__main__":
    get_args()
