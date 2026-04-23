# PDF Converter 项目进度文档

## 项目状态：已完成

**开始日期**: 2026-04-22  
**当前阶段**: 版本4.0 - 专注 Word 转换与性能优化（已完成）

---

## 版本历史

### 版本4.0（当前）- 2026-04-23
- **专注 Word 转换**：删除 Markdown 功能，专注 PDF 转 Word
- **内存优化**：任务完成后强制释放内存，防止内存泄漏
- **稳定性提升**：增强错误处理，验证生成文件完整性
- **任务列表优化**：3 列简洁布局（任务名、状态、用时）
- **智能排序**：最新任务排第一，已完成自动移到底部
- **日志优化**：每次新任务自动清空日志区

### 版本3.0 - 2026-04-23
- **任务独立化**：Word 和 Markdown 各自生成独立任务，可同时转换
- **文件名防冲突**：自动添加_Word/_Markdown 后缀避免文件名冲突
- **空白图片修复**：智能检测并删除 PDF 水印、分隔线等装饰性图片
- **任务列表重构**：4 列布局（任务名、状态、用时、操作），状态显示更简洁
- **操作按钮简化**：取消/删除按钮纯文字显示

### 版本2.0 - 2026-04-22
- **任务队列系统重构**：替换进度条为任务列表
- **Bug 修复**：修复 Word 文档图片显示不全问题
- **用户体验改进**：支持转换过程中添加任务、单独终止任务

### 版本1.0 - 2026-04-22
- 基础功能实现：PDF 转 Word/Markdown
- 批量转换支持
- Element Plus 风格 UI

---

## 已完成工作

### ✅ Phase 1: 项目基础（已完成）

#### 1.1 项目结构创建
- [x] 创建项目目录结构
- [x] 创建 requirements.txt
- [x] 创建所有模块的 __init__.py

#### 1.2 开发环境配置
- [x] 安装 Python 依赖
- [x] 验证核心库可用性

#### 1.3 主窗口基础 UI
- [x] 实现主窗口框架
- [x] 实现文件选择功能
- [x] 实现拖拽上传功能
- [x] 实现输出目录选择功能

---

## 当前版本修复的 Bug

### Bug #1: 内存泄漏 ✅ 已修复 (v4.0)
**问题**：PDF 转换过程中内存持续上升，任务完成后不释放

**修复**：
- [x] 在 `_on_task_finished` 方法中清理转换器对象
- [x] 增加线程等待时间（1 秒→2 秒）
- [x] 调用 `gc.collect()` 强制垃圾回收
- [x] 使用多进程模式限制 CPU 核心数（2 核）

**代码位置**：
```python
# src/core/task_manager.py
def _on_task_finished(self, task_id: str, success: bool, message: str):
    # 清理转换器对象，释放内存
    if hasattr(worker, 'word_converter') and worker.word_converter:
        worker.word_converter = None
    # 等待线程结束
    worker.wait(2000)
    # 删除 worker 引用
    del self.workers[task_id]
    # 强制垃圾回收
    import gc
    gc.collect()
```

### Bug #2: mysql 必知必会 PDF 转换失败 ✅ 已修复 (v4.0)
**问题**：转换特定 PDF 时生成的 Word 文件无法打开

**修复**：
- [x] 启用多进程模式（`multi_processing=True`）
- [x] 限制 CPU 核心数（`cpu_count=2`）避免内存爆炸
- [x] 验证输出文件存在性和大小
- [x] 验证 docx 文件可打开且内容非空
- [x] 添加 MemoryError 特殊处理

**代码位置**：
```python
# src/core/pdf_to_word.py
self.converter.convert(
    output_path,
    start=start,
    end=end,
    kwargs={
        'debug': False,
        'multi_processing': True,
        'cpu_count': 2,
    }
)

# 验证生成的文件
if os.path.getsize(output_path) == 0:
    return False, "转换生成的文件为空"
```

### Bug #3: Markdown 功能效果不佳 ✅ 已删除 (v4.0)
**问题**：PDF 转 Markdown 功能最终效果不好

**修复**：
- [x] 删除 `pdf_to_markdown.py` 模块
- [x] 删除 UI 中的 Markdown 复选框
- [x] 删除所有 Markdown 相关代码
- [x] 专注优化 Word 转换功能

### Bug #4: 任务列表操作列冗余 ✅ 已修复 (v4.0)
**问题**：操作列占用空间且功能单一

**修复**：
- [x] 删除操作列
- [x] 调整表格为 3 列布局（任务名、状态、用时）
- [x] 优化列宽分配

### Bug #5: 任务列表排序不合理 ✅ 已修复 (v4.0)
**问题**：新任务添加在底部，已完成任务混在中间

**修复**：
- [x] 新任务插入到第一行（`row=0`）
- [x] 任务完成后自动移到底部（`moveRow`）
- [x] 保持正在运行的任务在上方

### Bug #6: 日志区杂乱 ✅ 已修复 (v4.0)
**问题**：多次任务的日志混在一起

**修复**：
- [x] 开始新任务前自动清空日志区
- [x] 保持日志区整洁

