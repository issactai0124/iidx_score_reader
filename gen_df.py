import os.path
import pickle
from sys import argv
import numpy as np
import pandas as pd
from typing import List, Union
from util import extract_url_name, Page, Fumen, Bpm, Note


# returns time from start of a bar in ms
def px_to_time(pos: float) -> float:
    return pos * 240000


def prepare_time_df(fumen: Fumen, result_path: str):
    notes_time = []
    bpm_time = []
    t = 0
    px_prev = 0
    bpm_cur = 1  # dummy

    notes_bpms: List[Union[Bpm, Note]] = fumen.notes
    notes_bpms.extend(fumen.bpms)

    for x in sorted(notes_bpms,
                    key=lambda y: (y.px, 0) if isinstance(y, Bpm) else (y.px, 1, y.lane)):
        px_cur = x.px
        t += px_to_time(px_cur - px_prev) / bpm_cur
        if isinstance(x, Bpm):
            bpm_cur = x.bpm
            bpm_time.append((px_cur, t, bpm_cur))
        else:
            notes_time.append((px_cur, t, x.lane, ""))
        px_prev = px_cur

    bpm_df = pd.DataFrame(bpm_time, columns=['index', 'time', 'bpm'])
    notes_df = pd.DataFrame(notes_time, columns=['index', 'time', 'notes', 'type'])

    for x in sorted(fumen.charges, key=lambda y: (y.px, y.lane)):
        px_cur = x.px
        notes_df.loc[np.isclose(notes_df['index'], px_cur) &
                     np.isclose(notes_df['notes'], x.lane),
                     'type'] = x.name() + " off"
        notes_df.loc[np.isclose(notes_df['index'], px_cur - x.duration) &
                     np.isclose(notes_df['notes'], x.lane),
                     'type'] = x.name() + " on"

    with open(result_path, 'wb') as f:
        pickle.dump(notes_df, f)
        pickle.dump(bpm_df, f)
    print('written time_df file at', result_path)


if __name__ == '__main__':
    if len(argv) < 2:
        print('input fumen url!')
    else:
        # url = r"http://textage.cc/score/17/raison.html?1AB00" # for example
        url = argv[1]
        result_path = 'time_df/' + extract_url_name(url) + '.npy'

        # see if result is already generated
        if os.path.isfile(result_path):
            print(result_path + ' already exists!')
        else:
            page = Page(url)
            page.load()
            fumen = Fumen()
            fumen.process_from_web(page)
            prepare_time_df(fumen, result_path)
