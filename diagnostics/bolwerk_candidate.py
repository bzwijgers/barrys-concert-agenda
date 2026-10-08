"""Verify third-party structured event records for Bolwerk, where original site is blocked."""
from html import unescape
from urllib.request import Request,urlopen
import json,re
URLS={
"Bolwerk":"https://www.podiuminfo.nl/podium/44/concerten/Het-Bolwerk/Sneek/",
"Amare":"https://www.podiuminfo.nl/podium/4984/concerten/Amare/Den-Haag/",
}
for name,url in URLS.items():
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"}),timeout=15) as resp: page=resp.read().decode("utf-8","replace")
  records=[]
  for blob in re.findall(r'''<script[^>]*type=["']application/ld\+json["'][^>]*>(.*?)</script>''',page,re.I|re.S):
   try:item=json.loads(unescape(blob))
   except ValueError:continue
   if isinstance(item,dict) and item.get("@type") in ("MusicEvent","Event"):
    records.append({key:item.get(key) for key in ("name","startDate","url","location","eventStatus")})
  print(name,"count:",len(records),"records:",repr(records[:9]),flush=True)
 except Exception as error:print(name,"ERROR",repr(error),flush=True)
