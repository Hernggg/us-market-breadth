#!/usr/bin/env python3
"""Write audit-friendly compact JSON/Markdown from existing V4 outputs."""
from __future__ import annotations
import csv
import datetime as dt
import json
from pathlib import Path

def read_csv(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def to_number(s):
    if s is None or s=='':return None
    try:return int(s) if s.lstrip('-').isdigit() else float(s)
    except (ValueError,TypeError):return s

def publish(out:Path):
    status_file=out/'sp500_pit_update_status.txt'
    win_file=out/'sp500_pit_windows.csv'
    daily_file=out/'sp500_pit_daily.csv'
    qa_file=out/'sp500_pit_quality_report.txt'
    for path in (status_file,win_file,daily_file,qa_file):
        if not path.exists():raise ValueError(f'Missing required output: {path}')
    status_text=status_file.read_text(encoding='utf-8')
    quality=qa_file.read_text(encoding='utf-8')
    windows=read_csv(win_file)
    daily=read_csv(daily_file)
    if len(windows)!=5 or len(daily)!=60:raise ValueError('Incomplete windows/daily sessions; refusing to publish')
    dates=[row['date'] for row in daily]
    if len(set(dates))!=60 or dates!=sorted(dates):raise ValueError('Daily sessions not unique/increasing')
    if any(row.get('asof')!=dates[-1] for row in windows):raise ValueError('Window dates inconsistent')
    for row in windows:
        if row.get('status') != 'HIGH_COVERAGE_PROVISIONAL':
            raise ValueError('Data not high-coverage: refusing to replace public results')
    freshness='STALE_BEFORE_REQUESTED_DATE' if 'FRESHNESS: STALE_BEFORE_REQUESTED_DATE' in status_text else 'DATE_MATCHED' if 'FRESHNESS: DATE_MATCHED' in status_text else 'UNVERIFIED'
    report={'market':'S&P500', 'method':'third-party point-in-time member reconstruction, adjusted closes',
            'official_data':False, 'verified_status':'HIGH_COVERAGE_PROVISIONAL_NOT_OFFICIAL',
            'source':'https://github.com/Johnbrick123/sp500-data',
            'asof_actual':dates[-1], 'freshness':freshness, 'last_60_sessions':60,
            'note':'52W is adjusted-close extremes vs prior 251 sessions, NOT intraday 52-week highs/lows.',
            'windows':[{k:to_number(v) for k,v in row.items()} for row in windows],
            'last_day':{k:to_number(v) for k,v in daily[-1].items()},
            'source_audit':quality.splitlines()}
    (out/'latest.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    md=['# S&P 500 market breadth — @us-market V2.0',
        f'Actual data date: **{dates[-1]}** | Freshness: **{freshness}**',
        '', '**HIGH-COVERAGE PROVISIONAL. NOT official S&P Dow Jones Indices statistics.**',
        '', '| Metric | Today | 5 sessions | 10 sessions | 20 sessions | 60 sessions |',
        '|---|---:|---:|---:|---:|---:|']
    fields=[('Avg advances','avg_advances'),('Avg declines','avg_declines'),('A/D','ad_ratio'),('Above 50 DMA %','avg_ma50_pct'),('Above 200 DMA %','avg_ma200_pct'),('New 52W highs (adjusted close)','avg_new_highs'),('New 52W lows (adjusted close)','avg_new_lows')]
    for label,k in fields:
        md.append('| '+label+' | '+' | '.join(str(row.get(k,'N/A')) for row in windows)+' |')
    md+=['','**Method:** historical third-party membership; price = split+dividend adjusted close. The 52W metric uses close, not intraday high/low.',
        '**Caution:** publication date and *actual market data date* may differ. If stale, do not interpret as the latest U.S. trading session.',
        '', 'Source: https://github.com/Johnbrick123/sp500-data',
        'Read `sp500_pit_quality_report.txt` and `sp500_pit_update_status.txt` for audit details.']
    (out/'latest.md').write_text('\n'.join(md)+'\n',encoding='utf-8')
    return report

if __name__=='__main__':publish(Path('public'))
