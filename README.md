# iidx_score_reader
Read iidx score from textage.cc and generate npy file with format suggested by [asari-saminun](https://asari-saminun.hatenablog.com/entry/2020/03/30/212935 "asari-saminun").

## Usage
python gen_npy.py http://textage.cc/score/17/raison.html?1AB00
or
python3 gen_npy.py http://textage.cc/score/17/raison.html?1AB00

### Notes
- Only supports SP (Single Player) charts.
- Requires ChromeDriver