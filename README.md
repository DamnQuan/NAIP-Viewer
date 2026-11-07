# NAIP-Viewer

NAIP 航图阅读器（Vue 3 + Vite 前端 + Node 零依赖登录后端）。浏览 NAIP2610 机场航图 PDF、
NAIP 总资料、航路 / 导航台 / 空域数据，支持深浅色主题。

## 登录与账号

需登录后使用，不支持自助注册。两种角色：

- **管理员**：可添加 / 删除账号、修改任意账号密码与角色（侧栏「账号管理」）
- **普通用户**：仅浏览

默认管理员：**quanquan / quanquan**（首次启动后端时自动创建，请登录后立即改密）。
账号数据存 `data/users.json`（scrypt 散列，不入库），删除该文件即可重置全部账号。

## 启动

```bash
npm install
npm run index     # 解析 NAIP2610 的 CSV，生成 public/data/index/*.json

# 开发（两个终端）
npm run server    # 登录后端 http://127.0.0.1:8787
npm run dev       # 前端 http://localhost:5173（/api 已代理到后端）

# 生产
npm run build
npm run server    # 后端直接托管 dist/，访问 http://127.0.0.1:8787
```

生产部署时把数据链接进 dist：

```bat
mklink /J dist\data ..\public\data
```

## 功能

- **登录系统** — 用户名 + 密码，会话 7 天；普通 / 管理员两级权限，
  管理员可增删账号、改密码与角色（含最后一名管理员保护、生产环境 /data 访问需登录）
- **机场航图** — 275 个机场，航图按类别分组（细则/机场图/SID/STAR/ILS/VOR/NDB/RNP 等），
  标注 SUP 与修订，PDF 渲染 + 缩放 + PgUp/PgDn 连续翻图 + 打印
- **NAIP 总资料** — 修订单、总则、航路、机场等 134 份文件，多页 PDF
- **航路数据** — VOR/DME、NDB、航路点、航路、班机航线、空域、机场跑道、等待程序，可搜索分页

## 结构

```
server.js                 登录后端（零依赖：scrypt 散列 + 会话 Cookie + 账号管理 API）
scripts/build_index.py    CSV(GBK) → JSON 索引（含航图文件名映射规则）
src/api.js                后端 API 封装
src/store.js              全局状态与数据 URL
src/components/           LoginPage / HomePage / AdminPanel / AirportPanel / DocsPanel /
                          DataPanel / PdfViewer / VIcon
```
