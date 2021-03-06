#!bin/python
import sys, os, getopt, string, re
import json
import csv
from datetime import datetime
import paramiko

project_kernel=["vied-viedandr-linux_drivers", "vied-viedandr-camera", "vied-viedandr-gsd-lpisp-fw"]
project_linux_hal=["vied-viedandr-libcamhal", "vied-viedandr-icamerasrc"]
project_andr_hal=["vied-viedandr-camera3hal", "vied-viedandr-camera_extension",\
        "vied-viedandr-cameralibs", "vied-viedandr-libcamera2", "vied-viedandr-libiacss"]
project_test=["vied-viedandr-android-tests", "vied-viedlin-applications"]

ICG_GERRIT_ADDR = 'icggerrit.corp.intel.com'
QUERY_ARGS_DEFAULT = '--current-patch-set --comments '

class Download:
    def __init__(self, project_l=None, start_d=None, brch=None,
            change_ids=None):
        self.gerrit_addr = ICG_GERRIT_ADDR
        self.query_args = QUERY_ARGS_DEFAULT
        self.project_list = project_l
        self.mergeDate_start = start_d
        self.branch = brch
        self.changeid_list = change_ids
    def add_query_args(self, args):
        self.query_args += args
    def set_project_list(self, p_list):
        self.project_list += p_list[:]
    def set_start_date(self, d):
        self.mergeDate_start = d
    def set_branch(self, b):
        self.branch = b
    def set_changeid_list(self, id_list):
        self.changeid_list += id_list[:]

    def compose_query(self, os_str):
        if self.project_list:
            query_proj = 'AND (project:'+self.project_list[0]
            for p in self.project_list[1:]:
                query_proj += ' OR project:' + p
            query_proj += ')'
        else:
            query_proj = ''
        print("query_proj:", query_proj)

        if self.mergeDate_start:
            query_startD = 'AND after:' + \
                            self.mergeDate_start.strftime('%Y-%m-%d')
        #don't need add endDate in query command
        else:
            query_startD = ''

        if self.branch:
            query_branch = 'AND branch:' + self.branch
        else:
            query_branch = ''

        if self.changeid_list:
            query_changeid = 'AND (change:' + self.changeid_list[0]
            for p in self.changeid_list[1:]:
                query_changeid += ' OR change:' + p
            query_changeid += ')'
        else:
            query_changeid = ''

        if (os_str == 'linux'):
            query_base = 'ssh -p 29418 {addr} gerrit query ' +\
                '--format=JSON "status:merged {startD} {branch} {proj} ' +\
                '{changeid}" {args}'
            down_cmd = query_base.format(
                addr=self.gerrit_addr, proj=query_proj, args=self.query_args,
                startD=query_startD, branch=query_branch,
                changeid=query_changeid)
        elif (os_str == 'win'):
            query_base = 'gerrit query ' +\
                '--format=JSON "status:merged {startD} {branch} {proj} ' +\
                '{changeid}" {args}'
            down_cmd = query_base.format(
                proj=query_proj, args=self.query_args,
                startD=query_startD, branch=query_branch,
                changeid=query_changeid)
        else:
            print("Error: os string isn't linux or win!")
            raise
        #print('\tdownload command: ', down_cmd)
        return down_cmd

    def query(self):
        """
        down_patch, and save json to list, remove "moreChanges" lines.
        """
        if os.name == 'posix':
            return self.query_lin()
        if os.name == 'nt':
            return self.query_win()

    def query_lin(self):
        cmd = self.compose_query('linux')
        endline = 0
        orig_cmd = cmd
        raw_list = []
        while True:
            result=os.popen(cmd) # need change to subprocess to check exit code
            for line in result:
                patch = json.loads(line)
                raw_list.append(patch)
            if not raw_list[-1].get('moreChanges'):
                del raw_list[-1]
                print("\tquery_patch done, patch #:", len(raw_list))
                break
            else:
                endline += raw_list[-1].get('rowCount',0)
                cmd = orig_cmd + ' --start ' + str(endline)
                del raw_list[-1]
                print("\tmore changes, keep query_patch from lines %d" % endline)

        return raw_list

    def query_win(self):
        cmd = self.compose_query('win')

        priv_fn = 'rsa_key.priv'
        cur_dir = os.getcwd()
        #if priv_fn not in os.listdir(cur_dir):
        if not os.path.exists(os.path.join(cur_dir, priv_fn)):
            print('Error: private key file', priv_fn, 'not find in current dir!')
            print('current dir:', cur_dir)
            raise
        try:
            key = paramiko.RSAKey.from_private_key_file(priv_fn)
        except:
            print('Error: fail to get private key from file', priv_fn)
            raise

        #get user name
        user = ''
        needsave = False
        conf_file = os.path.join(cur_dir, 'username')
        if not os.path.exists(conf_file):
            print('Fail to find username file under current dir.')
            while not user:
                user = input("Please input your user id to login gerrit: ")
            needsave = True
        else:
            with open(conf_file, 'r') as f:
                try:
                    result = f.readline()
                    user = result.splitlines()[0]
                except:
                    print('Error: fail to read user name from username file')
                while not user:
                    user = input("Please input your user id to login gerrit: ")
                    needsave = True
        if needsave:
            print('\tget user name:', '"'+str(user)+'"', ', saving it to', conf_file)
            with open(conf_file, 'w') as f:
                try:
                    f.write(user)
                except:
                    print('Error: fail to write username file')
                    print('Please save user name in current dir with file name "username".')

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.load_system_host_keys()
        ssh.connect(ICG_GERRIT_ADDR, 29418, user, pkey=key)

        endline = 0
        orig_cmd = cmd
        raw_list = []
        while True:
            try:
                s_in, result, s_err = ssh.exec_command(cmd)
            except EOFError:
                print('ssh error, will try again...')
                ssh.connect(ICG_GERRIT_ADDR, 29418, user, pkey=key)
                s_in, result, s_err = ssh.exec_command(cmd)
            for line in result:
                patch = json.loads(line)
                raw_list.append(patch)
            if not raw_list[-1].get('moreChanges'):
                del raw_list[-1]
                print("\tquery_patch done, downloaded raw #:", len(raw_list))
                break
            else:
                endline += raw_list[-1].get('rowCount',0)
                cmd = orig_cmd + ' --start ' + str(endline)
                del raw_list[-1]
                print("\tmore changes, keep query_patch from lines %d" % endline)

        return raw_list
