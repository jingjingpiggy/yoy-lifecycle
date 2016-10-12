#!bin/python
import sys, os, getopt, string, re
import json
import requests
import csv
from datetime import datetime

class Parser:
    """
    Parser: parse a patch, get required values and save in dict.
    If multiple lines per patch like 'files'/'comments' header,
    save as list[dict, dict,...] under the header. Handler class will
    covert it to multiple lines.
    """
    #map header to function name
    header_map = {
        'number': 'number', #int
        'changeId': 'changeId',
        'OwnerEmail': 'OwnerEmail',
        'Size+': 'SizePlus', #int
        'Size-': 'SizeMinus', #int
        'createdOn': 'createDate', #datetime
        'publishDate': 'publishDate', #datetime
        'mergeDate': 'mergeDate', #datetime
        'bugId': 'bugId',
        #'bugDB': (getBugDB, None)
        'ifCommon': 'ifCommon',
        'comments': 'comments',#([{comnts,revwr,date},..],[ignr_revwr])
        'all_reviewer': 'all_reviewer',
        'files': 'files' #[{file,s+,s-},..]
        }
    #headers that need get w/ comment and save in comment value map
    comment_subheader = ['reviewer', 'review-time', 'inline_comments']
    #sub-headers of comments to be parsed
    comment_subheader_in = []

    def start_parse(self, patch):
        self.raw_p = patch
        self.parsed_p = dict()
        self.comment_subheader_in = []
        self.parsed_p['number'] = self.get_value('number')

    def clear(self):
        self.raw_p = dict()
        self.comment_subheader_in = []

    def parse_all(self, headers):
        self.comment_subheader_in = [h for h in headers if h in self.comment_subheader]
        if self.comment_subheader_in and not 'comments' in headers:
            print("W: parse_all: comments not in headers but",\
                   str(self.comment_subheader_in), "is! Is this in purpose or a mistake?")
            print("              Will dump comments now.")
            headers.append('comments')
        for h in headers:
            if h not in self.comment_subheader_in:
                self.get_value(h)
        return self.parsed_p

    def get_value(self, header):
        """
        Return value of the header, and save in parsed_p dict.
        if header existed in header_map, call get_ func to get value;
        if not, directly read from raw_p dict (like project and subject)
        """
        value = self.parsed_p.get(header, 'not find')
        if value == 'not find':
            func_name = self.header_map.get(header, None)
            if func_name:
                method = getattr(self, 'get_'+func_name, None)
                if callable(method): value = method()
            else:
                value = self.raw_p.get(header, 'not find')
            self.parsed_p[header] = value
        return value

    def read_value(self, *params, input_dict=None):
        '''
        Function: get nested value from input dict
            params: keys to get the value, from outer to inner layer
            Return: the value
        '''
        keys = list(params)
        if input_dict:
            v = input_dict.get(keys.pop(0), 'not find')
        else:
            #if use None as default value, get 0 will be
            #considered as not find, so use not find
            v = self.raw_p.get(keys.pop(0), 'not find')
        while len(keys) > 0 and v != 'not find':
            v = v.get(keys.pop(0), 'not find')
        if v == 'not find':
            v = 'not find ' + str(params)
        return v

    def convert_timestamp(self, posix_ts):
        time_obj = datetime.fromtimestamp(posix_ts)
        #t_str = time_obj.strftime(date_fstr)
        return time_obj

    def get_number(self):
        try:
            v = int(self.read_value('number'))
        except:
            print('Error in:', str(self.raw_p))
            raise
        return v
    def get_changeId(self):
        return self.read_value('id')
    def get_OwnerEmail(self):
        return self.read_value('owner', 'email')
    def get_SizePlus(self):
        v = self.read_value('currentPatchSet', 'sizeInsertions')
        return int(v) if isinstance(v, int) else v
    def get_SizeMinus(self):
        v = self.read_value('currentPatchSet', 'sizeDeletions')
        return int(v) if isinstance(v, int) else v
    def get_createDate(self):
        ts = self.read_value('createdOn')
        if ts:
            time = self.convert_timestamp(ts)
        else:
            time = 'not find '+str(params[0])
        return time
    def get_publishDate(self):
        #don't use get_value, as get_comments only return human comments
        commentList = self.raw_p.get('comments')
        if not commentList or 'not find' in commentList:
            print('!!!Error: not find comments in patch',
                   self.get_value.get('number'))
            return 'not find comments in patch'

        publishComment = [c for c in commentList \
                         if 'Draft Published' in c['message']]
        if len(publishComment) == 0:
            #time = 'not find publish comments'
            time = ''
        else:
            #pick the last publish time
            review_ts = publishComment[-1].get('timestamp')
            if review_ts:
                time = self.convert_timestamp(review_ts)
            else:
                time = 'not find timestamp in comment'
        return time
    def get_mergeDate(self):
        commentList = self.raw_p.get('comments')
        if not commentList or 'not find' in commentList:
            print('!!!Error: not find comments in patch',
                   self.get_value('number'))
            return 'not find comments in patch'
        publishComment = [c for c in commentList if \
          'Change has been successfully cherry-picked' in c['message'] \
          or 'Change has been successfully pushed' in c['message'] \
          or 'Change has been successfully merged' in c['message']]
        if len(publishComment) == 0:
            time = 'not find merge comments'
        else:
            #pick the first merge time
            review_ts = publishComment[0].get('timestamp')
            if review_ts:
                time = self.convert_timestamp(review_ts)
            else:
                time = 'not find timestamp in merge comment:' + publishComment[0]
        return time
    def get_bugId(self):
        commitMesg = self.get_value('commitMessage')
        if not commitMesg or commitMesg.startswith('not find'):
            return "not find commit message in patch or it's null"
        buglist = ''
        p1 = re.compile(r'\s*Track[\w\s-]*On\s*:\s*', re.I)
        p2 = re.compile(r'\s*(Fix[\w\s-]*)?Issue\s*:\s*', re.I)
        #replace_p1 = re.compile(r'[\w\s:/]*jira01.devtools.intel.com[\w/]*browse/', re.I)
        #replace_p2 = re.compile(r'[\w\s:/]*hsdes.intel.com[\w/#\?]*id=/', re.I)
        #replace_p_list = [(replace_p1, '#J'), (replace_p2, '#H')]
        for line in commitMesg.splitlines():
            match = p1.match(line)
            if match:
                bugid = line[match.end():].strip()
                if bugid: # may nothing after TrackedOn
                    if buglist:
                        buglist = buglist + ', ' + bugid
                    else:
                        buglist = bugid
        if not buglist: #search for Issues: if not find Tracked-On
            for line in commitMesg.splitlines():
                match = p2.match(line)
                if match:
                    bugid = line[match.end():].strip()
                    if bugid:
                        if buglist:
                            buglist = buglist + ', ' + bugid
                        else:
                            buglist = bugid
        if not buglist:
            buglist = 'no TrackOn'
        else:
            buglist = buglist.replace('https://', '')
            buglist = buglist.replace('hsdes.intel.com/home/default.html#article?id=', '#H')
            buglist = buglist.replace('jira01.devtools.intel.com/browse/', '#J')
            buglist = buglist.replace('HSD', '#H')
            buglist = buglist.replace('HSD-', '#H')

        return buglist

    def get_ifCommon(self):
        p_proj = self.get_value('project')
        if 'notfind' in p_proj:
            raise Exception('get_ifCommon: Fail to project!')
        if p_proj != "vied-viedandr-camera3hal":
            return 'not AndrHAL'

        file_list = self.get_value('files')
        if 'not find' in file_list:
            raise Exception('get_ifCommon: Fail to get changed files!'+
                    ' Is "--files" addded in query?!')

        common_p = re.compile(r'cif[\w]*/|ipu2/|ipu4/|usb/|config/',
                                re.I)
        for item in file_list:
            filestr = item.get('file')
            if filestr and 'COMMIT_MSG' not in filestr:
                if not common_p.search(filestr):
                    #as long as common file find in patch, it's common
                    return 'common'
        return ''

    def get_files(self):
        '''
        Function: get patch changed files list
        Return: a list of dict which contains filestr, fileSize+ and
        fileSize-; or return a string w/ 'not find', if fail to find
        'file' in patch
        '''
        raw_list = self.read_value('currentPatchSet', 'files')
        if 'not find' in raw_list:
            raise Exception('get_ifCommon: Fail to get changed files!'+
                    ' Is "--files" addded in query?!')

        file_list = []
        for item in raw_list:
            filestr = item.get('file')
            if filestr and 'COMMIT_MSG' not in filestr:
                file_insert = item.get('insertions')
                file_del = item.get('deletions')
                file_list.append({
                        'file': filestr,
                        'fileSize+':file_insert,
                        'fileSize-':file_del
                        })
        if not file_list:
            file_list = 'not find file, raw_list: ' + str(raw_list)
        return file_list

    def get_comments(self):
        '''
        Function: dump human comments of the patch.
        If reviewer have no email or email doesn't have @intel.com,
        comments ignored. For debug, ignored reviewer set returned.
        Return: a tuple contains:
           1. a list of dict which contains comments, reviewer and
           reviewTObj(reviwe datetime obj);
           2. a list of ignored comments' reviewers
        '''
        raw_list = self.read_value('comments')
        if 'not find' in raw_list:
            raise Exception('getComments: Fail to get comments!')

        if 'inline_comments' in self.comment_subheader_in:
            patch_sets = self.read_value('patchSets')
            if 'not find' in patch_sets:
                raise Exception('getComments: inline: Fail to get',
                         'patch sets!')
            p_setNum = re.compile(r'\s*Patch Set (?P<num>\d+)\s*:', re.I)
            p_inlineNum = re.compile(r'\((?P<num>\d+) comments?\)', re.I)

        comment_list = []
        ignore_reviewer = []

        for c in raw_list:
            reviewer = self.read_value('reviewer','email',input_dict=c)
            if 'not find' in reviewer or '@intel.com' not in reviewer:
                #not human's comment, ignore
                ignore_reviewer.append(reviewer)
                continue
            comment_obj = dict()
            comment_obj['comments'] = c['message']
            if 'reviewer' in self.comment_subheader_in:
                comment_obj['reviewer'] = reviewer
            if 'review-time' in self.comment_subheader_in:
                review_ts = c['timestamp']
                reviewTObj = self.convert_timestamp(review_ts)
                comment_obj['review-time'] = reviewTObj

            if 'inline_comments' in self.comment_subheader_in:
                #if 'comment)' or 'comments)' in m, there is inline comments
                comment_obj['inline_comments'] = ''
                match = p_inlineNum.search(comment_obj['comments'])
                if match:
                    #get inline comment num of the comment
                    inline_num = int(match.group('num'))

                    #get patch set num of the comment
                    match_set = p_setNum.search(comment_obj['comments'])
                    if not match_set:
                        print('Error: get inline comment: fail to get patch',
                                 'set num from comment! inline_comments =',
                                 '"not find set num"')
                        print('\tpatch id:', self.parsed_p['number'])
                        comment_obj['inline_comments'] = 'not find set num'
                        continue

                    set_num = int(match_set.group('num'))
                    set_comments = []
                    for s in patch_sets:
                        try:
                            diff = s['number'] - set_num
                        except TypeError:
                            diff = int(s['number']) - set_num
                        if not diff:
                            if 'comments' in s:
                                set_comments = s['comments'] #set_comments link to patch_sets
                                break
                    if not set_comments: #some patch miss early sets info, like 73738
                        print('Error getComments: not find patch set', set_num,\
                                '! inline_comments="not find set"')
                        print('\tpatch id:', self.parsed_p['number'])
                        comment_obj['inline_comments'] = 'not find match'
                        continue
                        #Debug
                        print('\tcomment:', str(comment_obj))
                        #print('\tpatch sets:' ,patch_sets)

                    #find reviewer's comment in patch_sets, add in inline_comment
                    inline_str = ''
                    find_num = 0
                    for inline_c in set_comments[:]:
                        inline_reviewer = self.read_value('reviewer', 'email',
                                            input_dict=inline_c)
                        if inline_reviewer == reviewer:
                            try:
                                inline_str += 'line' + inline_c['line'] + ':"'
                            except TypeError:
                                inline_str += 'line' + str(inline_c['line']) + ':"'
                            inline_str += inline_c['message'] + '" '
                            set_comments.remove(inline_c)
                            find_num += 1
                            if find_num == inline_num:
                                break
                    if find_num == 0:
                        print('Error getComment: not find matched comments in',
                                'patch set! inline_comments="not find match"')
                        print('\tpatch id:', self.parsed_p['number'])
                        comment_obj['inline_comments'] = 'not find match'
                    elif find_num < inline_num:
                        print('Error: get inline comment:', inline_num,
                                'inline comments only find', find_num, '!')
                        print('\tpatch id:', self.parsed_p['number'])
                        print('\tset comment:',set_comments)
                        print('\tpatch sets:',patch_sets)
                        comment_obj['inline_comments'] = inline_str
                    else:
                        comment_obj['inline_comments'] = inline_str
                    #Debug
                    #print(str(comment_obj))

            comment_list.append(comment_obj)
        return comment_list, ignore_reviewer

    def get_all_reviewer(self):
        comments = self.get_value('comments')
        if comments == 'not find':
            print('E get all_reviewer: not find comments!',
                            'all_reviewer="not find comments"')
            print('\tpatch id:', self.parsed_p['number'])
            return 'not find comments'
        owner = self.get_value('OwnerEmail')
        all_reviewer = []
        p_integrator = re.compile(r'Integrator\s*[\+-]1|-Integrator|Validation-Android',\
                                    re.I)
        for c in comments[0]:
            if c['reviewer'] != owner and c['reviewer'] not in all_reviewer:
                if not p_integrator.search(c['comments']) or\
                        'Code-Review' in c['comments'] or 'Approver' in c['comments']:
                    all_reviewer.append(c['reviewer'])

        return ','.join(all_reviewer)



