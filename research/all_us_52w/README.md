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


## 2026-11-25 重大进展：已实际取得并重算完整真实60日历史

之前只看到 thetrading.tools 的图表及最新数值，后来在该网站公开研究附录中，**发现其主动公布、可供下载的完整原始汇总 JSON**：

- 来源：https://www.thetrading.tools/data/market_breadth/nh_nl.json
- 网站自己在 https://www.thetrading.tools/insights/bullish-percent-index-oversold-near-record-high 公开链接到此数据集。
- 每日实际字段：`date`, `new_highs`, `new_lows`, `total_issues`, `nh_nl_diff`；同时包含 `nasdaq_new_highs`, `nasdaq_new_lows`, `nasdaq_issues` 等字段。
- 已用 GitHub 云端程序 **在真实数据上成功读取、计算并交叉验证最近60个交易日**：
  https://github.com/Hernggg/us-market-breadth/actions/runs/45544850467
- 2026-11-24 全美股：当日 63/280，5日 36.20/468.80，10日 49.90/402.20，20日 96.65/321.75，60日 80.083/257.817（新高家数/新低家数）。样本当天4360只。
- 2026-11-24 Nasdaq上市合资格普通股：当日38/187，5日22.2/304.8，10日28.8/266.8，20日53.45/221.75，60日41.833/168.25；当天样本2469只。
- 真实数据源的最后交易日、每个交易日无重复、每行家数合法、净新高算术验证，并与现有 S&P 500 PIT 60日交易日历逐项比对全部通过。
- 脚本：`research/all_us_52w/compute_public_history_once.py`，只读取一次公开发布的数据文件，在一次性 GitHub Actions 的日志中输出小量**统计均值**；不储存或重新发布原始厂商全部数据。未更动用户 TradingView 三合一脚本或 S&P 500 生产数据。

### 一定不要误称已经完成的事项

- 这条数据属于研究网站筛选的普通股，**并不是交易所官方“全美股”总量**。网站说明用当下现存股票构造历史，存在幸存者偏差，股票数量和其他来源不等同。
- Nasdaq子集是该网站的**Nasdaq上市合资格普通股**，不等于TradingView ADVQ/DECQ/MAHQ/MALQ的全交易所口径，也不等于严格Nasdaq Composite成分股。
- **每日自动触发、持久存储及默认@us-market直接读取仍未接通**。不能把研究分支里一次性 GitHub Actions 运行当成生产每日自动化。
- 网站 [Terms of Service](https://www.thetrading.tools/terms) §7 指其计算输出为受版权保护的内容，个人非商业可注明出处分享／引用，系统性重新发布需要事先书面允许；§6 限制会干扰服务器的高频自动采集。**因此在确认长期使用/再发布许可前，不能把整份原始JSON或每天的批量历史数据镜像到公开GitHub，也不应直接开启无授权的系统性公开转载。**

后续：先解决合法的每日调用与有限衍生结果发布范围，再把 4.3 A（全美股）和 Nasdaq 实用参考口径的真实五周期指标纳入正式 V2.1 执行链路；永远沿用实际日期和研究样本定义。
