import os
from datetime import datetime

class excel_writer():
    def __init__(self, filename=''):
        self.fileName = filename
        self.abs_fileName = ''
        self.newFile = False
        self.wb = None

    def open_file(self):
        cur_dir = os.getcwd()
        if not self.fileName:
            self.fileName = 'default-excel' + '-' + datetime.now().strftime('%y%m%d-%H%M') + '.xlsx'
            self.abs_fileName = os.path.join(cur_dir, self.fileName)
            self.newFile = True
        else:
            self.abs_fileName = os.path.join(cur_dir, self.fileName)
            if not os.path.exists(self.abs_fileName):
                print('Warning: cannot find', self.fileName, 'in currect dir', cur_dir)
                print('\tcreate a new excel:')
                print('\t', self.abs_fileName)
                self.newFile = True
