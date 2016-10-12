#!bin/python
from downPatch import *
from parser1 import *
from datetime import datetime, timedelta

class Handler:
    """
    A Handler download patches from Gerrit, and convert json to patch
    list.
    """
    def __init__(self, parser, start_d, end_d, proj_list):
        self.parser = parser
        self.start_date = start_d
        self.end_date = end_d
        self.project_list = proj_list[:]
        self.patch_table = []
    def add_required_headers(self, h_list):
        self.required_headers += h_list
    def download_patch(self, proj_l=None, start_d=None, brch=None,
            changeids=None):
        downloader = Download(proj_l, start_d, brch, changeids)
        #check if need extra query args
        extr_set = {"ifCommon", "comments", "files"}
        if extr_set & set(self.required_headers):
            downloader.add_query_args('--files --patch-sets ')
        result = downloader.query()
        return result
    def parse_patches(self, raw_data, header=None, ignoreDate=False):
        done_table = []
        if not header:
            header = self.required_headers[:]
        for patch in raw_data:
            self.parser.start_parse(patch)
            if not ignoreDate:
            #ignore patches that merge date < start date or >= end date
                if self.start_date or self.end_date:
                    merge_date = self.parser.get_value('mergeDate')
                    try:
                        if (self.start_date and merge_date < self.start_date)\
                            or (self.end_date and merge_date >= self.end_date):
                            continue
                    except TypeError:
                        if isinstance(merge_date, str):
                            print("!!get MergeDate Error!! id:", self.parser.\
                                    get_value('number'), merge_date)

            handled_p = self.parser.parse_all(header)
            self.parser.clear()
            #print('handled patch:', handled_p['number'])
            done_table.append(handled_p)
        return done_table

class HandlerLifecycle(Handler):
    def __init__(self, parser, start_d, end_d, proj_list):
        Handler.__init__(self, parser, start_d, end_d, proj_list)
        self.required_headers = ['number','project','branch',\
            'changeId','OwnerEmail','status','subject','Size+',\
            'Size-','commitMessage','createdOn','publishDate',\
            'mergeDate', 'bugId']

class HandlerLifecycle_Andr(HandlerLifecycle):
    def handle(self):
        raw_data = self.download_patch(self.project_list, self.start_date)
        print('handle raw_data len:', len(raw_data))
        self.patch_table = self.parse_patches(raw_data)
        return self.patch_table

class HandlerLifecycle_Iotg(HandlerLifecycle):
    def match_patch(self, match_key, p, pt2):
        for p2 in pt2:
            if p[match_key] == p2[match_key]:
                p['sandboxID'] = p2['number']
                p['sandboxOwner'] = p2['OwnerEmail']
                p['sandboxCreated'] = p2['createdOn']
                p['sandboxPublished'] = p2['publishDate']
                p['sandboxMerged'] = p2['mergeDate']
                return True
        return False

    def handle(self):
        branch_linux={
            '0master': 'master', 
            '1sandbox': 'sandbox/yocto_startup_1214'
        }
        #get master patches
        raw_master = self.download_patch(self.project_list, \
                self.start_date, branch_linux['0master'])
        self.patch_table = self.parse_patches(raw_master)

        #get sandbox patches
        raw_sandbox = self.download_patch(self.project_list, \
                self.start_date, branch_linux['1sandbox'])
        sandbox_header = ['number','changeId','OwnerEmail','createdOn',\
                        'publishDate','mergeDate']
        sandbox_table = self.parse_patches(raw_sandbox, sandbox_header)

        #match 2 branches
        extra_header = ['sandboxID', 'sandboxOwner',\
                 'sandboxCreated', 'sandboxPublished', 'sandboxMerged']
        self.required_headers.extend(extra_header)
        miss_list = []
        for p in self.patch_table:
            if not self.match_patch('changeId', p, sandbox_table):
                miss_list.append(str(p['changeId']))

        #download not matched patches according to changeId
        if miss_list:
            print("download again for not found sandbox patches...")
            raw_miss = self.download_patch(brch=branch_linux['1sandbox'],\
                    changeids=miss_list)
            miss_patches = self.parse_patches(raw_miss, sandbox_header, True)
            for p in self.patch_table:
                if str(p['changeId']) in miss_list:
                    self.match_patch('changeId', p, miss_patches)

        return self.patch_table


