# 论文图素材库

按图类型、年份、会议、领域和评分筛选的论文配图参考图库。

- 网站入口：`index.html` 或 `gallery.html`
- 列表缩略图：最长边 600 像素
- 放大预览：最长边 1600 像素，WebP 压缩
- 高清原图及上下文：点击各图的 arXiv 论文链接

年份支持多选，默认全部勾选。取消勾选某一年（例如 2026）即可排除该年的图片；点击「清空」后再勾选需要的年份，可以只看指定年份；点击「全选」恢复全部年份。

年份从 arXiv 编号的 `YYMM` 提取，以首次公开年份为准，不使用会议年份或后续更新年份。例如 `2508.19236` 即使发表于 ICLR2026，仍归入 2025 年。编号对应首次公告月份，可能与实际上传日期跨月或跨年；当前数据未包含精确上传日期，详见 [arXiv 编号说明](https://info.arxiv.org/help/availability.html)。无法识别年份的图片列入「年份未知」。年份筛选可与其他条件组合使用。

图片版权归原论文作者及相应权利人所有；此处仅用于学术参考，不授予图片再使用许可。

## 更新图库

UI 源模板为 `tools/gallery_template.html`，共享投票客户端为仓库根目录的 `shared-votes.js`。请修改这些源文件；`index.html` 和 `gallery.html` 是构建产物。

先同步远程代码，然后从含原始图片的本地图书库目录读取数据并构建（Python 3.9+，需要 Pillow）：

```sh
git pull --ff-only
python3 tools/build_gallery.py --source-root /path/to/figure_library --html-only
python3 -m unittest discover -s tools -p 'test_*.py'
```

`--html-only` 复用已压缩的图片，缺失的图片仍会生成；原图有修改时去掉此参数以重新压缩。构建只从本地 `gallery.html` 读取图库数据和分类，不复用旧 UI，也不会用本地旧投票脚本覆盖仓库版本。共享投票配置读取本地 `_share/vote-backend/public-config.json`；新增图片 ID 后仍需部署投票后端的 catalog。原图、后台凭据不需要提交。
