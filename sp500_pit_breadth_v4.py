#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""@us-market V2.0 S&P 500 PIT prototype based on a public third-party dataset.

NOT an official S&P DJ Indices statistic. Requires:
  python -m pip install duckdb
Downloads three public release assets and reuses local cached copies.

Inputs: Johnbrick123/sp500-data Release `data`:
  prices.parquet, membership_intervals.parquet, recycled_tickers.csv
Outputs: daily, windows, missing members and quality audit.

Intentionally keeps raw component-coverage checks and DOES NOT silently fill missing
member prices, or treat dividends-adjusted close highs as official 52-week highs.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, json, math, sys, time, traceback
from collections import defaultdict, deque
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = 'https://github.com/Johnbrick123/sp500-data/releases/download/data'
META_API = 'https://api.github.com/repos/Johnbrick123/sp500-data/releases/tags/data'
ASSETS = {'membership_intervals.parquet': 1000, 'recycled_tickers.csv': 10, 'prices.parquet': 5_000_000}
WINDOWS = [1, 5, 10, 20, 60]
METHOD = 'THIRD_PARTY_PIT_MEMBERSHIP_ADJUSTED_CLOSE_NOT_OFFICIAL'


def download_if_needed(folder: Path, name: str, min_size: int, force=False):
    path = folder/name
    if not force and path.is_file() and path.stat().st_size > min_size:
        print('Cached:', name, format(path.stat().st_size,','), 'bytes', flush=True)
        return path
    url = f'{BASE}/{name}'
    temp = folder/(name+'.part')
    if temp.exists(): temp.unlink()
    print('Downloading:', url, '\n(large file: about 235 MB for prices)', flush=True)
    try:
        req = Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; us-market-breadth/1.0)'})
        with urlopen(req, timeout=150) as remote, open(temp,'wb') as dest:
            total=0; next_report=25_000_000
            while True:
                part=remote.read(1024*1024)
                if not part: break
                dest.write(part); total+=len(part)
                if total>=next_report:
                    print(f'  {total/1e6:.0f} MB received...',flush=True)
                    next_report+=25_000_000
        if temp.stat().st_size <= min_size:
            raise RuntimeError(f'{name} too small: {temp.stat().st_size} bytes')
        temp.replace(path)
    except Exception:
        if temp.exists(): temp.unlink()
        raise
    return path



def remote_assets():
    """Read *official GitHub release metadata* to check for updated assets.

    The third-party dataset itself is not an official index product.
    On failure return None and never claim a fresh source.
    """
    try:
        req=Request(META_API,headers={'User-Agent':'us-market-v2-breadth-audit/4.0',
                                     'Accept':'application/vnd.github+json'})
        with urlopen(req,timeout=20) as resp:
            release=json.loads(resp.read())
        return {a['name']:a for a in release.get('assets',[])}
    except Exception as exc:
        print('WARNING: Could not inspect remote update metadata:',str(exc),flush=True)
        return None


def cache_refresh_plan(folder:Path, force:bool=False):
    """Decide whether we need fresh assets; compare remote asset metadata to local files.

    On first V4 run, existing locally downloaded V3 assets are recognized by their
    download mtime and byte size. Future runs check GitHub asset updated_at/size.
    """
    info=remote_assets()
    plan={}; remarks=[]
    for name,minimum in ASSETS.items():
        path=folder/name
        if force or not path.exists() or path.stat().st_size<=minimum:
            plan[name]=True
            remarks.append(f'{name}: '+('FORCE_REFRESH' if force else 'MISSING_OR_INVALID'))
            continue
        if info and name in info:
            asset=info[name]
            updated=asset.get('updated_at') or asset.get('created_at')
            # If remote metadata date is newer than the local downloaded file,
            # refresh. Compare actual sizes for extra safety.
            try:
                remote_time=dt.datetime.fromisoformat(updated.replace('Z','+00:00')).timestamp() if updated else 0
            except ValueError:
                remote_time=0
            remote_size=asset.get('size')
            changed=bool((remote_time > path.stat().st_mtime+60) or
                         (isinstance(remote_size,int) and remote_size>0 and remote_size!=path.stat().st_size))
            plan[name]=changed
            remarks.append(f'{name}: '+('REMOTE_CHANGED_REFRESH' if changed else 'REMOTE_UNCHANGED_REUSE'))
        else:
            plan[name]=False
            remarks.append(f'{name}: REMOTE_NOT_VERIFIED_REUSE')
    return plan, remarks, info is not None


