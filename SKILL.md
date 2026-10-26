---
name: a-stock-data
description: 需要写代码实际获取A股及相关市场真实数据时使用——行情/K线/逐笔、研报(东财+新浪+同花顺+iwencai)、信号(热点/北向/龙虎榜/解禁/板块资金流)、资金面(两融/大宗/股东户数/分红/ETF份额)、新闻(财联社/东财/华尔街见闻/新闻联播)、财务三表/F10/估值历史/ST名单、公告(巨潮)、打板(涨停池/连板/炸板率/异动)、ETF期权、舆情互动(互动易/上证e互动/热榜)、筹码分布、复权因子、宏观与利率(社融/PMI/中债收益率/LPR/宏观日历)、指数成分与交易日历、期货与大宗商品、事件驱动(业绩预告/调研/增减持/回购/质押/新股)、可转债。仅在需要调用数据接口取数时使用：A股概念解释、投资观点讨论、策略问答等无需取数的话题不加载本skill。
---
# A股全栈数据工具包

十五层 · 87 个端点（82 主 + 5 备胎）· 34 个数据源。**本文件是唯一必读**：作用域 + 端点索引 + 跑法 + 铁律。
每层的可运行代码与实测记录在 `references/` 下，按下表定位后只读那一份。

**只负责取数，不带回测引擎**：回测交给自己的框架或聚宽（`to_joinquant()` 转聚宽代码，历史估值/行业/成分按对应端点取，注意前视偏差）。

## When to Activate

- 需要**真实取数**时激活：行情/估值、研报、资金流与龙虎榜、打板情绪、期权、互动问答与热榜、新闻公告、
  财报与估值历史、指数与交易日历、期货大宗、事件驱动、可转债、宏观与利率——具体能力见下方端点索引。
- 关键词：估值、一致预期、市盈率、PEG、研报、产业链、K线、盘口、公告、新闻、强势股、题材、热点、北向资金、
  概念板块、资金流向、主力、龙虎榜、席位、解禁、行业轮动、融资融券、两融、大宗交易、股东户数、分红、指数、ETF、
  涨停、打板、连板、炸板、跌停、封板、晋级率、ETF期权、希腊字母、隐含波动率、互动易、上证e互动、热榜、人气榜、
  期货、商品期权、持仓排名、A50、黄金、上海金、业绩预告、机构调研、增减持、回购、股权质押、新股申购、打新、
  可转债、转股溢价率、国债收益率、收益率曲线、回购利率、FR007、LPR、宏观日历、ETF份额、ST、新闻联播、聚宽、回测
- 不需要激活：A股概念解释、投资观点讨论、策略问答等不取数的话题。

## 端点路由速查（按层分组，签名即用法）

按下表定位到函数，再去对应文件取该端点的代码。返回 `pandas.DataFrame`；「源」标在每组标题上——能用腾讯/交易所官方就别用东财（见铁律 3）。

### 前置 · 本地 · `references/01-common.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 前置 | `norm_ticker(code)` | 任意写法→纯6位（`SH600519`/`600519.SH`/`600519.XSHG` 皆可；解析失败抛错不返空） |
| 前置 | `to_joinquant(code)` | 转聚宽代码 `600519.XSHG` / `000001.XSHE`（北交所不转换） |

### §1 行情 · 腾讯 / 通达信官网 / 百度 / 新浪 / 通达信 · `references/layers/01-quote.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 1.1 | `tencent_quote(codes)` | 实时价/PE/PB/市值/换手/涨跌停/指数/ETF（带 `is_stale` 僵尸报价标志） |
| 1.2 | `tencent_kline(code, period, adjust, start, end, count)` | 日/周/月前后复权 + 1~60 分钟 K 线（沪深，不含北交所） |
| 1.3 | `tdx_daily_package(date)` | 某交易日沪深北全部证券日线（含成交额） |
| 1.4 | `tencent_ticks(code)` | 最近一个交易日的分笔成交（价/手/元/主动买卖；沪深个股+ETF，不含北交所） |
| 1.5 | `baidu_kline_with_ma(code)` | 日K线带 MA5/10/20 |
| 1.6 | `sina_adjust_factor(code, kind)` / `apply_adjust(bars, factors)` | 复权因子 qfq/hfq + 套用到不复权K线 |
| 1.7 | `tdx_client()` → `.bars()` / `.quotes()` / `.transaction()` | K线(多周期,不复权) / 五档盘口 / 逐笔成交（⚠️ 2026-09 起返回空，#52，留档） |

