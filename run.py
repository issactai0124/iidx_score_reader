from pyquery import PyQuery as pq
from sys import argv, stderr, exit
import os.path
import numpy as np
from scipy import sparse
import pickle
import yaml

LEFT_TO_COLUMN_INDEX = {
    '0px': 0,
    '37px': 1,
    '51px': 2,
    '65px': 3,
    '79px': 4,
    '93px': 5,
    '107px': 6,
    '121px': 7
}

LEFT_CN_TO_COLUMN_INDEX = {
    '2px': 0,
    '38px': 1,
    '52px': 2,
    '66px': 3,
    '80px': 4,
    '94px': 5,
    '108px': 6,
    '122px': 7
}

HISPEED = '12'
WIDTH_NOTES = 5
WIDTH_CN = 1
WIDTH_SOFTLAN = 7
FULL_BAR_HEIGHT = float(HISPEED) * 16
CHART_NAME = ''
RESULT_PATH = ''

def get_row(top, bar_height, offset):
    return int(round((bar_height-offset-int(top.replace('px', '')))
                     *192/FULL_BAR_HEIGHT, 0))

def get_row_notes(top, bar_height):
    return get_row(top, bar_height, WIDTH_NOTES)

def get_row_cn(top, bar_height):
    return get_row(top, bar_height, WIDTH_CN)

def get_row_softlan(top, bar_height):
    return get_row(top, bar_height, WIDTH_SOFTLAN)

def extract_url_name(s):
    start = s.rfind('/') + 1
    end = s.find('.', start)
    return s[start:end]

def extract_top(s):
    start = s.find('top:') + 4
    end = s.find(';', start)
    return s[start:end]

def get_number_of_row_cn(height):
    return int(round((int(height.replace('px', '')))*192/FULL_BAR_HEIGHT, 0))

def read_page():
    # load page pickle, if not load from chrome web driver
    try:
        with open('pickle/' + CHART_NAME + '.pkl', 'rb') as f:
            print('found page pickle! load from pickle peko!')
            page = pickle.load(f)
            bpm = pickle.load(f)
            title = pickle.load(f)
    except:
        print('pickle of page not found. load from chrome driver...')
        from selenium import webdriver
        
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
            
        chrome_path = config["chrome_webdriver_path"] #chromedriver.exe
        try:
            web = webdriver.Chrome(chrome_path)
        except:
            print('chrome driver error!')
            exit(0)
        url_with_option = url + '=' + HISPEED
        web.get(url_with_option)
        page = web.page_source
        # make the pickle file just smaller...
        try:
            title = web.execute_script('return title')
            bpm = web.execute_script('return bpm')
        except:
            print('fail to execute script. possibly invalid url!')
            exit(0)
        page = page[page.find("<table cellpadding"):]
        if(type(bpm) == tuple):
            bpm = bpm[0].split("～")[0]
        elif(type(bpm) == str and "～" in bpm):
            bpm = bpm.split("～")[0]
        if(config["save_page_npy"]):
            with open('pickle/' + CHART_NAME + '_page.pkl', 'wb') as f:
                pickle.dump(page, f)
                pickle.dump(bpm, f)
                pickle.dump(title, f)
    return page, bpm, title
        
def read_bpm(fumen_array, bpm_dict, bar_row_dict):
    if (bpm_dict):
        bar_aggrow_dict = {}
        aggrow = 0
        for item in sorted(bar_row_dict.items(), reverse=False):
            bar_aggrow_dict.update({item[0]: aggrow})
            aggrow = aggrow + item[1]
        
        cur_row = 0
        prev_row = 0
    
        for item in sorted(bpm_dict.items(), reverse=False):
            cur_row = bar_aggrow_dict[item[0][0]] + item[0][1]
            fumen_array[cur_row:, 8] = item[1] # overkill

