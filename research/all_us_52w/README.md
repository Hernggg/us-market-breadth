# 全美股 52 周新高／新低：真实来源与当前交付状态

**更新日期：2026-11-25 MYT，研究分支，不是每日自动数据源。**

## 最重要的新发现

Barchart 文档明确提供两个独立的**全美市场52周家数**指标：

- **`$MAHX`** — 52-Week Highs Overall
- **`$MALX`** — 52-Week Lows Overall

原厂资料：
- Barchart [所有市场新高新低汇总](https://www.barchart.com/stocks/highs-lows/summary) 明确列出 Overall / NYSE / NASDAQ 等独立系列，52 Week 高 $MAHX、低 $MALX。
- Barchart [历史新高](https://www.barchart.com/stocks/quotes/%24MAHX/price-history) 与 [历史新低](https://www.barchart.com/stocks/quotes/%24MALX/price-history)。
- TradingView [INDEX:MAHX](https://www.tradingview.com/symbols/INDEX-MAHX/) 与 [INDEX:MALX](https://www.tradingview.com/symbols/INDEX-MALX/) 均有独立指标页面。**尚未在用户真实免费 TradingView 帐户验证 request.security 是否能返回完整60日**。
- EODData [INDEX/MAHX](https://eoddata.com/stockquote/INDEX/MAHX.htm) 与 [INDEX/MALX](https://eoddata.com/stockquote/INDEX/MALX.htm) 也有历史网页，但公开HTML历史表只显示少量行，部分页面明显滞后；EODData API 免费账号访问受上次注册问题影响，未验证。
- Barchart [0.01 sentinel 的正式说明](https://help.barchart.com/support/solutions/articles/248023-what-is-the-new-highs-new-lows-summary-page-and-where-can-i-find-it-): 图表中0.01表示**0只**。我们的适配器仅对已确认同类 Barchart 指标应用此映射，不把所有证券报价的0.01当成0。

## 必须注意的统计范围

**Barchart Overall U.S.** 不等于已经独立核实的「全美股合资格普通股」范围。我们还需要确认 Overall 包含多少 ETF、优先股、REIT、外国证券等，以及市场家数变化/指数日期定义。

另有对普通股筛选更明确的 thetrading.tools [New Highs/Lows](https://www.thetrading.tools/new-highs-new-lows)，2026年11月24日公布全美股 **63 NH / 280 NL / 4,360 有效股票**，有2010年以来的趋势图，但首页的最近10日可直接读取表格仅是**净高低差 NH-NL**，不分别提供60个交易日每天的 NH 和 NL，因此不能逆推出原模板要求的两个五周期平均值。历史回看还采用当前幸存成员，需注明。

不能将 Barchart Overall 的60日平均跟 thetrading.tools 的当日 63/280 混算。

## 这次已经真正完成的工程

- `research/all_us_52w/import_authorized_ma_hx_lx.py`
  - 接收**有使用权的私人真实历史 CSV**，新高 $MAHX、新低 $MALX 各一份；按美股真实交易日历严格核对；分别计算 1/5/10/20/60 日平均及净新高。
  - 用完整真实60交易日逐日记录计算，遇缺日不造假、不把缺失当零、不把20日当60日。
  - 识别 Barchart 已证实的 0.01=0 家数编码；拒绝其他小数家数。
  - 出口权限需要人工确认，生成的数值只写到**非公开私人路径**；不会把受限行情或厂商派生序列存进 public GitHub。
  - 输出明确标记 `strict_all_us_common_stock_scope_verified=false`、`licensed_unattended_automation_verified=false`，不能冒充全美股正式指标已完成。
- `tests/test_all_us_52w_vendor_import.py`: 8 项 Python 单元测试全部通过，包括缺日、错误日期、不可混算、授权、0.01 零值和五窗口计算。
- GitHub Actions [测试结果](https://github.com/Hernggg/us-market-breadth/actions/runs/45543911931) **success**。注意该测试使用人工样本验证计算程序，不代表已经取得真实60日行情。
- **没有修改**用户已经成功运行的 TradingView 三合一指标，也没有修改主仓库 S&P 500 更新或 `public/latest.json`。

## 使用方法（未来取得权利清晰的 CSV 后）

```bash
python research/all_us_52w/import_authorized_ma_hx_lx.py \
  --ma-hx-csv /private/MAHX.csv \
  --ma-lx-csv /private/MALX.csv \
  --calendar-csv public/sp500_pit_daily.csv \
  --asof 2026-11-24 \
  --private-use-rights-confirmed \
  --out /tmp/all_us_52w_private_report.json
```

要求真实文件含 **Date,Close** 两列，每个来源每天一行，至少60个交易日；这个CSV是本地标准化输入结构，**尚未使用实际 Barchart 原生 CSV 进行端到端测试**。若日期晚于 SP500 PIT public CSV 最后一天，必须更换更及时的真实交易日历，而不是强行改时间。

## 当前阻塞项目（不能假装成功）

1. **取得60个交易日独立的 MAHX/MALX 每日数值**：Barchart网站对自动访问做机器人检查；会员历史下载权利未核实，不应使用爬虫绕过。TradingView 免费版能看这些指标网页，但不能自动通过公开GitHub抓取其图表。
2. **原始统计总体**：必须核实 Overall 实际证券资格与全美合资格普通股定义的差异；如未证实只能标记「全美市场第三方参考」。
3. **长期每日自动更新**：需要获准的正式数据接口或供应商导出权限，不能把网站截图当成自动API。
4. **用户期望不手动操作**：暂不要求用户改 TradingView 脚本或下载 CSV；研究仍继续找可机器读取的授权方式。

下一阶段技术验收只认：**真实60行 NH + 真实60行 NL + 完成期交易日 + 统计范围 + 使用权 + 计算窗口**。任何一项不满足，不把它并进 V2.1 4.3 正式主表。