class HandlerComments(Handler):
    def __init__(self, parser, start_d, end_d, proj_list):
        Handler.__init__(self, parser, start_d, end_d, proj_list)
        self.required_headers = ['number','project','branch',\
            'changeId','OwnerEmail','status','subject','commitMessage',\
            'createdOn','mergeDate','ifCommon','reviewer','review-time',\
            'comments','inline_comments','all_reviewer']

    def handle(self):
        raw_data = self.download_patch(self.project_list, self.start_date)
        print('\thandle raw_data len:', len(raw_data))
        self.patch_table = self.parse_patches(raw_data)
        #convert to multiple lines per patch for comments
        converted_table = self.convert_multilines(self.patch_table)
        return converted_table

    def convert_multilines(self, table):
        conv_t = []
        for p in table:
            comment_list = p['comments'][0]
            for c in comment_list:
                conv_line = {} #converted line
                #fill non-comment-related columns
                for head in [h for h in self.required_headers if h not in\
                                            self.parser.comment_subheader]:
                    if comment_list.index(c) == 0:
                        conv_line[head] = p[head]
                    elif head == 'mergeDate' or head == 'number':
                        conv_line[head] = p[head]
                    else:
                        conv_line[head] = ''
                for head in [h for h in self.required_headers if h in\
                                            self.parser.comment_subheader]:
                    conv_line[head] = c[head]
                conv_line['comments'] = c['comments']
                conv_t.append(conv_line)
        return conv_t

class HandlerComments_AndrHal(HandlerComments):
    def handle(self):
        raw_data = self.download_patch(self.project_list, self.start_date)
        print('\thandle raw_data len:', len(raw_data))
        self.patch_table = self.parse_patches(raw_data)
        #separate to diff table
        common_table, specific_table = [], []
        common_table, specific_table = self.split_table()
        #convert to multiple lines per patch for comments
        converted_common = self.convert_multilines(common_table)
        converted_specific = self.convert_multilines(specific_table)
        return converted_common, converted_specific

    def split_table(self):
        common_t, spec_t = [], []
        for p in self.patch_table:
            if p['ifCommon'] == 'common':
                common_t.append(p)
            else:
                spec_t.append(p)
        return common_t, spec_t



class GerritMetrics:
    # a map for get num from matrix
    # a table to save parsed matrix
    # interface to download/read matrix
    def __init__(self):
        self.header = []
        self.data = []
    def download(self, mergeDate_start, mergeDate_end, projects=None):
        #end date need -1 before use:
        mergeDate_end = mergeDate_end - timedelta(days=1)

        #Compose request url
        url_prefix = 'https://icggerrit.corp.intel.com:8081/metrics/get_data.php?action=reviewtimeNoWeekends&t='
        date_fmt = '%d-%m-%Y'
        date_str = mergeDate_start.strftime(date_fmt)+'|'+mergeDate_end.strftime(date_fmt)
        project_str = '&p='
        if not projects:
            print('GerritMetrics download: project list is null, will select all projects.')
            projects = project_andr_hal + project_linux_hal + project_kernel + project_test
        else:
            print('\t Pass in project list:', str(projects))
        for pjt in projects[:-1]:
            project_str += pjt
            project_str += '%2C'
        project_str += projects[-1]
        url_suffix = '&sort=value&format=csv'

        url = url_prefix + date_str + project_str + url_suffix
        #print('url: ', url)

        #Send request
        os.environ['NO_PROXY'] = 'intel.com'
        try:
            req_result = requests.get(url, verify=False)
        except:
            print("GerritMetrics download: Error to request, url:", url)
            raise
        if req_result.status_code != 200:
            print('request Gerrit Metrics Err: status_code:', req_result.status_code)
            return False

        #handle response result
        csv_iter = csv.DictReader(req_result.text.splitlines())
        self.header = csv_iter.fieldnames
        if not 'change_id' in self.header:
            print('request Gerrit Metrics Err: result wrong!\n', r.text[:150], '...')
            return False
        self.data = [r for r in csv_iter]
        return True