def process_doc(doc, bpm):
    # read information per bar
    tables = doc.find('table[cellpadding="0"]')
    if(not tables):
        print('fail to read from the url!')
        exit(0)

    trial = 0
    fumen = {1: np.zeros((192, 9))}
    total_row = 192
    bar_row_dict = {1: 192}
    bpm_dict = {(1, 0): bpm}
    
    for table in tables:
        bar = pq(table)
        try:
            bar_num = int(bar.find('th[width="32"]').text())
        except:
            bar_num = 999 # some charts show no bar number for the last bar
        bar_height = int(bar.attr['height']) # read length of bar
        row = int(bar_height/FULL_BAR_HEIGHT*192)
        bar_row_dict.update({bar_num: row})
        fumen_bar = np.zeros((row,9))
        fumen.update({bar_num: fumen_bar})
        
        # read bpm change
        for softlan in bar.find('span'): 
            pq_softlan = pq(softlan)
            bpm_dict.update({(bar_num, get_row_softlan(
                extract_top(pq_softlan.attr['style']), bar_height))
                : pq_softlan.text()})
            
        total_row = row if bar_num == 1 else total_row + row
        
        # 1 note per image
        for note in bar.find('img'):
            style = pq(note).attr['style']
            if style is None or 'height:' in style: # charge notes
                try:
                    top, left, height = map(lambda s: s.split(':')[1].strip(),
                                            style.split(';')[:3])
                except:
                    #print('Skip 1... {}'.format(pq(note)), file=stderr)
                    continue
                row_cn = get_row_cn(top, bar_height)
                if(row_cn <= row):
                    fumen_bar[row_cn-get_number_of_row_cn(height):row_cn,
                              LEFT_CN_TO_COLUMN_INDEX[left]] = 1
                else: # should not happen...?
                    fumen_bar[row-get_number_of_row_cn(height):row,
                              LEFT_CN_TO_COLUMN_INDEX[left]] = 1
                    print('length of CN too long! bar = {}, tag = {}'.
                          format(bar_num, pq(note)), file=stderr)
                fumen.update({bar_num: fumen_bar})
                continue
            try: # normal notes
                top, left = map(lambda s: s.split(':')[1].strip(),
                                style.split(';')[:2])
            except Exception as e:
                #print('Skip 2... {}'.format(pq(note)), file=stderr)
                continue
            try:
                row_notes = get_row_notes(top, bar_height)
                if(row_notes < row): # goes to current bar
                    fumen_bar[row_notes, LEFT_TO_COLUMN_INDEX[left]] = 2
                    fumen.update({bar_num: fumen_bar})
                else:
                    if(bar_num+1 in fumen): # goes to next bar
                        fumen_bar_next = fumen[bar_num+1]
                        fumen_bar_next[row_notes-row,
                                       LEFT_TO_COLUMN_INDEX[left]] = 2
                        fumen.update({bar_num+1: fumen_bar_next})
                    else:
                        print('fail to read note position! bar = {}, tag = {}'
                              .format(bar_num, pq(note)), file=stderr)
            except Exception as e:
                print('unexpected error! bar = {}, tag = {}'
                      .format(bar_num, pq(note)), file=stderr)
        trial += 1
    # for debug
    #    if trial > 5: 
    #        break
    
    # prepare final array
    fumen_array = np.zeros((0,9))
    for key in sorted(fumen.keys(), reverse=False):
        fumen_array = np.concatenate([fumen_array, fumen[key]])

    with open('pickle/' + CHART_NAME + '_npy.pkl', 'wb') as f:
        pickle.dump(sparse.csr_matrix(fumen_array), f)
        pickle.dump(bpm_dict, f)
        pickle.dump(bar_row_dict, f)
        
    return fumen_array, bpm_dict, bar_row_dict
    
def run():
    # load npy pickle, if not load from page
    try:
        with open('pickle/' + CHART_NAME + '_npy.pkl', 'rb') as f:
            print('found npy pickle! load from pickle peko!')
            s_fumen_array = pickle.load(f)
            fumen_array = np.array(s_fumen_array.todense())
            bpm_dict = pickle.load(f)
            bar_row_dict = pickle.load(f)
    except:
        page, bpm, title = read_page()
        doc = pq(page)
        fumen_array, bpm_dict, bar_row_dict = process_doc(doc, bpm)
        
    read_bpm(fumen_array, bpm_dict, bar_row_dict)
    np.save(RESULT_PATH, fumen_array)
    print('written npy file at', RESULT_PATH)
        

if __name__ == '__main__':
    if(len(argv) < 2):
        print("input fumen url!")
        exit(0)
    
    #url = r"http://textage.cc/score/17/raison.html?1AB00" # for example    
    url = argv[1]
    CHART_NAME = extract_url_name(url)
    RESULT_PATH = 'score_sp_npy/' + CHART_NAME + '.npy'
    
    # see if result is already generated
    if(os.path.isfile(RESULT_PATH)):
        print(RESULT_PATH + ' already exists!')
        exit(0)
        
    run()