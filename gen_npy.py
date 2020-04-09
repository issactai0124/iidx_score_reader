import os.path
from sys import argv
import numpy as np
from util import extract_url_name, Page, Fumen


# returns row number, row 0 means start of a bar
def px_to_row(pos: float) -> int:
    return int(pos * 192)


def prepare_npy(fumen: Fumen, result_path: str):
    result_npy = np.zeros((px_to_row(fumen.total_px), 9))
    for bpm in sorted(fumen.bpms, key=lambda x: x.px):
        result_npy[px_to_row(bpm.px):, 8] = bpm.bpm  # overkill

    for charge in sorted(fumen.charges, key=lambda x: (x.px, x.lane)):
        px_cur = px_to_row(charge.px)
        duration_px = px_to_row(charge.duration)
        result_npy[px_cur - duration_px:px_cur, charge.lane] = 1

    for note in sorted(fumen.notes, key=lambda x: (x.px, x.lane)):
        result_npy[px_to_row(note.px), note.lane] = 2

    np.save(result_path, result_npy)
    print('written npy file at', result_path)


if __name__ == '__main__':
    if len(argv) < 2:
        print('input fumen url!')
    else:
        # url = r"http://textage.cc/score/17/raison.html?1AB00" # for example
        url = argv[1]
        result_path = 'score_sp_npy/' + extract_url_name(url) + '.npy'

        # see if result is already generated
        if os.path.isfile(result_path):
            print(result_path + ' already exists!')
        else:
            page = Page(url)
            page.load()
            fumen = Fumen()
            fumen.process_from_web(page)
            prepare_npy(fumen, result_path)