### §2 研报 · 东财 / 同花顺 / iwencai / 新浪 · `references/layers/02-research.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 2.1 | `eastmoney_reports(code)` / `download_pdf(rec)` | 个股研报+评级+三年EPS / 研报PDF |
| 2.1 | `eastmoney_industry_reports(industry_code)` | 行业研报 |
| 2.2 | `ths_eps_forecast(code)` | 机构一致预期 EPS |
| 2.3 | `iwencai_search(query)` / `iwencai_query(query)` | NL 语义搜研报/选股（需 Key） |
| 2.4 | `sina_research_reports(code=None, page=1)` | 研报列表：标题/类型/机构/研究员（无评级） |

### §3 信号 · 同花顺 / 东财 · `references/layers/03-signal.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 3.1 | `ths_hot_reason()` | 当日强势股+题材归因 |
| 3.2 | `hsgt_realtime()` | 北向分钟流向（hgt 可用 / sgt 仅参考） |
| 3.3 | `eastmoney_concept_blocks(code)` | 个股所属板块/概念归属 |
| 3.4 | `eastmoney_fund_flow_minute(code)` | 个股资金流（分钟级） |
| 3.5 | `dragon_tiger_board(code, date)` | 个股龙虎榜+买卖席位 TOP5 |
| 3.6 | `lockup_expiry(code, date)` | 解禁历史+未来90天待解禁 |
| 3.7 | `industry_comparison()` | 行业板块涨跌排名 |
| 3.8 | `board_fund_flow(board_type, period)` | 板块资金流向（行业/概念/地域 × 今日/5日/10日，主力+四档） |
| 3.9 | `daily_dragon_tiger(date)` | 全市场龙虎榜+净买额排名 |

### §4 资金面与筹码 · 东财 / 上交所·深交所 / 本地计算 · `references/layers/04-fund-flow.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 4.1 | `margin_trading(code)` | 融资融券明细 |
| 4.2 | `block_trade(code)` | 大宗交易+营业部 |
| 4.3 | `holder_num_change(code)` | 股东户数变化 |
| 4.4 | `dividend_history(code)` | 分红送转历史 |
| 4.5 | `stock_fund_flow_120d(code)` | 个股资金流（120日，日级） |
| 4.6 | `chip_distribution(df)` | 筹码分布（获利比例/平均成本/90-70成本区间/筹码峰） |
| 4.7 | `etf_shares(date, exchange)` | ETF 份额（万份）：上交所历史日期 / 深交所当前快照 |

### §5 新闻 · 东财 / 财联社 / 华尔街见闻 / 央视网 · `references/layers/05-news.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 5.1 | `eastmoney_stock_news(code)` | 个股新闻 |
| 5.2 | `cls_telegraph()` | 财联社电报（7×24，本地签名零key） |
| 5.3 | `eastmoney_global_news()` | 全球资讯（7×24） |
| 5.4 | `wallstreetcn_lives(channel, limit, cursor)` | 7×24 快讯（按频道，可翻页） |
| 5.5 | `cctv_news(date, with_content=True)` | 新闻联播条目 + 文字稿（政策信号研究用） |

### §6 基础数据 · 通达信 / 东财 / 新浪 / baostock / 申万 · `references/layers/06-fundamentals.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 6.1 | `tdx_client(check='finance').finance(symbol)` | 季报快照 37 字段 |
| 6.2 | `tdx_client(check='finance').F10(symbol, name)` | F10 文本（2026-09 起服务端只剩「最新提示」一类） |
| 6.3 | `eastmoney_stock_info(code)` | 行业/股本/市值/上市日期 |
| 6.4 | `sina_financial_report(code, type)` | 财报三表 |
| 6.5 | `baostock_valuation_history(code, s, e)` | 估值历史 PE/PB/PS/PCF + 换手率 + 停牌 + ST（**不支持北交所**） |
| 6.6 | `baostock_stock_basic(code)` | 上市日 / **退市日** / 状态 |
| 6.7 | `sw_industry_history()` / `sw_industry_as_of(df, code, d)` | 申万行业**变迁史**（消除前视偏差，仅代码无中文名） |
| 6.8 | `st_stock_list()` | 沪深京 ST / *ST 当日名单 |

