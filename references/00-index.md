# 端点总表（87 入口）与层目录

> 隶属 `a-stock-data` skill · 入口 [`SKILL.md`](../SKILL.md) · 端点总表 [`00-index.md`](00-index.md) · 共用 helper [`01-common.md`](01-common.md) · 备胎/降级 [`02-data-sources.md`](02-data-sources.md)
> 写代码前先读 `01-common.md`（`em_get` / `norm_ticker` / `V39_RETRY_SESSION` 等）；主源被封时查 `02-data-sources.md`。

## 层目录速览

```
行情层（实时，不封IP）
├── 腾讯财经 API   → PE/PB/市值/换手率/涨跌停/指数/ETF (HTTP)
├── 腾讯 K 线      → 沪深日/周/月前后复权 + 1~60 分钟，三入口轮换 (V3.9 新增)
├── 通达信盘后包   → 某交易日沪深北全市场日线含成交额 (tdx.com.cn HTTP，V3.9 新增)
├── 腾讯逐笔       → 最近一个交易日的分笔成交明细，沪深个股 + ETF (HTTP，V3.10 新增)
├── 百度股市通     → K线带MA5/10/20 (V3.0 新增，HTTP)
├── 新浪复权因子   → qfq/hfq 因子序列 + 套用到不复权K线 (V3.7 新增)
└── mootdx        → K线 + 五档盘口 + 逐笔成交 (TCP 7709；⚠️ 2026-09 起行情命令返回空，#52，留档)

研报层
├── 东财 reportapi → 个股研报 + 行业研报 + PDF下载 + 评级 + 三年EPS
├── 同花顺 THS     → 一致预期EPS (直连 basic.10jqka.com.cn)
├── iwencai        → NL语义搜索研报 (唯一能力，需X-Claw)
└── 新浪研报列表   → 标题/机构/研究员/日期，研报第二来源 (V3.9 新增)

信号层
├── 同花顺热点     → 当日强势股 + 题材归因 reason tags (零鉴权 73ms)
├── 同花顺北向     → hgt/sgt 分钟资金流向 + 本地自缓存历史
├── 东财 slist     → 个股所属板块/概念归属 (V3.2.2 替换百度PAE)
├── 东财 push2     → 个股资金流向 分钟级 (V3.1 替换百度PAE)
├── 龙虎榜席位     → 上榜记录 + 买卖席位 TOP5 + 机构动向 (datacenter-web)
├── 全市场龙虎榜   → 每日全市场上榜股票 + 净买额排名 (datacenter-web)
├── 限售解禁日历   → 历史解禁 + 未来90天待解禁 (datacenter-web)
├── 行业板块排名   → 东财行业涨跌/上涨下跌家数 (V3.0 替换同花顺)
└── 板块资金流向   → 行业/概念/地域 × 今日/5日/10日 主力+超大/大/中/小四档 (push2, V3.5)

资金面 / 筹码层
├── 融资融券明细   → 日级融资余额/买入/偿还 + 融券 (datacenter-web)
├── 大宗交易       → 成交价/量 + 买卖方营业部 (datacenter-web)
├── 股东户数变化   → 季度股东户数 + 环比变化 (datacenter-web)
├── 分红送转       → 历史每股派息/送股/转增 (datacenter-web)
├── 个股资金流120日 → 主力/大单/中单/小单 日级净流入 (push2his)
├── 筹码分布 CYQ   → 获利比例/平均成本/90-70成本区间/筹码峰 (本地计算，V3.7 新增)
└── ETF 份额       → 上交所按日归档 / 深交所当前快照，万份 (V3.9 新增)

新闻层
├── 东财个股新闻   → 个股相关新闻 (search-api-web JSONP)
├── 财联社快讯     → 全市场实时电报 (v1 API+本地签名零key，✅V3.4 复活)
├── 东财全球资讯   → 7×24 财经快讯 (np-weblist，与财联社互备)
├── 华尔街见闻     → 7×24 快讯，按频道 + 翻页游标 (V3.9 新增)
└── 新闻联播       → 当日条目标题 + 文字稿 (央视网，V3.9 新增)

基础数据层
├── mootdx finance → 季报快照 (37字段, EPS/ROE/净利)
├── mootdx F10     → 最新提示 (公告/报道/大宗/两融/风险提示摘要；2026-09 起只剩这一类)
├── 东财个股信息   → 行业/总股本/流通股/市值/上市日期 (push2)
├── 新浪财报三表   → 资产负债表/利润表/现金流量表 (quotes.sina.cn)
├── baostock 估值历史 → 日频 PE/PB/PS/PCF + 换手率 + 停牌 + ST (不支持北交所，V3.7 新增)
├── baostock 标的信息 → 上市日/退市日/状态 (V3.7 新增)
├── 申万行业分类   → 行业归属变迁史，消除前视偏差 (仅代码无中文名，V3.7 新增)
└── ST 名单        → 沪深京 ST / *ST 当日快照 (东财，baostock 兜底，V3.9 新增)

公告层
├── 巨潮 cninfo    → 公告全文检索+下载 (cninfo.com.cn)
└── mootdx F10     → 最新公告摘要

打板层 (V3.3 新增)
├── 东财涨停池     → 连板数/几天几板/封板资金/炸板次数/行业 (push2ex)
├── 东财炸板池     → 涨停后开板 + 振幅/涨速 (push2ex)
├── 东财跌停池     → 封单资金/连续跌停/开板次数 (push2ex)
├── 东财昨涨停池   → 昨涨停今表现，算晋级率/赚钱效应 (push2ex)
└── 同花顺涨停揭秘 → 涨停原因题材/封板成功率/板型 (10jqka)

ETF期权层 (V3.3 新增)
├── 合约清单       → 50ETF/300ETF/科创50/500ETF 各月认购认沽 (新浪)
├── T型报价        → 买卖五档/持仓量/行权价/最新价 (新浪)
└── 希腊字母+IV    → Delta/Gamma/Theta/Vega/隐含波动率 (新浪)

舆情互动层 (V3.3 新增)
├── 互动易问答     → 投资者提问+公司回复 (巨潮，深市)
├── 上证e互动      → 沪市投资者提问+公司回复 (上交所运营的独立平台，V3.9 新增)
├── 同花顺热榜     → 人气值/概念标签/排名变化 (10jqka)
├── 东财人气榜     → 排名+排名变化+名称价格 (emappdata)
└── 东财概念命中   → 个股被归到哪些概念在炒+热度 (emappdata)

宏观与利率层 (V3.7 新增，V3.9 扩展)
├── 人民银行社融   → 社会融资规模增量 月度12列 (pbc.gov.cn，三级跳取 xls 附件)
├── 国家统计局PMI  → 制造业/非制造业/综合 + 大中小型企业分档 (stats.gov.cn)
├── 中债收益率曲线 → 国债 / 商业银行 AAA / 中短票 AAA，3月~30年 (V3.9 新增)
├── 回购定盘利率   → FR001/007/014 + FDR (中国货币网，V3.9 新增)
├── LPR            → 1 年 / 5 年全历史 (东财，V3.9 新增)
└── 全球宏观日历   → 公布值/预期/前值 + 重要事件 (华尔街见闻，V3.9 新增)

指数与交易日历层 (V3.8 新增)
├── 中证指数       → 当前成分 / 月末权重 / 近期 PE 与股息率
├── 国证指数       → 最近公布的成分与权重（月末快照）
└── 深交所日历     → 官方整月交易标志（完整性校验）

期货与大宗商品层 (V3.9 新增，#49)
├── 期货日行情     → 上期所/上期能源/郑商所/中金所/广期所 官方收盘数据
├── 期权日行情     → 商品期权 + 股指期权，Delta / 隐含波动率（中金所不公布这两项）
├── 持仓排名       → 会员成交量 / 持买 / 持卖前 20 名
├── 实时期货       → 新浪实时价（含大商所品种）
├── 期货日 K       → 新浪单合约 / 主力连续逐日 K 线（含大商所，V3.10 新增）
├── A50 期指       → 富时中国 A50 连续合约报价
└── 上海金现货     → 上金所 Au99.99 / Au(T+D) / Ag(T+D) 日线

事件驱动层 (V3.9 新增)
├── 业绩预告 · 机构调研 · 股东增减持 · 股票回购
└── 股权质押（中国结算周度） · 新股申购日历   (均为东财 datacenter)

可转债层 (V3.9 新增)
└── 可转债全表     → 条款 + 转股价 / 债价 / 转股价值 / 溢价率 (东财)

官方备胎扩展 (V3.8 新增)
├── 上交所/深交所  → 两融明细（分交易所调用，金额元、余量股/份）
└── 北交所         → 当前行情与五档快照（必须核对交易日）
```

