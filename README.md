# iidx_score_reader
Read iidx scores from [textage.cc](http://textage.cc/score/index.html) and generate files of different formats.

## Notes
- Only supports SP (Single Player) charts.
- Requires ChromeDriver

### gen_npy.py
generate npy file with format suggested by [asari-saminun](https://asari-saminun.hatenablog.com/entry/2020/03/30/212935 "asari-saminun").

#### Usage
- python (or python3) gen_npy.py http://textage.cc/score/17/raison.html?1AB00

### gen_df.py
generate pkl file containing following data:
- notes df, columns = index, time, notes, and type (CN on/off)
- bpms df, columns = index, time and bpm

#### Usage
- python (or python3) gen_df.py http://textage.cc/score/17/raison.html?1AB00
