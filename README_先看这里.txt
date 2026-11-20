@us-market V2.0 - 线上自动更新试验包（S&P 500）

用途：部署到你自己的 GitHub 公共仓库后，GitHub Actions 会按美国交易日自动运行，每天尝试下载上游历史文件、计算五周期，并发布小型 CSV / JSON / Markdown。

目前未部署！用户必须先创建 GitHub 账号/仓库并一次性上传项目文件。
GitHub Actions 定时任务通常在马来西亚时间 周二-周六 11:23 左右启动（可能延迟）。
即使成功运行，若第三方来源未更新，最新实际数据日期不会前进！

最简单的部署：
1）注册/登录 https://github.com/
2）创建公开仓库，例如 us-market-breadth。
3）把本压缩包所有文件（包含隐藏 .github/workflows/daily-update.yml）放入仓库。
   注意：GitHub 网页上传嵌套隐藏目录不方便，推荐解压后使用 GitHub Desktop 提交整个文件夹，或连接 GitHub app 让我协助发布。
4）Repository -> Actions -> Update SP500 market breadth -> Run workflow。首次运行检查结果。
5）Repository -> public/latest.md 就是我以后可以读取的固定结果路径。
   例如 https://github.com/YOURNAME/us-market-breadth/blob/main/public/latest.md

以后：打开 ChatGPT 输入 @us-market，同时提供这个公开仓库URL一次。
ChatGPT 可以在单次复盘时通过网络查看这个公开地址，但不会在聊天之外自动监控数据，也不能保证网络搜索立即读到新提交。

重点限制：
- 目前仅覆盖 S&P500；全美股普通股和 Nasdaq Composite 仍待开发。
- 不是官方历史指数广度；每次需阅读质量报告。
- 计算采用调整后收盘价，52周新高/低与盘中价格口径不同。
- 公共仓库的所有内容对外公开，不要放个人账号、密码、令牌或内部交易记录。
- GitHub 定时工作流可能延迟；公共仓库60天无活动时可能被自动停用。
- GitHub 及上游数据源服务条款、免费使用政策可能调整。
