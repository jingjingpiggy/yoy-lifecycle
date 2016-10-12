#!python3
import time
from downPatch import *
from handle import *
from winExcel import *
from pyxlExcel import *

project_list_android = project_kernel + project_andr_hal
project_list_test = project_test[:]
project_list_iotgUsr = project_linux_hal[:]

def create_excel_writer(excel_name, which):
    if which == 'win32':
        excel = excel_writer_win32(excel_name)
    elif which == 'pyxl':
        excel = excel_writer_pyxl(excel_name)
    else:
        print('!!!Error!!! unknown excel process tool:', which)
        raise
    return excel

def main_lifecycle(start_d, end_d, excel_name, whichexcel):
    print('------Start: lifecycle------')
    project_list_android = project_kernel[:] + project_andr_hal[:]
    project_list_test = project_test[:]
    project_list_iotgUsr = project_linux_hal[:]
    sheet_names = ['AndrKHPatch', 'testProjPatch', 'IoTGPatch', 'metrics']

    parser = Parser()
    raw_excel_name = 'yoy-lifecycle_raw.xlsx' #raw file to save result
    excel = create_excel_writer(raw_excel_name, whichexcel)

    print('---Android projects:---')
    handler = HandlerLifecycle_Andr(parser, start_d, end_d,
                                    project_list_android)
    result = handler.handle()
    excel.open_file()
    excel.write_excel(handler.required_headers, result, sheet_names[0])
    excel.save_file()

    print('---Test projects:---')
    handler = HandlerLifecycle_Andr(parser, start_d, end_d,
                                project_list_test)
    result = handler.handle()
    excel.write_excel(handler.required_headers, result, sheet_names[1])
    excel.save_file()

    print('---Linux projects:---')
    handler = HandlerLifecycle_Iotg(parser, start_d, end_d,
                                project_list_iotgUsr)
    result = handler.handle()
    excel.write_excel(handler.required_headers, result, sheet_names[2])
    excel.save_file()

    print('---Gerrit Metrics:---')
    metrics = GerritMetrics()
    metrics.download(start_d, end_d)
    excel.write_excel(metrics.header, metrics.data, sheet_names[3])
    excel.save_file()
    time.sleep(1)
    excel.close_file()
    time.sleep(2)
    excel.quit()
    
    #copy result to target excel by win32 API
    print('Start copy to target excel...')
    target_excel = excel_writer_win32(excel_name)
    if target_excel.open_file() < 0:
        raise
    if target_excel.open_copy_srcfile(raw_excel_name) < 0:
        raise
    for sheet in sheet_names:
        if target_excel.copy_sheet(sheet, sheet) < 0:
            print('Error: copy sheet', sheet, 'fail!')
            raise
    target_excel.save_file()
    time.sleep(1)
    target_excel.close_file()
    time.sleep(1)
    target_excel.close_copy_srcfile()
    time.sleep(1)
    target_excel.quit()
    
    print('------Finished: lifecycle------')
    return 0


