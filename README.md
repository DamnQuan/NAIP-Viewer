# NAIP-Viewer

NAIP 航图阅读器（Vue 3 + Vite，纯前端）。浏览 NAIP2610 机场航图 PDF、NAIP 总资料、
航路 / 导航台 / 空域数据，支持深浅色主题。

## 准备数据

数据文件不入库（见 `.gitignore`），放到 `public/data/NAIP2610/`：

```
public/data/
└── NAIP2610/        ← NAIP 原始数据（Terminal/、GeneralDoc/、各 CSV）
└── index/           ← 由 npm run index 生成，无需手工准备
```

如果数据在别处，可以建目录联接代替复制（Windows）：

```bat
cd public\data
mklink /J NAIP2610 <NAIP2610 数据目录的实际路径>
```

## 启动

```bash
npm install
npm run index     # 解析 NAIP2610 的 CSV，生成 public/data/index/*.json
npm run dev       # 开发预览 http://localhost:5173
npm run build     # 构建到 dist/（不含数据，避免拷贝数 GB 航图）
```

静态部署时，把数据链接进 dist：

```bat
mklink /J dist\data ..\public\data
```

然后 `dist/` 用任意静态服务器托管即可。

## 功能

- **机场航图** — 275 个机场，航图按类别分组（细则/机场图/SID/STAR/ILS/VOR/NDB/RNP 等），
  标注 SUP 与修订，PDF 渲染 + 缩放 + PgUp/PgDn 连续翻图 + 打印
- **NAIP 总资料** — 修订单、总则、航路、机场等 134 份文件，多页 PDF
- **航路数据** — VOR/DME、NDB、航路点、航路、班机航线、空域、机场跑道、等待程序，可搜索分页

## 结构

```
scripts/build_index.py    CSV(GBK) → JSON 索引（含航图文件名映射规则）
src/store.js              全局状态与数据 URL
src/components/           HomePage / AirportPanel / DocsPanel / DataPanel / PdfViewer / VIcon
```