## 端点路由速查（按需定位，不必通读全文）

只需一类数据时，按下表定位章节（§）局部读取。除 iwencai 需 API Key 外全部零 key。

| § | 函数 | 拿什么 | 源 |
|---|------|--------|----|
| 前置 | `norm_ticker(code)` | 任意写法→纯6位（`SH600519`/`600519.SH`/`600519.XSHG` 皆可；解析失败抛错不返空） | 本地 |
| 前置 | `to_joinquant(code)` | 转聚宽代码 `600519.XSHG` / `000001.XSHE`（北交所不转换） | 本地 |
| 1.1 | `tencent_quote(codes)` | 实时价/PE/PB/市值/换手/涨跌停/指数/ETF（带 `is_stale` 僵尸报价标志） | 腾讯 |
| 1.2 | `tencent_kline(code, period, adjust, start, end, count)` | 日/周/月前后复权 + 1~60 分钟 K 线（沪深，不含北交所） | 腾讯 |
| 1.3 | `tdx_daily_package(date)` | 某交易日沪深北全部证券日线（含成交额） | 通达信官网 |
| 1.4 | `tencent_ticks(code)` | 最近一个交易日的分笔成交（价/手/元/主动买卖；沪深个股+ETF，不含北交所） | 腾讯 |
| 1.5 | `baidu_kline_with_ma(code)` | 日K线带 MA5/10/20 | 百度 |
| 1.6 | `sina_adjust_factor(code, kind)` / `apply_adjust(bars, factors)` | 复权因子 qfq/hfq + 套用到不复权K线 | 新浪 |
| 1.7 | `tdx_client()` → `.bars()` / `.quotes()` / `.transaction()` | K线(多周期,不复权) / 五档盘口 / 逐笔成交（⚠️ 2026-09 起返回空，#52，留档） | 通达信 |
| 2.1 | `eastmoney_reports(code)` / `download_pdf(rec)` | 个股研报+评级+三年EPS / 研报PDF | 东财 |
| 2.1 | `eastmoney_industry_reports(industry_code)` | 行业研报 | 东财 |
| 2.2 | `ths_eps_forecast(code)` | 机构一致预期 EPS | 同花顺 |
| 2.3 | `iwencai_search(query)` / `iwencai_query(query)` | NL 语义搜研报/选股（需 Key） | iwencai |
| 2.4 | `sina_research_reports(code=None, page=1)` | 研报列表：标题/类型/机构/研究员（无评级） | 新浪 |
| 3.1 | `ths_hot_reason()` | 当日强势股+题材归因 | 同花顺 |
| 3.2 | `hsgt_realtime()` | 北向分钟流向（hgt 可用 / sgt 仅参考） | 同花顺 |
| 3.3 | `eastmoney_concept_blocks(code)` | 个股所属板块/概念归属 | 东财 |
| 3.4 | `eastmoney_fund_flow_minute(code)` | 个股资金流（分钟级） | 东财 |
| 3.5 | `dragon_tiger_board(code, date)` | 个股龙虎榜+买卖席位 TOP5 | 东财 |
| 3.6 | `lockup_expiry(code, date)` | 解禁历史+未来90天待解禁 | 东财 |
| 3.7 | `industry_comparison()` | 行业板块涨跌排名 | 东财 |
| 3.8 | `board_fund_flow(board_type, period)` | 板块资金流向（行业/概念/地域 × 今日/5日/10日，主力+四档） | 东财 |
| 3.9 | `daily_dragon_tiger(date)` | 全市场龙虎榜+净买额排名 | 东财 |
| 4.1 | `margin_trading(code)` | 融资融券明细 | 东财 |
| 4.2 | `block_trade(code)` | 大宗交易+营业部 | 东财 |
| 4.3 | `holder_num_change(code)` | 股东户数变化 | 东财 |
| 4.4 | `dividend_history(code)` | 分红送转历史 | 东财 |
| 4.5 | `stock_fund_flow_120d(code)` | 个股资金流（120日，日级） | 东财 |
| 4.6 | `chip_distribution(df)` | 筹码分布（获利比例/平均成本/90-70成本区间/筹码峰） | 本地计算 |
| 4.7 | `etf_shares(date, exchange)` | ETF 份额（万份）：上交所历史日期 / 深交所当前快照 | 上交所/深交所 |
| 5.1 | `eastmoney_stock_news(code)` | 个股新闻 | 东财 |
| 5.2 | `cls_telegraph()` | 财联社电报（7×24，本地签名零key） | 财联社 |
| 5.3 | `eastmoney_global_news()` | 全球资讯（7×24） | 东财 |
| 5.4 | `wallstreetcn_lives(channel, limit, cursor)` | 7×24 快讯（按频道，可翻页） | 华尔街见闻 |
| 5.5 | `cctv_news(date, with_content=True)` | 新闻联播条目 + 文字稿（政策信号研究用） | 央视网 |
| 6.1 | `tdx_client(check='finance').finance(symbol)` | 季报快照 37 字段 | 通达信 |
| 6.2 | `tdx_client(check='finance').F10(symbol, name)` | F10 文本（2026-09 起服务端只剩「最新提示」一类） | 通达信 |
| 6.3 | `eastmoney_stock_info(code)` | 行业/股本/市值/上市日期 | 东财 |
| 6.4 | `sina_financial_report(code, type)` | 财报三表 | 新浪 |
| 6.5 | `baostock_valuation_history(code, s, e)` | 估值历史 PE/PB/PS/PCF + 换手率 + 停牌 + ST（**不支持北交所**） | baostock |
| 6.6 | `baostock_stock_basic(code)` | 上市日 / **退市日** / 状态 | baostock |
| 6.7 | `sw_industry_history()` / `sw_industry_as_of(df, code, d)` | 申万行业**变迁史**（消除前视偏差，仅代码无中文名） | 申万 |
| 6.8 | `st_stock_list()` | 沪深京 ST / *ST 当日名单 | 东财（baostock 兜底） |
| 7.1 | `cninfo_announcements(code)` | 公告检索+PDF 下载 | 巨潮 |
| 7.2 | `tdx_client(check='finance').F10(symbol, name='最新提示')` | 最新公告摘要 | 通达信 |
| 8.1 | `em_zt_pool` / `em_zb_pool` / `em_dt_pool` / `em_yzt_pool` | 涨停/炸板/跌停/昨涨停四池 | 东财 |
| 8.2 | `ths_limit_up_pool(date)` | 涨停原因题材+封板成功率+板型 | 同花顺 |
| 8.3 | `limit_up_sentiment(date)` | 炸板率/连板高度/连板梯队 | 东财(四池组合) |
| 8.4 | `em_stock_monitor()` | 重点监控池（风险警示名单+生效时间窗） | 东财 |
| 8.5 | `em_price_anomaly()` / `em_price_anomaly_count()` | 日内异动明细 / 按标的聚合异动统计（严重异常波动） | 东财 |
| 9.1 | `sina_option_codes` / `sina_option_tquote` / `sina_option_greeks` | ETF期权合约清单 / T型报价 / 希腊字母+IV | 新浪 |
| 10.1 | `cninfo_irm(code)` | 互动易问答（提问+公司回复，深市） | 巨潮 |
| 10.2 | `ths_hot_list()` / `em_hot_rank()` / `em_hot_concept(code)` | 热榜/人气榜/概念命中 | 同花顺+东财 |
| 10.3 | `sse_e_interaction(code=None, kind='answered')` | 上证e互动问答（沪市） | 上证e互动（上交所运营） |
| 11.1 | `pboc_social_financing(year)` | 社会融资规模增量（月度12列） | 人民银行 |
| 11.2 | `nbs_pmi()` | 制造业/非制造业/综合 PMI + 大中小型企业 | 国家统计局 |
| 11.3 | `chinabond_yield_curve(start, end, curve)` | 国债 / 银行 AAA / 中短票 AAA 收益率曲线 3月~30年 | 中债 |
| 11.4 | `repo_fixing_rates(kind)` | 回购定盘利率 FR / FDR 001·007·014 | 中国货币网 |
| 11.5 | `lpr_history()` | LPR 1 年 / 5 年全历史 | 东财 |
| 11.6 | `macro_calendar(start, end, country, min_importance)` | 全球宏观日历（公布值/预期/前值） | 华尔街见闻 |
| 12.1 | `index_constituents(index_code, provider)` | 最近公布的沪深北指数成分；csi/cni 显式选源 | 中证/国证 |
| 12.2 | `index_weights(index_code, provider)` | 最近公布的指数权重（百分数），保留真实日期 | 中证/国证 |
| 12.3 | `index_valuation(index_code)` | 两种口径 PE、股息率；不含 PB | 中证 |
| 12.4 | `trading_calendar(year, month)` | 官方整月交易日历 | 深交所 |
| 13.1 | `futures_daily(date, exchange)` | 期货日行情（SHFE/INE/CZCE/CFFEX/GFEX） | 五家期货交易所 |
| 13.2 | `options_daily(date, exchange)` | 商品期权 / 股指期权日行情 + Delta / IV（中金所不公布这两项） | 五家期货交易所 |
| 13.3 | `futures_position_rank(date, exchange, symbol)` | 会员成交 / 持买 / 持卖前 20 名 | 上期所/能源/郑商所/中金所 |
| 13.4 | `futures_realtime(symbols)` | 实时期货（含大商所品种） | 新浪 |
| 13.5 | `a50_futures()` | 富时中国 A50 期指 | 新浪 |
| 13.6 | `sge_spot(instrument)` | 上海金交所现货日线（黄金/白银/铂金） | 上金所 |
| 13.7 | `futures_kline(symbol, start, end)` | 期货日 K：单个合约 / 主力连续的逐日序列（含大商所） | 新浪 |
| 14.1 | `earnings_forecast(code, report_date, limit)` | 业绩预告 | 东财 |
| 14.2 | `institution_survey(code, start, end, detail, limit)` | 机构调研（汇总 / 逐机构） | 东财 |
| 14.3 | `holder_trades(code, direction, start, end, limit)` | 股东增减持 | 东财 |
| 14.4 | `share_buyback(code, progress, limit)` | 股票回购方案与进度 | 东财 |
| 14.5 | `equity_pledge(code, date, limit)` | 股权质押比例（中国结算周度，仅沪深） | 东财 |
| 14.6 | `ipo_calendar(limit)` | 新股申购日历 | 东财 |
| 15.1 | `convertible_bonds(include_delisted=False)` | 可转债条款 + 转股价值 / 溢价率 | 东财 |
| 官方备胎扩展 | `margin_trading_backup(date, exchange, code=None)` | 单所两融明细（先执行 §12 helper） | 上交所/深交所 |
| 官方备胎扩展 | `bse_quote_backup(date, code=None)` | 北交所全板/单票当前快照（先执行 §12 helper） | 北交所 |
| 备用源速查 | `dragon_tiger_backup` / `fund_flow_backup` / `announcements_backup` | 龙虎榜/资金流/公告官方备胎（主源被封时降级） | 交易所官方+新浪+东财(沪市公告) |
| 估值公式 | `forward_pe` / `pe_digestion` / `calc_peg` / `full_valuation(code)` | 前向PE / PE消化时间 / PEG / 单票估值全景 | 本地计算 |