### §7 公告 · 巨潮 / 通达信 · `references/layers/07-announcement.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 7.1 | `cninfo_announcements(code)` | 公告检索+PDF 下载 |
| 7.2 | `tdx_client(check='finance').F10(symbol, name='最新提示')` | 最新公告摘要 |

### §8 打板 · 东财 / 同花顺 · `references/layers/08-limit-up.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 8.1 | `em_zt_pool` / `em_zb_pool` / `em_dt_pool` / `em_yzt_pool` | 涨停/炸板/跌停/昨涨停四池 |
| 8.2 | `ths_limit_up_pool(date)` | 涨停原因题材+封板成功率+板型 |
| 8.3 | `limit_up_sentiment(date)` | 炸板率/连板高度/连板梯队 |
| 8.4 | `em_stock_monitor()` | 重点监控池（风险警示名单+生效时间窗） |
| 8.5 | `em_price_anomaly()` / `em_price_anomaly_count()` | 日内异动明细 / 按标的聚合异动统计（严重异常波动） |

### §9 ETF 期权 · 新浪 · `references/layers/09-options.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 9.1 | `sina_option_codes` / `sina_option_tquote` / `sina_option_greeks` | ETF期权合约清单 / T型报价 / 希腊字母+IV |

### §10 舆情互动 · 巨潮 / 同花顺 / 东财 / 上证e互动 · `references/layers/10-sentiment.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 10.1 | `cninfo_irm(code)` | 互动易问答（提问+公司回复，深市） |
| 10.2 | `ths_hot_list()` / `em_hot_rank()` / `em_hot_concept(code)` | 热榜/人气榜/概念命中 |
| 10.3 | `sse_e_interaction(code=None, kind='answered')` | 上证e互动问答（沪市） |

### §11 宏观与利率 · 人民银行 / 国家统计局 / 中债 / 中国货币网 / 东财 / 华尔街见闻 · `references/layers/11-macro.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 11.1 | `pboc_social_financing(year)` | 社会融资规模增量（月度12列） |
| 11.2 | `nbs_pmi()` | 制造业/非制造业/综合 PMI + 大中小型企业 |
| 11.3 | `chinabond_yield_curve(start, end, curve)` | 国债 / 银行 AAA / 中短票 AAA 收益率曲线 3月~30年 |
| 11.4 | `repo_fixing_rates(kind)` | 回购定盘利率 FR / FDR 001·007·014 |
| 11.5 | `lpr_history()` | LPR 1 年 / 5 年全历史 |
| 11.6 | `macro_calendar(start, end, country, min_importance)` | 全球宏观日历（公布值/预期/前值） |

### §12 指数与交易日历 · 中证 / 国证 / 深交所 · `references/layers/12-index-calendar.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 12.1 | `index_constituents(index_code, provider)` | 最近公布的沪深北指数成分；csi/cni 显式选源 |
| 12.2 | `index_weights(index_code, provider)` | 最近公布的指数权重（百分数），保留真实日期 |
| 12.3 | `index_valuation(index_code)` | 两种口径 PE、股息率；不含 PB |
| 12.4 | `trading_calendar(year, month)` | 官方整月交易日历 |

### §13 期货与大宗商品 · 五家期货交易所 / 新浪 / 上金所 · `references/layers/13-futures.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 13.1 | `futures_daily(date, exchange)` | 期货日行情（SHFE/INE/CZCE/CFFEX/GFEX） |
| 13.2 | `options_daily(date, exchange)` | 商品期权 / 股指期权日行情 + Delta / IV（中金所不公布这两项） |
| 13.3 | `futures_position_rank(date, exchange, symbol)` | 会员成交 / 持买 / 持卖前 20 名 |
| 13.4 | `futures_realtime(symbols)` | 实时期货（含大商所品种） |
| 13.5 | `a50_futures()` | 富时中国 A50 期指 |
| 13.6 | `sge_spot(instrument)` | 上海金交所现货日线（黄金/白银/铂金） |
| 13.7 | `futures_kline(symbol, start, end)` | 期货日 K：单个合约 / 主力连续的逐日序列（含大商所） |

### §14 事件驱动 · 东财 · `references/layers/14-events.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 14.1 | `earnings_forecast(code, report_date, limit)` | 业绩预告 |
| 14.2 | `institution_survey(code, start, end, detail, limit)` | 机构调研（汇总 / 逐机构） |
| 14.3 | `holder_trades(code, direction, start, end, limit)` | 股东增减持 |
| 14.4 | `share_buyback(code, progress, limit)` | 股票回购方案与进度 |
| 14.5 | `equity_pledge(code, date, limit)` | 股权质押比例（中国结算周度，仅沪深） |
| 14.6 | `ipo_calendar(limit)` | 新股申购日历 |

