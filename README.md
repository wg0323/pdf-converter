# PDF转换器（PDF Converter）

一款基于 PyQt6 的 Windows 桌面应用，将 PDF 文件批量转换为 Word（.docx）文档。支持普通 PDF 与扫描版 PDF，扫描版可通过 PaddleOCR 识别文字（未安装 OCR 时自动降级为图片模式）。

## 功能特点

- **PDF 转 Word**：普通 PDF 使用 pdf2docx 转换，保留排版与图片
- **扫描版 PDF 支持**：自动检测扫描版，OCR 识别文字（可选 PaddleOCR），不可用时降级为整页图片模式
- **任务队列管理**：最多 20 个任务排队，串行逐个转换（底层库非线程安全，串行以保证稳定）
- **智能图片修复**：自动清理转换产物中的水印、异常浮动图片、空白装饰图
- **防覆盖保护**：输出文件同名时自动追加序号；重复任务自动去重
- **拖拽添加**：支持将 PDF 文件直接拖入窗口
- **协作式取消**：转换中可安全取消任务，退出时等待线程结束

## 技术栈

| 类别 | 技术 |
| --- | --- |
| 语言 | Python 3 |
| GUI | PyQt6 |
| PDF 转 Word | pdf2docx |
| PDF 解析 | PyMuPDF (fitz) |
| Word 处理 | python-docx |
| 图像处理 | Pillow |
| OCR（可选） | PaddleOCR + PaddlePaddle |
| 打包 | PyInstaller |

## 项目结构

```
pdf-converter/
├── src/
│   ├── main.py                  # 程序入口
│   ├── core/
│   │   ├── pdf_to_word.py       # PDF转Word核心（含扫描版检测/OCR/图片修复）
│   │   ├── single_task_worker.py# 单任务工作线程（QThread）
│   │   └── task_manager.py      # 任务队列调度（串行执行）
│   ├── models/
│   │   └── task_item.py         # 任务数据模型
│   └── ui/
│       ├── main_window_v2.py    # 主窗口
│       └── styles/              # 界面样式
├── resources/icons/             # 应用图标资源
├── tests/                       # 功能测试
├── PDFConverter.spec            # PyInstaller 打包配置
├── build.bat                    # 一键打包脚本
└── requirements.txt             # 依赖清单
```

## 安装与运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行程序
python src/main.py
```

> 提示：PaddleOCR 为可选依赖，未安装时扫描版 PDF 将以图片模式转换。

## 打包

```bash
build.bat
```

产物输出至 `dist\PDFConverter.exe`（单文件，含图标资源）。

## 测试

```bash
python tests/test_conversion.py
```

## 当前进度

**当前版本**：v4.0（专注 Word 转换）

### 已完成

- [x] PDF 转 Word 核心功能（普通 / 扫描版自动识别）
- [x] 任务队列调度（20 任务上限、串行执行）
- [x] Word 文档图片修复（水印清理、异常浮动图处理、空白图删除）
- [x] Element Plus 风格 UI、拖拽添加、任务智能排序
- [x] PyInstaller 单文件打包
- [x] 代码审查改进（2026-07）：
  - 修复跨线程取消竞争与 QThread 销毁崩溃（改为协作式取消 + finished 信号延迟清理）
  - 修复任务行号缓存失效导致的 UI 状态错位
  - 修复 inline 图片删除索引错位可能误删正常图片的问题
  - 修复 pdf2docx 转换参数未生效、扫描版转换资源泄漏
  - 新增任务去重与输出文件防覆盖保护
- [x] 移除 Markdown 转换功能（2026-07）：删除 pdf_to_markdown 模块及全部相关代码、依赖（pdfplumber）与打包配置
- [x] 移除输出格式选择入口，固定为 PDF 转 Word（2026-07）
- [x] 修复并发转换闪退（2026-07）：底层 pdf2docx/PyMuPDF/PaddleOCR 非线程安全，改为串行执行；新增 faulthandler + excepthook 崩溃日志（crash_log.txt）
- [x] 修复大文档转换整体闪退（2026-07）：定位到 PyMuPDF C 扩展在解析特定文档时 refcount 崩溃（Python 无法捕获）。将 pdf2docx 转换放入独立子进程隔离，子进程崩溃时主程序存活并将该任务标记为失败，不再拖垮整个应用

### 下一步计划

- [ ] 添加转换进度百分比显示
- [ ] 支持自定义转换参数（页码范围等）
- [ ] 添加转换历史记录功能
- [ ] 优化大文件转换性能