def main_comments(start_d, end_d, excel_name, whichexcel):
    print('------Start: comments------')
    parser = Parser()
    raw_excel_name = 'yoy-comments_raw' #raw file to save result
    filenames_suf = {'kernel': '_kernel.xlsx', 'linux': '_linux.xlsx',\
                        'AndrCom': '_AndrHal_common.xlsx', 'AndrSpec': '_AndrHal_specific.xlsx'}
    sheetname = 'patch'

    print('---Kernel:---')
    project_list = project_kernel[:]
    handler = HandlerComments(parser, start_d, end_d, project_list)
    result = handler.handle()
    print('\tpatch num:', len(result), '(expected it <= downloaded #)')
    
    raw_filename = raw_excel_name + filenames_suf['kernel']
    excel = excel_writer_pyxl(raw_filename)
    excel.open_file()
    excel.write_excel(handler.required_headers, result, sheetname)
    excel.save_file()

    print('---Linux UserSpace:---')
    project_list = project_linux_hal[:]
    handler = HandlerComments(parser, start_d, end_d, project_list)
    result = handler.handle()
    print('patch num:', len(result), '(expected <= download #)')
    
    raw_filename = raw_excel_name + filenames_suf['linux']
    excel = excel_writer_pyxl(raw_filename)
    excel.open_file()
    excel.write_excel(handler.required_headers, result, sheetname)
    excel.save_file()

    print('---Android UserSpace Common:---')
    project_list = project_andr_hal[:]
    handler = HandlerComments_AndrHal(parser, start_d, end_d, project_list)
    result_comm, result_spec = handler.handle()
    print('patch num:', len(result_comm), '(expected <= download #)')
    
    raw_filename = raw_excel_name + filenames_suf['AndrCom']
    excel = excel_writer_pyxl(raw_filename)
    excel.open_file()
    excel.write_excel(handler.required_headers, result_comm, sheetname)
    excel.save_file()
    
    print('---Android UserSpace Specific:---')
    print('patch num:', len(result_spec), '(expected <= download #)') 
    raw_filename = raw_excel_name + filenames_suf['AndrSpec']
    excel = excel_writer_pyxl(raw_filename)
    excel.open_file()
    excel.write_excel(handler.required_headers, result_spec, sheetname)
    excel.save_file()
    
    print('---Done saving into raw files', raw_excel_name+'*.xlsx' )
    
    #copy result to target excel by win32 API
    print('---Start copy to target excel files ---')
    for suf in filenames_suf.values():
        filename = excel_name[:-5] + suf
        raw_filename = raw_excel_name + suf
        target_excel = excel_writer_win32(filename)
        if target_excel.open_file() < 0:
            raise
        if target_excel.open_copy_srcfile(raw_filename) < 0:
            raise
        if target_excel.copy_sheet(sheetname, sheetname) < 0:
            print('Error: copy file', filename, 'fail!')
            raise
        target_excel.save_file()
        time.sleep(1)
        target_excel.close_file()
        time.sleep(1)
        target_excel.close_copy_srcfile()
        time.sleep(1)
        target_excel.quit()
    print('---copy files done---')
    
    print('------Finished: comments------')


def printUsage():
    print("\nUsage: " + sys.argv[0] + " -t <lifecycle/comment> -s <yyyy-mm-dd> -e <yyyy-mm-dd> -n <excel name>")
    print("          -t: type, lifecycle or comment")
    print("          -s: start date, like 2016-6-1")
    print("          -e: end date(not included), like 2016-7-1 means patches"\
            + "merged before 16/7/1")
    print("Options: ")
    print("         ")

def main():
    datestart, dateend, excelname, function_tocall = None, None, None, None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "t:s:e:n:")
    except:
        printUsage()
    print("opts: ", str(opts))
    print("args: ", str(args))
    for opt, v in opts:
        if opt == '-t':
            if v == 'lifecycle':
                function_tocall = main_lifecycle
            elif v == 'comment':
                function_tocall = main_comments
            else:
                print("\nInvalid Param:", opt, v)
                printUsage()
                return -1
        if (opt == '-s' or opt == '-e'):
            s = v.split('-')
            if len(s) != 3 or len(s[0]) != 4 or len(s[1]) > 2 or len(s[2]) > 2:
                print("\nInvalid Param:", opt, v)
                printUsage()
                return -1
            try:
                year = int(s[0])
                month = int(s[1])
                date = int(s[2])
            except:
                print("\nInvalid Param:", opt, v)
                printUsage()
                return -1
            if year <2000 or month <1 or month >12 or date <1 or date >31:
                print("\nInvalid Param:", opt, v)
                printUsage()
                return -1
            if opt == '-s':
                datestart = datetime(year, month, date);
            if opt == '-e':
                dateend = datetime(year, month, date);
        if opt == '-n':
            if '.xlsx' in v:
                excelname = v
            elif '.xls' in v:
                excelname = v[:v.index('.xls')]
                print('\nNot support this excel format, change excel name from',
                        v, 'to', excelname, '!')
            else:
                excelname = v + '.xlsx'
    if not (datestart and dateend and function_tocall):
        print("\nNo Enough Param:", str(sys.argv[1:]))
        printUsage()
        return -1
    if datestart >= dateend:
        print("\nStart date >= End date! start:", datestart.strftime('%Y-%m-%d'),
                'end:', dateend.strftime('%Y-%m-%d'))
        printUsage()
        return -1
    if not excelname:
        excelname = 'Patch_lifecycle_' + datetime.today().strftime('%y%m%d') + '.xlsx'
        print('\n No excel name, will use default name.')

    #main_lifecycle(datestart, dateend, excelname, 'pyxl')
    #main_comments(datestart, dateend, excelname, 'pyxl')
    function_tocall(datestart, dateend, excelname, 'pyxl')

if __name__ == '__main__':
   main()