### §15 可转债 · 东财 · `references/layers/15-convertible.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 15.1 | `convertible_bonds(include_delisted=False)` | 可转债条款 + 转股价值 / 溢价率 |

### 估值公式 · 本地计算 · `references/20-valuation.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 估值公式 | `forward_pe` / `pe_digestion` / `calc_peg` / `full_valuation(code)` | 前向PE / PE消化时间 / PEG / 单票估值全景 |

### 备胎与降级 · 交易所官方 / 新浪 / 东财 · `references/02-data-sources.md`

| § | 函数 | 拿什么 |
|---|---|---|
| 官方备胎扩展 | `margin_trading_backup(date, exchange, code=None)` | 单所两融明细（先执行 §12 helper） |
| 官方备胎扩展 | `bse_quote_backup(date, code=None)` | 北交所全板/单票当前快照（先执行 §12 helper） |
| 备用源速查 | `dragon_tiger_backup` / `fund_flow_backup` / `announcements_backup` | 龙虎榜/资金流/公告官方备胎（主源被封时降级） |

## 怎么跑起来

- 代码就在各层 md 里，整段复制执行；端点间共用的 helper 也在文档内，先执行依赖的代码块再调端点。
- 共用 helper 在 `references/01-common.md`，**按目录跳读，不要通读**：绝大多数端点只依赖
  「市场前缀规则 + Ticker 格式归一化」（`get_prefix` / `norm_ticker`）、「东财数据中心统一查询」（`em_get`）、
- 依赖安装、安装目录约定见 `references/01-common.md` 的「安装说明」。

### 其余文档（按需，不必读）

| 文件 | 内容 | 什么时候读 |
|---|---|---|
| `references/01-common.md` | 前置与共用 helper 代码块 | 写端点代码前，跳读所需小节 |
| `references/02-data-sources.md` | 源优先级、东财风控阈值与封禁案例、官方两融/北交所备胎、备用源速查与降级 | 选源、批量任务、主源被封 |
| `references/20-valuation.md` | 前向 PE / PE 消化年数 / PEG / `full_valuation` | 估值计算 |
| `references/21-workflows.md` | 完整调研流程（多端点串联模板） | 单票/板块深度调研 |

## 核心铁律（不读长文档也必须遵守）

1. **Ticker 一定先归一化**：用 `norm_ticker(code)` 变纯 6 位。接口只认纯 6 位或「前缀/后缀二选一」
   （`SH600519` / `600519.SH` 可以，`SH600519.SH` 自相矛盾不行），解析失败**抛 `ValueError`，绝不返回空串**。
   `000001` 是歧义码（`sh000001`=上证指数 / `sz000001`=平安银行）——丢掉市场标识＝静默选错标的。
   北交所在市代码是 `43x/83x/87x/920x`，老码（如 `832982`）会拿到僵尸数据，前缀规则见 `01-common.md` 的「市场前缀规则」。
2. **所有东财请求走 `em_get()`**，绝不裸 `requests.get`：串行 + 间隔 ≥1s + 随机抖动 + 复用 `EM_SESSION`。
   东财风控阈值与真实封 IP 案例见 `02-data-sources.md`；批量场景把 `EM_MIN_INTERVAL` 调大到 1.5~2s，且**不并发**。
3. **能用腾讯 / 交易所官方，就不用东财**。行情、K 线、市值、估值快照走腾讯；全市场日线走通达信盘后包；
   东财只用于它独有的数据（龙虎榜、资金流、解禁、事件驱动、可转债等）。
4. **「确实没有」与「接口坏了」必须分开**：新端点返回带 `source` / `source_url` / `fetched_at` 的 DataFrame，
   空结果返回语义一致的空结构；解析不出就抛错，不许悄悄给空表或 `None` 列。
5. **日期按北京时间**：`cn_today()`（A 股口径），不要用本机 `date.today()`；海外时区会错开一天。
6. **Python 3.9 兼容**：不写 `X | None`、不用 3.10+ 语法；文档里的代码块都是可直接 exec 的原文。
7. **只取真实数据，不编造**：拿不到就说拿不到，并指向 `02-data-sources.md` 的备用源。
