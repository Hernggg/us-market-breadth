#!/usr/bin/env python3
"""One-time structural probe of provider's explicitly downloadable JSON files.

Only prints schema keys and date range; NO underlying daily figures or records.
This is a research test, not a scheduled or production reader.
"""
import json
import urllib.request
from collections import Counter

URLS={
    "ad_line":"https://www.thetrading.tools/data/market_breadth/ad_line.json",
    "market_breadth":"https://www.thetrading.tools/data/market_breadth/market_breadth.json",
}

def summarize(obj,depth=0):
    if isinstance(obj,dict):
        ks=list(obj)
        out={"kind":"object","keys":ks[:45],"count":len(ks)}
        for k in ("data","history","series","daily","last_updated","asof","date"):
            if k in obj:
                val=obj[k]
                if isinstance(val,(dict,list)):out[k]=summarize(val,depth+1) if depth<2 else {"kind":type(val).__name__,"len":len(val)}
                else:out[k]=str(val)[:70]
        return out
    if isinstance(obj,list):
        o={"kind":"array","length":len(obj)}
        if obj:
            x=obj[-1]
            if isinstance(x,dict):
                o["last_item_keys"]=list(x)[:55]
                o["last_item_date"]=x.get("date")
                if "date" in x and isinstance(obj[0],dict):o["first_item_date"]=obj[0].get("date")
            elif isinstance(x,list):
                o["last_item_kind"]="array"
                o["last_item_length"]=len(x)
        return o
    return {"kind":type(obj).__name__}

def main():
    for label,url in URLS.items():
        req=urllib.request.Request(url,headers={"User-Agent":"Personal-Breadth-Research/1.0","Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=35) as response:
            raw=response.read(20_000_001)
        if len(raw)>20_000_000:raise ValueError(label+" exceeded size cap")
        obj=json.loads(raw)
        print("VENDOR_JSON_SCHEMA_ONLY",label,json.dumps(summarize(obj),ensure_ascii=False))
        print("HTTP_BYTES",label,len(raw))

if __name__=="__main__":
    main()
