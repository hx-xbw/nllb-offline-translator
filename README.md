# 离线多语言翻译系统（NLLB-200 + FastAPI）

一个**完全在本地运行**的多语言翻译 Web 系统。无需联网、不调用任何第三方翻译 API，文本与文档不上传云端，适合对数据隐私有要求的场景。

> 毕业设计项目 · 2026

## 功能

- **200 种语言互译**：基于 Meta 的 NLLB-200 模型，支持任意语言对直接翻译
- **文本翻译**：选择源语言 / 目标语言，输入文本即时翻译
- **文档翻译**：上传 `.txt` / `.docx` / `.pdf`，翻译后直接下载结果文件
- **长文档分段**：自动按 800 字符切分，规避模型 512 token 的输入上限
- **中文文件名兼容**：按 RFC 8187 编码下载文件名，解决浏览器乱码
- **响应式界面**：Jinja2 模板 + Bootstrap，适配 PC 与移动端

## 技术栈

| 层 | 技术 |
|---|---|
| Web 框架 | FastAPI、Uvicorn、Jinja2、Bootstrap |
| 模型 | `facebook/nllb-200-distilled-600M`、Hugging Face Transformers、PyTorch |
| 文档解析 | python-docx（DOCX）、PyPDF2（PDF） |
| 部署 | 本地 CPU / GPU 自动切换 |

## 关键实现

**1. 模型懒加载**

600M 参数模型首次加载需要 30–90 秒。如果放在应用启动时同步加载，用户第一次访问页面就会长时间白屏。因此改为**首次翻译请求时才加载**，服务启动瞬间可用。

**2. GPU 自动检测**

```python
if torch.cuda.is_available():
    model = model.cuda()
```

有 NVIDIA 显卡自动上 GPU，没有则退回 CPU，同一份代码适配两种环境。

**3. 长文本分段**

模型单次最多处理 512 token，长文档直接送入会被截断丢内容。按 800 字符切块逐段翻译后拼接，保证全文完整。

**4. 中文文件名下载乱码**

`Content-Disposition` 头直接放中文文件名，浏览器会乱码。改用 RFC 8187 的 `filename*=utf-8''` 形式并做 URL 编码解决。

## 快速开始

```bash
# 1. 安装依赖（建议 Python 3.10+）
pip install -r requirements.txt

# 2. 启动服务
uvicorn main:app --reload

# 3. 浏览器打开
# http://127.0.0.1:8000
```

Windows 用户也可以直接双击 `启动翻译系统.bat`。

> 首次启动会自动从 Hugging Face 下载模型（约 2.4 GB），需要网络；下载完成后即可完全离线运行。

## 实测性能

测试环境：Intel i5-12400F / 16 GB 内存 / **无独立显卡** / Windows 11

| 场景 | 耗时 |
|---|---|
| 100 字短文本 | 0.8 – 1.5 s |
| 500 字中等文本 | 1.5 – 3 s |
| 1000 字长文本（分段） | 4 – 7 s |
| 10 页 PDF（约 6000 字） | 15 – 30 s |
| 20 页 PDF（约 12000 字） | 40 – 70 s |

## 目录结构

```
.
├── main.py                 # FastAPI 应用：路由、模型加载、翻译逻辑、文档解析
├── templates/
│   └── index.html          # 前端页面（Jinja2 + Bootstrap）
├── requirements.txt
├── 启动翻译系统.bat          # Windows 一键启动
└── 一键启动翻译系统.ps1
```

## 已知限制

- 模型体量较大，内存占用约 3 GB，低配机器建议改用更小的模型或加量化
- PDF 仅支持文本型，扫描件需要先 OCR
- 界面为服务端渲染，后续可改为 Vue / React 单页应用
