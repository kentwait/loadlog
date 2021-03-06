#!/usr/bin/env python3
"""
loadlog.py

Log system-wide CPU temp and load, fan speed and memory usage. Uses Python 3 to record how running a particular program
affects CPU temperature and load, fan speed, and overall memory usage. Any program that can be launched from the
command line can be profiled by this script.

Tested on OS X 10.9.5, Python 3.4

Requirements
------------
istats : Ruby gem
    Command-line program that outputs overall CPU temperature and fan speed
    Install using command `gem install iStats`
    URL: https://github.com/Chris911/iStats

psutil : Python 3 module
    Install using `pip3 install psutil`
    URL: https://pythonhosted.org/psutil/

Usage
-----
loadlog.py <"command"> [options]


How it works
------------
This script records system stats before the target program is launched, while the target is running, and
after a certain period of time after the program has finished.

To use this script, you must pass a command that you want to execute flanked by " ". Enter any command-line based
command as you would type it in Terminal. You can also pass it optional arguments such as the computer name to be
printed on the log file and the amount of time between recordings.

The script first instantiates a stats object and records system constants such as how many cpu cores are present
and how much memory is installed. It also records load, temperature and fan speed before the command is executed
(pre-run). After a certain amount of time (prewait), the script executes the command passed to it
as a child process. While the program is running (child process is active), the script records cpu and memory load stats
on a log file. After a predetermined amount time (postwait) after the command finishes executing,
the script again records cpu and memory load of the post-run state.

"""
__author__ = 'Kent Kawashima'
__version__ = 0.1

import subprocess as proc
import re
import datetime
import psutil
import time
import argparse

class stats(object):

    def __init__(self, computer, command):
        self.computer = computer
        self.command = command
        self.cpu_physical_count = psutil.cpu_count(logical=False)
        self.cpu_logical_count = psutil.cpu_count(logical=True)
        self.total_memory = psutil.virtual_memory().total

    def now(self):
        cmd_lst = ['istats']
        self.datetime = datetime.datetime.now()
        istats_stdout = proc.check_output(cmd_lst).decode('utf-8')
        self.cpu_temp = []
        self.fan_speed = []
        for line in istats_stdout.split('\n'):
            if line.startswith('CPU'):
                self.cpu_temp.append(float(re.search('\d+\.\d+', line).group(0)))
            if line.startswith('Fan'):
                self.fan_speed.append(float(re.search('\d+\.\d+', line).group(0)))
        self.percpu_percent = psutil.cpu_percent(interval=0.1, percpu=True)
        self.cpu_percent = psutil.cpu_percent(interval=0.1, percpu=False)
        self._memory = psutil.virtual_memory()
        self.memory_percent = self._memory.percent
        self.memory_available = self._memory.available
        self.memory_used = self._memory.used

        summary = {'datetime': self.datetime.isoformat(sep=' '),
                   'cpu_temp': self.cpu_temp,
                   'fan_speed': self.fan_speed,
                   'percpu_percent': self.percpu_percent,
                   'memory_percent': self.memory_percent,
                   }
        return summary

def log_entry(entry, logfile_path):
    with open(args.logfile, 'a') as file_handle:
        print('+ {0}'.format(entry['datetime']), file=file_handle)
        print('  cpu_temp : {0}'.format(entry['cpu_temp']), file=file_handle)
        print('  fan_speed : {0}'.format(entry['fan_speed']), file=file_handle)
        print('  percpu_percent : {0}'.format(entry['percpu_percent']), file=file_handle)
        print('  memory_percent : {0}'.format(entry['memory_percent']), file=file_handle)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run a command-line program, '
                                                 'logging CPU and memory load during runtime',
                                     usage='loadlog.py <"command"> [options]')
    parser.add_argument('command', type=str, help='command and arguments necessary to run the target program '
                                                    'surrounded by " "')
    parser.add_argument('--prewait', type=int, default=0, help='Time (s) to wait between initial logging and '
                                                               'initializing the program')
    parser.add_argument('--interval', type=int, default=1800, help='Time interval (s) between logs. Minimum of 60s')
    parser.add_argument('--postwait', type=int, default=1800, help='Time (s) to wait after program has finished '
                                                                   'before recording final load log')
    #parser.add_argument('--poll_interval', type=int, default=60, help='Time interval (s) between polling')
    parser.add_argument('--computer', type=str, default='Unknown', help='Name of current machine')
    parser.add_argument('--logfile', type=str, default='load.log', help='Log file save path')
    args = parser.parse_args()

    s = stats(computer=args.computer, command=args.command)
    with open(args.logfile, 'w') as f:
        print('# computer : {0}'.format(s.computer), file=f)
        print('# command : {0}'.format(s.command), file=f)
        print('# cpu_cores : {0}'.format(s.cpu_physical_count), file=f)
        print('# logical_cores : {0}'.format(s.cpu_logical_count), file=f)
        print('# total_memory : {0}'.format(s.total_memory), file=f)
        print('# wait : {0}, {1}, {2}'.format(args.prewait, args.interval, args.postwait), file=f)

    log_entry(s.now(), f) # Get stats right before starting
    time.sleep(args.prewait)
    program = proc.Popen(args.command.split(' '))

    polled_time = 0
    while program.poll() is None:
        log_entry(s.now(), f)
        time.sleep(args.interval)
    time.sleep(args.postwait)
    log_entry(s.now(), f) # Log after completion