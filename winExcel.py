from excel_general import *
if os.name == 'nt':
    import win32com.client
    import win32timezone

class excel_writer_win32(excel_writer):
    def __init__(self, filename=''):
        excel_writer.__init__(self, filename)
        self.excel = None
        
    def open_file(self):
        excel_writer.open_file(self)
        
        print('Open excel file:', self.fileName)
        if os.name != 'nt':
            print('Error: win32 excel writer cannot run on none windows env!')
            return -1
        self.excel = win32com.client.DispatchEx('Excel.Application')
        if self.newFile:
            self.wb = self.excel.Workbooks.Add()
        else:
            try:
                self.wb = self.excel.Workbooks.Open(self.abs_fileName, UpdateLinks=0)
            except:
                print('Error: fail to open', self.abs_fileName)
                print('Please make sure file openable and is not opened when launch the script')
                raise
        self.excel.Visible = True
        print('\tOpen excel file Done')
        return 0

    def delete_lines(self, ws, startline):
        lastRow = ws.Cells(ws.Cells.Rows.Count,1).End(-4162).Row #-4162 is value of xlUp
        if lastRow >= startline:
            del_rang = str(startline)+':'+str(lastRow)
            try:
                if not ws.Rows(del_rang).Delete(-4162):
                    print('Error: delete old rows error!')
                    print('\tsheet:', ws.Name, '\trows:', str(startline+2)+':'+str(lastRow))
                    print('\t continue, please manually delete these lines.')
            except Exception as err:
                print('Error: exception happens when delete old rows!')
                print('Exception Info:', err)
                print('\tsheet:', ws.Name, '\trows:', str(startline+2)+':'+str(lastRow))
                print('\t continue, please manually delete these lines.')
                
    def write_excel(self, header, value_d, sheetname=''):
        print('Start write excel:', self.fileName)
        newSheet = False
        
        if sheetname and sheetname in [sh.Name for sh in self.wb.Sheets]:
            ws = self.wb.Worksheets(sheetname)
        else:
            newSheet = True
            ws = self.wb.Worksheets.Add()
            ws.Name = sheetname
            if sheetname and not self.newFile:
                print('Warning: fail find sheet', sheetname, 'in file', self.abs_fileName+'.', 'Insert it in excel.')
            print('\twrite to sheet:', ws.Name)
    
        ws.Activate()
        #delete old lines
        if not newSheet:
            self.delete_lines(ws, len(value_d))
    
        #write first line
        header_range = ws.Range(ws.Cells(1,1), ws.Cells(1,len(header)))
        orig_header = str([c.Value for c in header_range])
        diff = False
        for j in range(1,len(header)+1):
            if not newSheet and ws.Cells(1,j).Value != header[j-1]:
                diff = True
            ws.Cells(1,j).Value = header[j-1]
    
        if diff:
            print('Warning: new headers diff from current! Will cover old with new.')
            print('\t original:', orig_header)
            print('\t new:', str(header))
    
        #write data
        try:
            tzLocal = win32timezone.TimeZoneInfo('China Standard Time')
        except:
            print('Faill to get china timezone info from win32timezone')
            try:
                tzLocal = win32timezone.TimeZoneInfo('GMT Standard Time')
            except:
                print('Faill to get GMT timezone info from win32timezone, pick 1st available timezone')
                tzLocal = win32timezone.TimeZoneInfo.get_all_time_zones()[0]
                print('timezone:', str(tzLocal.displayName))
                self.save_close()
                
        for i in list(range(2,len(value_d)+2)):
            line = value_d[i-2]
            for j in list(range(1,len(header)+1)):
                v_write = line.get(header[j-1], None)
                if not v_write:
                    ws.Cells(i,j).ClearContents()
                else:
                    if isinstance(v_write, datetime):
                        v_write = datetime(v_write.year, v_write.month, v_write.day,\
                                 v_write.hour, v_write.minute, v_write.second, tzinfo=tzLocal)
                    try:
                        ws.Cells(i,j).Value = v_write
                    except:
                        print('Error: fail to write cell',str(i)+'x'+str(j),'value:', v_write)
                        self.save_file()
                        self.close_file()
                        raise
        wrap_idx = []
        for wrap_h in ['commitMessage', 'comments','inline_comments']:
            if wrap_h in header:
                wrap_idx.append(header.index(wrap_h)+1)
        for colm in wrap_idx:
            ws.Columns(colm).WrapText = False
            
        return 0
        
    def save_file(self):
        print('Saving to', self.abs_fileName)
        if self.newFile:
            try:
                self.excel.DisplayAlerts = False
                self.wb.SaveAs(self.abs_fileName)
            except:
                print('Error in saving new excel! quit')
                self.excel.DisplayAlerts = True
                self.wb.Close()
                raise
        else:
            try:
                print('\tsaving to', self.abs_fileName)
                self.excel.DisplayAlerts = False
                self.wb.Save()
            except:
                print('Error in saving existed excel! quit')
                self.excel.DisplayAlerts = True
                self.wb.Close()
                raise
        self.excel.DisplayAlerts = True
        print('\tsaved.')
        return 0
        
    def close_file(self):
        print('Close excel', self.abs_fileName)
        self.wb.Close()
        print('\tDone. Excel closed.')
        return 0
    
    def open_copy_srcfile(self, srcFile):
        print('Open copy excel file:', srcFile)
        cdir = os.getcwd()
        abs_srcFile = os.path.join(cdir, srcFile)
        if not os.path.exists(abs_srcFile):
            print('Error: cannot find', srcFile, 'in currect dir', cdir)
            return -1
        self.copy_abs_srcFile = abs_srcFile
        self.copy_srcFile = srcFile
        
        if os.name != 'nt':
            return -1
        try:
            self.copy_srcwb = self.excel.Workbooks.Open(abs_srcFile, UpdateLinks=0)
        except:
            print('Error: fail to open', abs_srcFile)
            print('Please make sure file openable and is not opened when launch the script')
            return -1
        self.excel.Visible = True
        print('\tOpen copy source excel file Done')
        return 0
        
    def copy_sheet(self, desSheet, srcSheet):
        '''Copy srcSheet of srcFile to desSheet or current file.
           Shall be called after open_file().
        '''
        print('Start copy sheet', srcSheet, '...')
        if srcSheet not in [sh.Name for sh in self.copy_srcwb.Sheets]:
            print('Error: sheet', srcSheet, 'not find in src file! excel file:',\
                                        self.copy_abs_srcFile)
            return -1
        srcws = self.copy_srcwb.Worksheets(srcSheet)
        
        if desSheet not in [sh.Name for sh in self.wb.Sheets]:
            print('Error: sheet', desSheet, 'not find in dest file! excel file:', self.abs_fileName)
            return -1
        desws = self.wb.Worksheets(desSheet)
        
        print('\tdelete old lines...')
        lines = srcws.Cells(srcws.Cells.Rows.Count,1).End(-4162).Row
        maxCol = srcws.Cells(1, srcws.Cells.Columns.Count).End(-4159).Column
        self.delete_lines(desws, lines)
        
        print('\tcopy cells(1,1) to', '('+str(lines)+','+str(maxCol)+')', '...')
        res = srcws.Range(srcws.Cells(1,1), srcws.Cells(lines, maxCol)).Copy(\
                                                Destination=desws.Cells(1,1))
        if not res:
            print('Error: copy return -1!')
            return -1
        print('\tDone. Sheet', srcSheet, 'copied.')
        return 0
    
    def close_copy_srcfile(self):
        self.copy_srcwb.Close()
        self.copy_abs_srcFile, self.copy_srcFile = None, None
        print('Copy srouce excel closed.')
        return 0
    
    def quit(self):
        print('Quit excel for', self.fileName)
        self.excel.Quit()