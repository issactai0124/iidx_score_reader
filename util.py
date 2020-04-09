import yaml
from pyquery import PyQuery as pq
from typing import List, Dict
from constants import HISPEED, FULL_BAR_HEIGHT, \
    LEFT_TO_COLUMN_INDEX, LEFT_CN_TO_COLUMN_INDEX


def extract_url_name(s: str) -> str:
    start = s.rfind('/') + 1
    return s[start:].replace('.html', '').replace('?', '_')


def extract_top(s: str) -> str:
    start = s.find('top:') + 4
    end = s.find(';', start)
    return s[start:end]


class Page:
    def __init__(self, url: str):
        self.adr = url + '=' + HISPEED
        self.title = ""
        self.page_source = ""
        self.bpm = 0
        self.hcn = False

    def load(self):
        from selenium import webdriver, common

        try:
            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)
        except IOError:
            raise FileNotFoundError('config.yaml not found!')
        chrome_path = config['chrome_web_driver_path']  # chrome_driver.exe

        try:
            web = webdriver.Chrome(chrome_path)
        except common.exceptions.WebDriverException:
            raise RuntimeError('chrome driver error!')
        web.get(self.adr)
        try:
            self.page_source = web.page_source
            self.title = web.execute_script('return title')
            self.hcn = web.execute_script('return hcn') == 1
            bpm = web.execute_script('return bpm')
        except common.exceptions.JavascriptException:
            raise RuntimeError('fail to execute script. invalid url?')
        finally:
            web.quit()
        if type(bpm) == tuple:
            bpm = bpm[0].split('～')[0]
        if type(bpm) == str:
            if '～' in bpm:
                bpm = bpm.split('～')[0]
        self.bpm = float(bpm)
        print('finish reading page source of {} at {}.'.format(self.title, self.adr))


class WebObj:
    def __init__(self, w: int, bar_num: int, top: int, bar_height: int):
        self.bar_num = bar_num
        self.bar_pos = (bar_height - w - top) / FULL_BAR_HEIGHT
        self.px = 0


class Note(WebObj):
    def __init__(self, bar_num: int, top: str, bar_height: int, lane: int):
        super().__init__(5, bar_num, int(top.replace('px', '')), bar_height)
        self.lane = lane


class Charge(WebObj):
    def __init__(self, bar_num: int, top: str, bar_height: int, lane: int, duration: int, hcn: bool):
        super().__init__(1, bar_num, int(top.replace('px', '')), bar_height)
        self.lane = lane
        self.duration = duration / FULL_BAR_HEIGHT
        self.hcn = hcn

    def name(self) -> str:
        return "HCN" if self.hcn else "CN"


class Bpm(WebObj):
    def __init__(self, bar_num: int, top: str, bar_height: int, bpm: float):
        super().__init__(7, bar_num, int(top.replace('px', '')), bar_height)
        self.bpm = bpm

    @classmethod
    def from_bpm(cls, bpm: float) -> 'Bpm':
        bpm = cls(1, "0px", 0, bpm)
        bpm.bar_pos = 0
        return bpm


class Fumen:
    def __init__(self):
        self.bpms: List[Bpm] = []
        self.notes: List[Note] = []
        self.charges: List[Charge] = []
        self.bar_to_px: Dict[int, float] = {}
        self.total_px: int = 0

    def process_from_web(self, page: Page):
        tables = pq(page.page_source).find('table[cellpadding="0"]')
        if not tables:
            raise RuntimeError('fail to read from the url!')

        bar_heights: Dict[int, float] = {1: 1}
        for table in tables:
            bar = pq(table)
            try:
                bar_num = int(bar.find('th[width="32"]').text())
            except ValueError:
                bar_num = 999  # some charts show no bar number for the last bar

            bar_height = int(bar.attr['height'])  # read length of bar
            bar_heights.update({bar_num: bar_height / FULL_BAR_HEIGHT})

            # read bpm change
            for bpm in bar.find('span'):
                pq_bpm = pq(bpm)
                top = extract_top(pq_bpm.attr['style'])
                if self.bpms:
                    self.bpms.append(Bpm(bar_num, top, bar_height, float(pq_bpm.text())))
                else:
                    self.bpms = [Bpm.from_bpm(float(pq_bpm.text()))]

            # 1 note per image
            for note in bar.find('img'):
                style = pq(note).attr['style']
                if style is None or 'height:' in style:  # charge notes
                    try:
                        top, left, height = map(lambda s: s.split(':')[1].strip(),
                                                style.split(';')[:3])
                    except IndexError as e:
                        continue
                    except ValueError as e:
                        continue
                    self.charges.append(Charge(bar_num, top, bar_height,
                                               LEFT_CN_TO_COLUMN_INDEX[left],
                                               int(height.replace('px', '')), page.hcn))
                else:  # normal notes
                    try:
                        top, left = map(lambda s: s.split(':')[1].strip(),
                                        style.split(';')[:2])
                    except IndexError as e:
                        continue
                    except ValueError as e:
                        continue
                    self.notes.append(Note(bar_num, top, bar_height,
                                           LEFT_TO_COLUMN_INDEX[left]))

        for bar_num, bar_height in sorted(bar_heights.items()):
            self.bar_to_px.update({bar_num: self.total_px})
            self.total_px += bar_height

        def cal_px(bar: int, pos: float) -> float:
            return self.bar_to_px[bar] + pos

        if not self.bpms:
            self.bpms = [Bpm.from_bpm(page.bpm)]
        for bpm in sorted(self.bpms, key=lambda x: (x.bar_num, x.bar_pos)):
            bpm.px = cal_px(bpm.bar_num, bpm.bar_pos)

        for note in sorted(self.notes, key=lambda x: (x.bar_num, x.bar_pos, x.lane)):
            note.px = cal_px(note.bar_num, note.bar_pos)

        for charge in sorted(self.charges, key=lambda x: (x.bar_num, x.bar_pos, x.lane)):
            charge.px = cal_px(charge.bar_num, charge.bar_pos)