### Bug #7: MySQL必知必会PDF转换时崩溃闪退 ✅ 已修复
**问题**：转换MySQL必知必会PDF时，任务完成后程序崩溃闪退

**根本原因**：
- `QTableWidget` 没有 `moveRow` 方法（这是 `QTableView` 的方法）
- 任务完成时 `update_task_row` 调用 `self.task_table.moveRow(row, ...)` 触发 `AttributeError`
- 由于异常发生在信号回调中，PyQt6 无法优雅处理，导致整个程序崩溃

**修复**：
- [x] 新增 `_move_row_to_bottom` 方法，手动实现行移动（复制数据→插入新行→删除旧行）
- [x] 替换 `moveRow` 调用为 `_move_row_to_bottom`
- [x] 移动行时阻止信号，避免 `cellChanged` 误触发

**代码位置**：
```python
# src/ui/main_window_v2.py
def _move_row_to_bottom(self, source_row: int):
    """将指定行移动到表格底部"""
    # 保存行数据 → 插入新行 → 删除旧行
```

### Bug #8: 转换后的Word文档无法打开 ✅ 已修复
**问题**：MySQL必知必会PDF转换完成后，生成的Word文档用Word软件打开时报错无法打开

**根本原因**：
- pdf2docx 将PDF中的背景图层转为anchor类型的浮动图片（`behindDoc=1`）
- 其中3个浮动图片的尺寸极度异常：宽4.3英寸×高3391英寸（正常A4页面仅11.7英寸高）
- 这些异常巨型图片导致Word渲染时崩溃
- 原有的 `_fix_images_in_docx` 只处理 `inline_shapes`，完全忽略了anchor类型的浮动图片
- XML查找使用 `body.findall(qn('w:drawing'))` 只搜索直接子元素，无法找到嵌套在 `w:p > w:r > w:drawing` 中的元素

**修复**：
- [x] 新增 `_fix_anchor_drawings` 方法，专门处理anchor类型浮动图片
- [x] 删除尺寸超过20×30英寸的异常巨型浮动图片
- [x] 删除 `behindDoc=1` 且尺寸接近整页的背景浮动图片
- [x] 修复XML查找逻辑：`body.findall()` 改为 `body.findall('.//')` 递归搜索嵌套元素
- [x] 优化图片分析内存使用：大图采用采样方式代替全像素遍历

**代码位置**：
```python
# src/core/pdf_to_word.py
def _fix_anchor_drawings(self, body):
    """处理anchor类型的浮动图片"""
    # 递归查找所有drawing元素
    drawings = body.findall('.//' + qn('w:drawing'))
    # 删除异常巨型图片和背景层图片

# XML查找修复
drawings = body.findall('.//' + qn('w:drawing'))  # 递归搜索
```

### Bug #9: 消防协议PDF转换后水印图片覆盖内容 ✅ 已修复
**问题**：转换"消防产品线_消防终端与平台通讯国标协议_v1"PDF时，生成的Word文档中有大量水印图片覆盖了有用内容

**根本原因**：
- pdf2docx 将PDF中的背景图层全部转为 `behindDoc=1` 的 anchor 类型浮动图片
- 该PDF共生成 227 个 anchor 浮动图片，全部是 `behindDoc=1`（背景/水印层）
- 初版修复策略过于激进：对所有 `behindDoc=1` 的 anchor 图片全部删除，导致含实质内容（表格、图表等）的图片也被误删

**修复**：
- [x] 改为内容分析策略：对 `behindDoc=1` 的 anchor 图片进行像素分析，智能区分水印和有用图片
- [x] 水印判断标准：极小文件（<1KB，装饰线）、纯色/低内容图片（深色像素<3%且中等亮度像素<10%）
- [x] 有内容图片处理：将 `behindDoc=1` 改为 `behindDoc=0`，使其在文字前面正常显示
- [x] 消防PDF处理结果：删除 143 个纯水印/背景图片，保留 84 个含内容的背景浮动图片
- [x] MySQL PDF不受影响（0个 behindDoc 图片）

**代码位置**：
```python
# src/core/pdf_to_word.py - _fix_anchor_drawings + _is_watermark_image
def _is_watermark_image(self, drawing, doc, ns_a, ns_r):
    """通过分析图片像素内容判断是否为水印"""
    # 极小文件 → 装饰线，是水印
    # 深色像素<3% 且 中等亮度像素<10% → 纯背景，是水印
    # 否则 → 有内容，不是水印，应保留
```

---

## 技术亮点

1. **内存管理优化**
   - 及时清理转换器对象
   - 强制垃圾回收
   - 限制并发 CPU 核心数

2. **文件完整性验证**
   - 检查输出文件存在性
   - 检查文件大小非零
   - 使用 python-docx 验证 docx 可打开

3. **用户体验优化**
   - 智能任务排序
   - 自动日志清理
   - 简洁的 3 列表格布局

---

## 下一步计划

- [ ] 添加转换进度百分比显示
- [ ] 支持自定义转换参数（页码范围等）
- [ ] 添加转换历史记录功能
- [ ] 优化大文件转换性能