def price_last_available(path:Path):
    import duckdb
    con=duckdb.connect()
    try:
        result=con.execute('SELECT max(CAST(date AS DATE)) FROM read_parquet(?) WHERE ticker=?',
                           [str(path),'SPY']).fetchone()[0]
        return result
    finally: con.close()


def parse_recycled(path:Path):
    banned=set()
    with open(path,encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        for row in rd:
            name=(row.get('ticker') or '').strip().upper()
            if name: banned.add(name)
    return banned


def valid(x):
    return x is not None and math.isfinite(float(x)) and float(x)>0


def summarize(daily):
    out=[]
    for n in WINDOWS:
        if len(daily)<n: continue
        part=daily[-n:]
        d={'window':'当日' if n==1 else f'{n}日平均','sessions':n,'asof':part[-1]['date'],'method':METHOD}
        for x in ('advances','declines','unchanged','new_highs','new_lows'):
            d['avg_'+x]=round(sum(row[x] for row in part)/n,3)
        dec=sum(row['declines'] for row in part)
        d['ad_ratio']=round(sum(row['advances'] for row in part)/dec,5) if dec else None
        for metric in ('ma50_pct','ma200_pct'):
            vals=[row[metric] for row in part]
            d['avg_'+metric]=round(sum(vals)/n,4) if all(v is not None for v in vals) else None
        d['avg_net_new_highs']=round(d['avg_new_highs']-d['avg_new_lows'],3)
        for field in ('price_coverage','ad_coverage','ma50_coverage','ma200_coverage','hilo_coverage'):
            d['min_'+field]=round(min(row[field] for row in part),4)
        d['all_sessions_high_coverage']=all(row['price_coverage']>=0.98 and row['ma200_coverage']>=0.95 and row['hilo_coverage']>=0.95 for row in part)
        d['status']='HIGH_COVERAGE_PROVISIONAL' if d['all_sessions_high_coverage'] else 'INCOMPLETE_COVERAGE'
        out.append(d)
    return out


def write_csv(path, values):
    if not values: return
    cols=list(values[0].keys())
    with open(path,'w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader();writer.writerows(values)


def calculate(price_file:Path, intervals_file:Path, recycled_file:Path, output:Path, asof:dt.date):
    import duckdb
    con=duckdb.connect()
    # All parquet assets have date, ticker, adj_close as described by dataset owner.
    cols={r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(price_file)]).fetchall()}
    required={'date','ticker','adj_close'}
    if not required.issubset(cols): raise ValueError('Source price schema changed: missing '+str(required-cols))
    source_expr='source' if 'source' in cols else "'' AS source"
    d=con.execute('SELECT DISTINCT CAST(date AS DATE) AS d FROM read_parquet(?) WHERE ticker=? AND date<=? ORDER BY d DESC LIMIT 311',
                  [str(price_file),'SPY',asof]).fetchall()
    days=sorted(x[0] for x in d)
    if len(days)<311: raise ValueError('Need 311 trading sessions to calculate 60D 52-week breadth, found '+str(len(days)))
    last=days[-1]
    start=days[0]
    metrics_dates=days[-60:]
    print('Trading sessions loaded:',len(days),'from',start,'to',last, flush=True)
    if last != asof:
        print('WARNING target data not available:',asof, '(last price day',last,')',flush=True)

    day_index={d:i for i,d in enumerate(days)}
    # Read all prices (even non-members, for price-history warm-up) through the period.
    sql=f'SELECT CAST(date AS DATE), UPPER(CAST(ticker AS VARCHAR)), adj_close, {source_expr} FROM read_parquet(?) WHERE date>=? AND date<=? ORDER BY ticker, date'
    price_rows=con.execute(sql,[str(price_file),start,last]).fetchall()
    print('Price rows in calculation window:',len(price_rows),flush=True)
    if not price_rows: raise ValueError('No price rows in window')

    # Compute per-security technical measurements before joining PIT membership.
    # Require unbroken market-session windows, not merely a count of candles.
    # The 50/200D averages include current session, while the 52W close highs
    # use previous 251 observed market sessions as the comparison period.
    # Store (global-session-position, adjusted close), not just prices.
    # A missing daily candle must NOT be silently skipped when counting the
    # prior 49 / 199 / 251 sessions. Otherwise SMA and 52W coverage can be
    # overstated after halts, missing quotes or incomplete histories.
    history=defaultdict(lambda:deque(maxlen=251))
    prev={}
    features=defaultdict(dict)
    for day,ticker,raw,source in price_rows:
        if not ticker or not valid(raw): continue
        pos=day_index.get(day)
        if pos is None: continue
        adj=float(raw)
        hist=history[ticker]
        if day in metrics_dates:
            data={'close':adj,'source':source or '', 'ad':None,'ma50':None,'ma200':None,'nh':None,'nl':None}
            if ticker in prev:
                prior_day,prior_close=prev[ticker]
                if pos and prior_day==days[pos-1]:
                    tol=max(1e-8,1e-10*abs(prior_close))
                    data['ad']=1 if adj>prior_close+tol else (-1 if adj<prior_close-tol else 0)
            # Check the entire lookback window has exactly one candle per
            # expected global exchange session; no price-fill or shortcuts.
            for period in (50,200):
                k=period-1
                if len(hist)>=k:
                    window=list(hist)[-k:]
                    if window[0][0]==pos-k and window[-1][0]==pos-1:
                        data[f'ma{period}']=adj>(sum(v for _,v in window)+adj)/period
            if len(hist)>=251:
                window=list(hist)[-251:]
                if window[0][0]==pos-251 and window[-1][0]==pos-1:
                    values=[v for _,v in window]
                    data['nh']=adj>max(values)
                    data['nl']=adj<min(values)
            features[day][ticker]=data
        hist.append((pos,adj))
        prev[ticker]=(day,adj)
    del price_rows

    # Read PIT membership spans; an interval is [start, end), as in dataset README.
    int_cols={r[0] for r in con.execute('DESCRIBE SELECT * FROM read_parquet(?)',[str(intervals_file)]).fetchall()}
    if not {'ticker','start','end'}.issubset(int_cols):
        raise ValueError('Source membership schema changed: '+str(int_cols))
    intervals=con.execute('SELECT UPPER(CAST(ticker AS VARCHAR)), CAST(start AS DATE), CAST("end" AS DATE) FROM read_parquet(?) WHERE start<=? AND ("end" IS NULL OR "end">?)',
                          [str(intervals_file),last,metrics_dates[0]]).fetchall()
    banned=parse_recycled(recycled_file)
    members_by_day={day:set() for day in metrics_dates}
    for ticker,begin,end in intervals:
        if not ticker: continue
        for day in metrics_dates:
            if day>=begin and (end is None or day<end):members_by_day[day].add(ticker)
    missing=[]; daily=[]
    for day in metrics_dates:
        m=members_by_day[day]; f=features.get(day,{})
        row={'date':day.isoformat(),'expected_members':len(m), 'priced_members':0,
             'advances':0,'declines':0,'unchanged':0,
             'ad_eligible':0,'ma50_eligible':0,'ma50_above':0,'ma200_eligible':0,'ma200_above':0,
             'hilo_eligible':0,'new_highs':0,'new_lows':0,'carried_or_suspended':0,'recycled_excluded':0}
        for ticker in sorted(m):
            if ticker in banned:
                row['recycled_excluded']+=1
                missing.append({'date':day.isoformat(),'ticker':ticker,'reason':'RECYCLED_TICKER_EXCLUDED'})
                continue
            p=f.get(ticker)
            if not p:
                missing.append({'date':day.isoformat(),'ticker':ticker,'reason':'NO_VALID_PRICE'})
                continue
            row['priced_members']+=1
            source=str(p['source']).lower()
            if 'carried' in source or 'halt' in source:
                row['carried_or_suspended']+=1
                missing.append({'date':day.isoformat(),'ticker':ticker,'reason':'CARRIED_OR_HALTED_PRICE'})
                continue
            if p['ad'] is not None:
                row['ad_eligible']+=1
                k='advances' if p['ad']==1 else ('declines' if p['ad']==-1 else 'unchanged')
                row[k]+=1
            for period in (50,200):
                if p[f'ma{period}'] is not None:
                    row[f'ma{period}_eligible']+=1
                    if p[f'ma{period}']:row[f'ma{period}_above']+=1
            if p['nh'] is not None:
                row['hilo_eligible']+=1
                row['new_highs']+=int(p['nh'])
                row['new_lows']+=int(p['nl'])
        denom=max(1,len(m))
        row['price_coverage']=row['priced_members']/denom
        row['ad_coverage']=row['ad_eligible']/denom
        row['ma50_coverage']=row['ma50_eligible']/denom
        row['ma200_coverage']=row['ma200_eligible']/denom
        row['hilo_coverage']=row['hilo_eligible']/denom
        row['ma50_pct']=100*row['ma50_above']/row['ma50_eligible'] if row['ma50_eligible'] else None
        row['ma200_pct']=100*row['ma200_above']/row['ma200_eligible'] if row['ma200_eligible'] else None
        if row['advances']+row['declines']+row['unchanged']!=row['ad_eligible']:
            raise AssertionError('A/D reconciliation failed: '+row['date'])
        daily.append(row)
    con.close()
    output.mkdir(parents=True,exist_ok=True)
    write_csv(output/'sp500_pit_daily.csv',daily)
    write_csv(output/'sp500_pit_windows.csv',summarize(daily))
    if missing:
        write_csv(output/'sp500_pit_missing.csv',missing)
    else:
        with open(output/'sp500_pit_missing.csv','w',encoding='utf-8-sig',newline='') as empty_file:
            empty_file.write('date,ticker,reason\n')
    windows=summarize(daily)
    latest=daily[-1]
    report=[
        '@us-market V2.0 | THIRD-PARTY Point-in-Time S&P500 Breadth Prototype',
        'Dataset: https://github.com/Johnbrick123/sp500-data',
        'Release: https://github.com/Johnbrick123/sp500-data/releases/tag/data',
        'IMPORTANT: Not official S&P Dow Jones Indices breadth.',
        f'Requested asof: {asof.isoformat()} | price latest session: {last.isoformat()}',
        f'Price source size: {price_file.stat().st_size/1e6:.1f} MB',
        f'Observed PIT members latest: {latest["expected_members"]}',
        f'Latest priced / expected: {latest["priced_members"]}/{latest["expected_members"]}',
        f'Latest A/D price-adjusted: {latest["advances"]}/{latest["declines"]}, eligible {latest["ad_eligible"]}',
        f'Latest coverage: price {latest["price_coverage"]:.2%}; A/D {latest["ad_coverage"]:.2%}; MA50 {latest["ma50_coverage"]:.2%}; MA200 {latest["ma200_coverage"]:.2%}; 52W {latest["hilo_coverage"]:.2%}',
        'MA methodology: dividend+split-adjusted close; 50/200 include current day, uninterrupted market sessions.',
        '52W methodology: adjusted CLOSE-only extremes against prior 251 consecutive SPY market sessions.',
        'IMPORTANT: 52W is NOT the same as intraday highs/lows or split-only price highs.',
        'A/D uses adjusted close, so dividend ex-days can differ from unadjusted exchange A/D.',
        'Carried/halting rows are not treated as genuine active price moves.',
        'Recycled symbols are excluded and counted as missing, not silently dropped.',
        f'Coverage issues in the last 60 sessions: {len(missing)} member-day rows',
        'Status is only HIGH_COVERAGE_PROVISIONAL; separate-source and constituent verification still required.',
        'Statuses: '+', '.join(x['window']+': '+x['status'] for x in windows),
    ]
    (output/'sp500_pit_quality_report.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    for line in report:print(line,flush=True)
    return output


def main():
    parser=argparse.ArgumentParser(description='@us-market V2.0 S&P500 PIT reconstruction with automatic source-freshness checks')
    parser.add_argument('--asof',default='2026-11-19',help='US completed market session YYYY-MM-DD (currently 2026-11-19)')
    parser.add_argument('--outdir',default='sp500_pit_output')
    parser.add_argument('--cache',default='sp500_pit_cache')
    parser.add_argument('--force-refresh',action='store_true',help='Download all source assets again even if GitHub metadata has not changed (large ~236MB)')
    args=parser.parse_args()
    output=Path(args.outdir);output.mkdir(parents=True,exist_ok=True)
    cache=Path(args.cache);cache.mkdir(parents=True,exist_ok=True)
    status=[]
    try:
        date=dt.date.fromisoformat(args.asof)
        plan,notes,remote_ok=cache_refresh_plan(cache,force=args.force_refresh)
        status.extend(['Requested session: '+str(date),'Remote GitHub release metadata available: '+str(remote_ok)])
        status+=notes
        files={}
        for name,minimum in ASSETS.items():
            try:
                files[name]=download_if_needed(cache,name,minimum,force=plan[name])
            except Exception as exc:
                path=cache/name
                # Safely keep previously downloaded data; do not silently call it current.
                if path.is_file() and path.stat().st_size>minimum:
                    files[name]=path
                    status.append(f'WARNING {name}: refresh FAILED, used old cached file ({exc})')
                else:
                    raise
        source_last=price_last_available(files['prices.parquet'])
        status.append('Actual source last SPY price date: '+str(source_last))
        fresh=bool(source_last and source_last>=date)
        status.append('FRESHNESS: '+('DATE_MATCHED' if fresh else 'STALE_BEFORE_REQUESTED_DATE'))
        if not fresh:
            status.append('IMPORTANT: Outputs are for '+str(source_last)+' only; DO NOT label as '+str(date))
            print('WARNING! Requested',date,'but latest actual price date is',source_last,flush=True)
        calculate(files['prices.parquet'],files['membership_intervals.parquet'],
                  files['recycled_tickers.csv'],output,date)
        status.append('PIT output calculations: COMPLETED')
        (output/'sp500_pit_update_status.txt').write_text('\n'.join(status)+'\n',encoding='utf-8')
        print('\n'.join(status),flush=True)
        print('OUTPUT FILES:',output.resolve(),flush=True)
        print('Next run checks for changed GitHub release assets automatically; existing cache is preserved.',flush=True)
        return 0 if fresh else 2
    except Exception as exc:
        msg='FAILED: '+str(exc)+'\n'+traceback.format_exc()
        print(msg,flush=True)
        (output/'sp500_pit_error.txt').write_text(msg,encoding='utf-8')
        if status:
            (output/'sp500_pit_update_status.txt').write_text('\n'.join(status)+'\n',encoding='utf-8')
        return 1

if __name__=='__main__':sys.exit(main())
