import os
import gc
import sys
import logging
import traceback
import tempfile
import multiprocessing
from pathlib import Path
from typing import Optional, TYPE_CHECKING

# pdf2docx 导入链很重（PyMuPDF/numpy/opencv），懒加载以免拖慢主程序启动
if TYPE_CHECKING:
    from pdf2docx import Converter

logger = logging.getLogger(__name__)


def _pdf2docx_worker(pdf_path, output_path, start, end, result_queue):
    """
    在独立子进程中执行 pdf2docx 转换。

    pdf2docx 依赖的 PyMuPDF C 扩展在解析某些文档时可能触发 refcount 错误
    等原生崩溃，这类崩溃无法被 Python 的 try/except 捕获，会直接终止进程。
    放到子进程执行后，即使崩溃也只是子进程退出，父进程（GUI）通过 exitcode
    感知并优雅报错，不会被整体拖垮。
    """
    try:
        from pdf2docx import Converter
        cv = Converter(pdf_path)
        cv.convert(
            output_path,
            start=start,
            end=end,
            pages=None,
            debug=False,
            multi_processing=False,
        )
        cv.close()
        result_queue.put((True, ""))
    except Exception as e:
        result_queue.put((False, f"转换失败: {e}"))


class PDFToWordConverter:
    def __init__(self):
        self.converter: Optional["Converter"] = None
        self._ocr_engine = None
        self._is_cancelled = False
        self._process: Optional[multiprocessing.Process] = None

    # ========== 扫描版PDF检测 ==========

    def _is_scanned_pdf(self, pdf_path: str, sample_pages: int = 10) -> bool:
        """
        检测PDF是否为扫描版（每页都是图片，无可提取文字）

        采样前N页，如果所有采样页均无文字且仅有整页图片，则判定为扫描版。

        Args:
            pdf_path: PDF文件路径
            sample_pages: 采样页数

        Returns:
            True 表示是扫描版PDF
        """
        try:
            import fitz
            doc = fitz.open(pdf_path)
            try:
                total = len(doc)
                check_count = min(sample_pages, total)

                if check_count == 0:
                    return False

                no_text_count = 0
                for i in range(check_count):
                    page = doc[i]
                    text = page.get_text().strip()
                    images = page.get_images()
                    if len(text) == 0 and len(images) >= 1:
                        no_text_count += 1
            finally:
                doc.close()

            # 如果所有采样页都无文字且有图片，则判定为扫描版
            is_scanned = (no_text_count == check_count) and (check_count > 0)
            if is_scanned:
                logger.info(f"检测到扫描版PDF（{check_count}/{check_count}页无文字）")
            else:
                logger.info(f"非扫描版PDF（{no_text_count}/{check_count}页无文字）")
            return is_scanned

        except Exception as e:
            logger.info(f"检测PDF类型时出错: {e}")
            return False

    # ========== OCR引擎管理 ==========

    @staticmethod
    def _find_ocr_addon() -> Optional[str]:
        """
        查找 OCR 增强包目录（ocr_addon）

        增强包内含 paddle/paddleocr 及其依赖与离线模型，单独分发，
        用户解压到程序目录内即可启用 OCR。
        打包环境找 exe 同级目录，开发环境找项目根目录。

        Returns:
            增强包目录路径，不存在则返回 None
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = str(Path(__file__).resolve().parents[2])
        addon_dir = os.path.join(base_dir, 'ocr_addon')
        return addon_dir if os.path.isdir(addon_dir) else None

    def _get_ocr_engine(self, log=None):
        """
        获取 PP-Structure 引擎实例（懒加载，首次使用时初始化）

        PP-Structure = 版面分析 + OCR + 阅读顺序恢复，可直出分层可编辑的 Word。
        优先使用 OCR 增强包（ocr_addon）中的依赖与离线模型。

        Args:
            log: 可选的界面日志回调（接收一个字符串），用于向用户透传启用/降级原因

        Returns:
            PPStructure 实例，如果不可用则返回 None
        """
        log = log or (lambda m: None)
        if self._ocr_engine is None:
            try:
                # 增强包存在时注入 sys.path（打包产物未内置 paddle，由增强包提供）。
                # 依赖放在 site-packages 子目录：paddle 启动时按路径名包含
                # "site-packages" 定位原生库目录，否则在冻结环境回退到
                # site.USER_SITE（为 None）而崩溃
                addon_dir = self._find_ocr_addon()
                if addon_dir is None:
                    log("未找到 OCR 增强包（程序目录下缺少 ocr_addon 文件夹）")
                    logger.info("未找到 OCR 增强包，扫描版PDF将使用图片模式转换")
                    return None
                if addon_dir:
                    addon_site = os.path.join(addon_dir, 'site-packages')
                    if os.path.isdir(addon_site) and addon_site not in sys.path:
                        sys.path.insert(0, addon_site)
                    # PyInstaller 冻结环境下 site.USER_SITE 为 None，而 paddle
                    # 启动时会用它拼接原生库路径（不判空，直接 TypeError），
                    # 指向增强包 site-packages 使其能定位 paddle/libs
                    import site
                    if getattr(site, 'USER_SITE', None) is None:
                        site.USER_SITE = addon_site

                from paddleocr import PPStructure
                logger.info("正在初始化PP-Structure引擎...")
                log("正在初始化 OCR 引擎（首次较慢）...")

                # 优先使用增强包内的离线模型，避免首次使用时联网下载
                model_kwargs = {}
                if addon_dir:
                    models_dir = os.path.join(addon_dir, 'models')
                    for name, param in (
                        ('det', 'det_model_dir'),
                        ('rec', 'rec_model_dir'),
                        ('layout', 'layout_model_dir'),
                    ):
                        model_dir = os.path.join(models_dir, name)
                        if os.path.isdir(model_dir):
                            model_kwargs[param] = model_dir

                # table=False：表格模型与 paddlepaddle 2.6 存在加载兼容问题，
                # 表格区域按图片处理；recovery=True 启用阅读顺序恢复
                self._ocr_engine = PPStructure(
                    recovery=True,
                    table=False,
                    lang='ch',
                    show_log=False,
                    **model_kwargs
                )
                logger.info("PP-Structure引擎初始化完成")
            except ImportError as e:
                log(f"OCR 增强包不完整（缺少 paddle 依赖：{e}）")
                logger.info(f"PaddleOCR不可用（{e}），扫描版PDF将使用图片模式转换")
                logger.info("提示：安装 paddleocr 和 paddlepaddle 可启用OCR文字识别功能")
                return None
            except Exception as e:
                log(f"OCR 引擎初始化失败：{e}")
                logger.info(f"PP-Structure引擎初始化失败: {e}")
                logger.info("扫描版PDF将使用图片模式转换")
                return None
        return self._ocr_engine

    def _release_ocr_engine(self):
        """释放OCR引擎资源"""
        if self._ocr_engine is not None:
            del self._ocr_engine
            self._ocr_engine = None
            gc.collect()

    def _convert_scanned_pdf_as_images(
        self,
        pdf_path: str,
        output_path: str,
        start: int = 0,
        end: Optional[int] = None,
        progress_callback=None
    ) -> tuple[bool, str]:
        """
        扫描版PDF的降级转换（图片模式）

        当OCR不可用时，将每页渲染为图片插入Word文档。
        每页使用较高DPI渲染以保证清晰度。

        Args:
            pdf_path: PDF文件路径
            output_path: 输出Word文件路径
            start: 起始页码（从0开始）
            end: 结束页码
            progress_callback: 进度回调函数

        Returns:
            (是否成功, 消息/错误信息)
        """
        import fitz
        import shutil
        from docx import Document
        from docx.shared import Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        actual_end = min(end or total_pages, total_pages)
        pages_to_convert = actual_end - start

        logger.info(f"图片模式转换: 共{total_pages}页，转换第{start + 1}-{actual_end}页")

        word_doc = Document()

        temp_dir = tempfile.mkdtemp(prefix='pdf_img_')

        try:
            for page_idx in range(start, actual_end):
                if self._is_cancelled:
                    break

                page = doc[page_idx]
                current_page = page_idx - start + 1

                if progress_callback:
                    progress_callback(current_page, pages_to_convert)

                # 渲染页面为图片
                pix = page.get_pixmap(dpi=150)
                img_path = os.path.join(temp_dir, f'page_{page_idx}.png')
                pix.save(img_path)

                if page_idx > start:
                    word_doc.add_page_break()

                # 插入图片到Word
                para = word_doc.add_paragraph()
                para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = para.add_run()
                run.add_picture(img_path, width=Inches(6.0))

                # 清理临时图片
                try:
                    os.remove(img_path)
                except OSError:
                    pass

                logger.info(f"已处理第 {page_idx + 1}/{total_pages} 页")

            if self._is_cancelled:
                return False, "转换被用户中断"

            word_doc.save(output_path)

            if not os.path.exists(output_path):
                return False, "转换完成但输出文件不存在"

            file_size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"图片模式转换完成，文件大小: {file_size_kb:.1f}KB")
            return True, f"成功转换到: {output_path}"

        except Exception as e:
            error_msg = f"图片模式转换失败: {str(e)}"
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return False, error_msg

        finally:
            # 统一释放资源：取消/异常/正常路径都会执行
            try:
                doc.close()
            except Exception:
                pass
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ========== 扫描版PDF的OCR转换 ==========

    def _convert_scanned_pdf(
        self,
        pdf_path: str,
        output_path: str,
        start: int = 0,
        end: Optional[int] = None,
        progress_callback=None,
        log_callback=None
    ) -> tuple[bool, str]:
        """
        使用 PP-Structure 将扫描版PDF转换为Word文档

        对每一页：渲染为图片 → 版面分析（标题/正文/图片等区域）→ OCR识别
        → 阅读顺序恢复 → 官方 recovery 直出分层可编辑的 docx。

        如果PaddleOCR不可用，回退到图片模式（每页作为图片插入Word）。

        Args:
            pdf_path: PDF文件路径
            output_path: 输出Word文件路径
            start: 起始页码（从0开始）
            end: 结束页码
            progress_callback: 进度回调函数
            log_callback: 可选的界面日志回调（接收一个字符串）

        Returns:
            (是否成功, 消息/错误信息)
        """
        log = log_callback or (lambda m: None)
        engine = self._get_ocr_engine(log=log)

        if engine is None:
            # OCR不可用，回退到图片模式（降级原因已由 _get_ocr_engine 透传）
            log("未启用 OCR，改用图片模式转换扫描版 PDF（输出为图片，无可编辑文字）")
            logger.info("OCR不可用，使用图片模式转换扫描版PDF")
            return self._convert_scanned_pdf_as_images(
                pdf_path, output_path, start, end, progress_callback
            )
        log("已启用 OCR 文字识别（PP-Structure），开始逐页识别...")
        import fitz
        import shutil
        import numpy as np
        import cv2
        from paddleocr import save_structure_res
        from paddleocr.ppstructure.recovery.recovery_to_doc import (
            sorted_layout_boxes, convert_info_docx,
        )

        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        actual_end = min(end or total_pages, total_pages)
        pages_to_convert = actual_end - start

        logger.info(f"扫描版PDF，使用PP-Structure转换: 共{total_pages}页，转换第{start + 1}-{actual_end}页")

        # 中间产物（图片区域裁剪/docx）必须用 ASCII 临时目录：
        # cv2.imwrite 在 Windows 上无法写入含中文的路径（静默失败）
        temp_dir = tempfile.mkdtemp(prefix='pdf_ppstructure_')
        doc_name = 'ppstructure_result'
        zoom = 200 / 72  # 200 DPI

        try:
            all_res = []
            last_img = None
            for page_idx in range(start, actual_end):
                if self._is_cancelled:
                    break

                current_page = page_idx - start + 1
                if progress_callback:
                    progress_callback(current_page, pages_to_convert)

                logger.info(f"PP-Structure识别第 {page_idx + 1}/{total_pages} 页...")

                # 渲染页面为 BGR ndarray
                pix = doc[page_idx].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
                    pix.height, pix.width, pix.n
                )
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                else:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                # 版面分析 + OCR；img_idx 用于多页结果在 docx 中分页
                rel_idx = page_idx - start
                result = engine(img, img_idx=rel_idx)
                # 图片区域裁剪落盘，convert_info_docx 生成 docx 时需要读取
                save_structure_res(result, temp_dir, doc_name, img_idx=rel_idx)
                res = sorted_layout_boxes(result, img.shape[1])
                all_res += res
                last_img = img

            if self._is_cancelled:
                return False, "转换被用户中断"

            if not all_res:
                return False, "PP-Structure未识别出任何内容"

            # 生成 docx（写到 ASCII 临时目录），再移动到用户目标路径
            convert_info_docx(last_img, all_res, temp_dir, doc_name)
            temp_docx = os.path.join(temp_dir, f'{doc_name}_ocr.docx')
            if not os.path.exists(temp_docx):
                return False, "转换完成但输出文件不存在"
            shutil.move(temp_docx, output_path)

            file_size_kb = os.path.getsize(output_path) / 1024
            logger.info(f"PP-Structure转换完成，文件大小: {file_size_kb:.1f}KB")
            return True, f"成功转换到: {output_path}"

        except MemoryError:
            return False, "内存不足，OCR转换需要较多内存，请尝试转换较少页数"

        except Exception as e:
            error_msg = f"OCR转换失败: {str(e)}"
            logger.error(f"错误详情:\n{traceback.format_exc()}")
            return False, error_msg

        finally:
            # 统一释放资源：取消/异常/正常路径都会执行
            try:
                doc.close()
            except Exception:
                pass
            self._release_ocr_engine()
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ========== 主转换入口 ==========

    def convert(
        self, 
        pdf_path: str, 
        output_path: str,
        start: int = 0,
        end: Optional[int] = None,
        progress_callback=None,
        log_callback=None
    ) -> tuple[bool, str]:
        """
        将PDF转换为Word文档

        自动检测PDF类型：
        - 普通PDF（含可提取文字）：使用pdf2docx转换
        - 扫描版PDF（每页均为图片）：使用OCR识别文字后转换

        Args:
            pdf_path: PDF文件路径
            output_path: 输出Word文件路径
            start: 起始页码（从0开始）
            end: 结束页码（None表示到最后一页）
            progress_callback: 进度回调函数(page_no, total_pages)
            log_callback: 可选的界面日志回调（接收一个字符串），用于透传扫描版检测/OCR状态

        Returns:
            (是否成功, 消息/错误信息)
        """
        log = log_callback or (lambda m: None)
        try:
            self._is_cancelled = False

            if not os.path.exists(pdf_path):
                return False, f"PDF文件不存在: {pdf_path}"

            # 检查文件大小，警告大文件
            file_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
            if file_size_mb > 50:
                logger.info(f"警告: 文件较大 ({file_size_mb:.1f}MB)，转换可能需要较长时间")

            # 确保输出目录存在
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)

            # 检测是否为扫描版PDF
            is_scanned = self._is_scanned_pdf(pdf_path)

            if is_scanned:
                # 扫描版PDF：使用OCR转换
                log("检测到扫描版 PDF（页面无可提取文字层）")
                return self._convert_scanned_pdf(
                    pdf_path, output_path, start, end, progress_callback, log
                )

            # 普通PDF：使用pdf2docx转换（在独立子进程中执行，隔离底层C库崩溃）
            logger.info(f"开始转换: {pdf_path}")
            success, err_msg = self._run_pdf2docx_isolated(
                pdf_path, output_path, start, end
            )
            gc.collect()

            # 转换期间收到取消请求，丢弃结果
            if self._is_cancelled:
                return False, "转换被用户中断"

            if not success:
                return False, err_msg

            # 验证生成的文件
            if not os.path.exists(output_path):
                return False, "转换完成但输出文件不存在"

            if os.path.getsize(output_path) == 0:
                return False, "转换生成的文件为空"

            logger.info(f"转换完成，文件大小: {os.path.getsize(output_path) / 1024:.1f}KB")

            # 后处理：修复图片显示问题
            try:
                self._fix_images_in_docx(output_path)
            except Exception as e:
                logger.info(f"图片修复失败（不影响主文件）: {e}")

            return True, f"成功转换到: {output_path}"

        except MemoryError:
            if self.converter:
                try:
                    self.converter.close()
                except Exception:
                    pass
            self.converter = None
            gc.collect()
            return False, "内存不足，请尝试转换较小的PDF文件或关闭其他程序"

        except KeyboardInterrupt:
            if self.converter:
                try:
                    self.converter.close()
                except Exception:
                    pass
            self.converter = None
            return False, "转换被用户中断"

        except Exception as e:
            error_msg = f"转换失败: {str(e)}"
            logger.error(f"错误详情:\n{traceback.format_exc()}")

            if self.converter:
                try:
                    self.converter.close()
                except Exception:
                    pass
            self.converter = None
            gc.collect()

            return False, error_msg
    
    def _fix_images_in_docx(self, docx_path: str):
        """
        修复Word文档中的图片显示问题
        
        问题1：图片显示不全或显示为空白
        问题2：某些白色/透明图片遮挡了其他内容
        问题3：水印、分隔线等装饰性元素（几乎纯白色、内容极少）
        问题4：anchor类型浮动图片尺寸异常（如高度数千英寸），导致Word无法打开
        
        解决方案：
        1. 检测并删除异常尺寸的浮动图片（anchor类型）
        2. 检测并删除几乎纯白色的图片（水印/分隔线）
        3. 删除异常大的图片
        4. 调整正常图片的尺寸
        """
        try:
            from docx import Document
            from docx.shared import Inches, Emu
            from docx.oxml.ns import qn
            from PIL import Image
            import io
            
            doc = Document(docx_path)
            body = doc.element.body
            
            # ========== 第一步：处理anchor类型的浮动图片 ==========
            # anchor图片可能是pdf2docx生成的背景层/水印
            # 这些图片如果尺寸异常（如高度数千英寸），会导致Word无法打开
            self._fix_anchor_drawings(body, doc)
            
            # ========== 第二步：处理inline类型的图片 ==========
            # 直接收集待删图片的XML节点引用，避免与anchor图片的索引空间混淆
            shapes_to_remove = []
            
            for idx, shape in enumerate(doc.inline_shapes):
                try:
                    width_px = shape.width
                    height_px = shape.height
                    
                    is_blank_image = False
                    
                    try:
                        image_part = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
                        image_part_rid = image_part
                        image_part = doc.part.related_parts.get(image_part_rid)
                        
                        if image_part:
                            img = Image.open(io.BytesIO(image_part.blob))
                            img_rgb = img.convert('RGB')

                            # 缩略图分析：缩小到100x100后遍历，避免逐像素getpixel
                            small_img = img_rgb.resize((100, 100), Image.LANCZOS)
                            samples = list(small_img.getdata())
                            small_img.close()

                            if samples:
                                avg_r = sum(p[0] for p in samples) / len(samples)
                                avg_g = sum(p[1] for p in samples) / len(samples)
                                avg_b = sum(p[2] for p in samples) / len(samples)
                                
                                min_channel = min(avg_r, avg_g, avg_b)
                                max_channel = max(avg_r, avg_g, avg_b)
                                
                                if min_channel > 240 and (max_channel - min_channel) < 15:
                                    is_blank_image = True
                                    logger.info(f"图片 {idx}: 检测到几乎纯白色图片（水印/分隔线），已删除")
                            
                            img.close()
                            img_rgb.close()
                        
                    except Exception as e:
                        logger.info(f"分析图片 {idx} 时出错: {e}")
                    
                    if is_blank_image:
                        shapes_to_remove.append(shape._inline)
                        continue
                    
                    max_reasonable_size = Inches(8)
                    if width_px > max_reasonable_size or height_px > max_reasonable_size:
                        shapes_to_remove.append(shape._inline)
                        logger.info(f"图片 {idx}: 尺寸异常大，已删除")
                        continue
                    
                    if width_px > 0 and height_px > 0:
                        aspect_ratio = width_px / height_px
                        if aspect_ratio > 10 or aspect_ratio < 0.1:
                            shapes_to_remove.append(shape._inline)
                            logger.info(f"图片 {idx}: 宽高比异常（{aspect_ratio:.2f}），可能是分隔线，已删除")
                            continue
                    
                    max_width = Inches(6.5)
                    if shape.width > max_width:
                        aspect_ratio = shape.height / shape.width
                        shape.width = max_width
                        shape.height = max_width * aspect_ratio
                        
                except Exception as e:
                    logger.info(f"处理图片 {idx} 时出错: {e}")
                    continue
            
            if shapes_to_remove:
                logger.info(f"发现 {len(shapes_to_remove)} 个问题inline图片，正在清理...")
                self._remove_problematic_shapes(shapes_to_remove)
            
            doc.save(docx_path)
            
        except Exception as e:
            logger.info(f"图片修复警告: {e}")
    
    def _fix_anchor_drawings(self, body, doc=None):
        """
        处理anchor类型的浮动图片

        pdf2docx 会将PDF中的背景图层转为anchor类型的浮动图片（behindDoc=1），
        这些图片包括水印、页眉页脚装饰线、整页白色背景层等，会遮挡正常内容。

        处理策略：
        1. behindDoc=1 且内容为水印/背景 → 删除
        2. behindDoc=1 且有实质内容 → 改为 behindDoc=0
        3. 尺寸异常的巨型图片 → 删除
        """
        try:
            from docx.shared import Inches
            from docx.oxml.ns import qn

            ns_wp = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
            ns_a = 'http://schemas.openxmlformats.org/drawingml/2006/main'
            ns_r = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

            # 异常巨型图片阈值（正常页面最大尺寸）
            max_reasonable_width_emu = int(Inches(20))
            max_reasonable_height_emu = int(Inches(30))

            # 查找所有 drawing 元素（使用 .// 递归搜索嵌套元素）
            drawings = body.findall('.//' + qn('w:drawing'))
            removed_count = 0
            behind_removed_count = 0
            behind_preserved_count = 0

            for drawing in drawings:
                try:
                    # 检查是否有anchor子元素
                    anchor = drawing.find(qn('wp:anchor'))
                    if anchor is None:
                        anchor = drawing.find('{' + ns_wp + '}anchor')

                    if anchor is None:
                        continue

                    # 检查是否是背景层（behindDoc=true）
                    behind_doc = anchor.get('behindDoc', 'false')
                    is_behind_doc = behind_doc == '1' or behind_doc.lower() == 'true'

                    # 获取anchor的extent（尺寸）
                    extent = anchor.find(qn('wp:extent'))
                    if extent is None:
                        extent = anchor.find('{' + ns_wp + '}extent')

                    if extent is not None:
                        cx = int(extent.get('cx', '0'))
                        cy = int(extent.get('cy', '0'))
                        is_huge = cx > max_reasonable_width_emu or cy > max_reasonable_height_emu
                    else:
                        cx = 0
                        cy = 0
                        is_huge = False

                    should_remove = False

                    if is_huge:
                        # 异常巨型浮动图片，无论是否behindDoc都删除
                        cx_inches = cx / 914400
                        cy_inches = cy / 914400
                        logger.info(f"删除异常巨型浮动图片: {cx_inches:.1f}x{cy_inches:.1f} 英寸, behindDoc={behind_doc}")
                        should_remove = True
                    elif is_behind_doc:
                        # behindDoc=1的浮动图片需要分析内容，判断是水印还是有用图片
                        is_watermark = self._is_watermark_image(drawing, doc, ns_a, ns_r)
                        if is_watermark:
                            width_inches = cx / 914400
                            height_inches = cy / 914400
                            logger.info(f"删除背景浮动图片(水印): {width_inches:.1f}x{height_inches:.1f} 英寸")
                            should_remove = True
                            behind_removed_count += 1
                        else:
                            # 有实质内容的behindDoc图片：改为behindDoc=0使其正常显示
                            anchor.set('behindDoc', '0')
                            behind_preserved_count += 1

                    if should_remove:
                        parent = drawing.getparent()
                        if parent is not None:
                            parent.remove(drawing)
                            removed_count += 1

                except Exception as e:
                    logger.info(f"处理anchor图片时出错: {e}")
                    continue

            if removed_count > 0:
                logger.info(f"共删除 {removed_count} 个浮动图片（其中背景水印 {behind_removed_count} 个）")
            if behind_preserved_count > 0:
                logger.info(f"保留 {behind_preserved_count} 个含内容的背景浮动图片")

        except Exception as e:
            logger.info(f"修复浮动图片时出错: {e}")

    def _is_watermark_image(self, drawing, doc, ns_a, ns_r):
        """
        判断behindDoc浮动图片是否为水印/背景
        
        通过分析图片内容来判断：
        - 极小文件（<1KB）：装饰线，是水印
        - 纯色/几乎无内容图片：背景层，是水印
        - 有实质内容（深色/中等亮度像素占比高）：不是水印，应保留
        
        Args:
            drawing: XML drawing 元素
            doc: Document 对象，用于获取图片数据
            ns_a: drawingml 主命名空间
            ns_r: 关系命名空间
            
        Returns:
            True 表示是水印应删除，False 表示有内容应保留
        """
        try:
            from docx.oxml.ns import qn
            from PIL import Image
            import io

            # 查找图片引用
            blip = drawing.find('.//' + qn('a:blip'))
            if blip is None:
                blip = drawing.find('.//{' + ns_a + '}blip')

            if blip is None:
                # 无图片数据，视为水印
                return True

            embed = blip.get(qn('r:embed'))
            if embed is None:
                embed = blip.get('{' + ns_r + '}embed')

            if not embed or doc is None:
                # 无法获取图片，保守处理：不删除
                return False

            image_part = doc.part.related_parts.get(embed)
            if image_part is None:
                return False

            blob_size = len(image_part.blob)

            # 极小文件（<1KB），通常是装饰线/占位符
            if blob_size < 1000:
                return True

            # 分析图片像素内容
            img = Image.open(io.BytesIO(image_part.blob))
            img_rgb = img.convert('RGB')

            # 缩略图分析：缩小到100x100后遍历，避免逐像素getpixel
            small_img = img_rgb.resize((100, 100), Image.LANCZOS)
            pixels = list(small_img.getdata())
            small_img.close()
            img.close()
            img_rgb.close()

            total_samples = len(pixels)
            dark_pixels = sum(1 for p in pixels if (p[0] + p[1] + p[2]) / 3 < 128)
            mid_pixels = sum(1 for p in pixels if 128 <= (p[0] + p[1] + p[2]) / 3 < 220)

            if total_samples == 0:
                return True

            dark_ratio = dark_pixels / total_samples
            mid_ratio = mid_pixels / total_samples

            # 判断逻辑：
            # 深色像素 >= 3% 或中等亮度像素 >= 10% → 有实质内容，不是水印
            # 否则 → 纯背景/水印
            is_watermark = dark_ratio < 0.03 and mid_ratio < 0.10

            return is_watermark

        except Exception:
            # 分析出错时保守处理：不删除
            return False
    
    def _remove_problematic_shapes(self, inline_elements):
        """
        从文档中删除指定的inline图片
        
        直接基于inline shape的XML节点删除其所在的w:drawing元素，
        避免使用findall索引（会与anchor图片混在同一列表导致错位误删）
        """
        try:
            from docx.oxml.ns import qn
            
            for inline_elem in inline_elements:
                # inline 元素的父节点即 w:drawing
                drawing = inline_elem.getparent()
                if drawing is None or drawing.tag != qn('w:drawing'):
                    continue
                parent = drawing.getparent()
                if parent is not None:
                    parent.remove(drawing)
                        
        except Exception as e:
            logger.info(f"删除问题图片时出错: {e}")
    
    def _run_pdf2docx_isolated(self, pdf_path, output_path, start, end):
        """
        在独立子进程中运行 pdf2docx 转换，隔离底层C库崩溃。

        Returns:
            (是否成功, 错误信息)
        """
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        proc = ctx.Process(
            target=_pdf2docx_worker,
            args=(pdf_path, output_path, start, end, result_queue),
        )
        self._process = proc
        proc.start()
        proc.join()
        self._process = None

        # 被取消（子进程已被 terminate）
        if self._is_cancelled:
            return False, "转换被用户中断"

        # 子进程异常退出（exitcode 非0/负值表示原生崩溃或被信号终止）
        if proc.exitcode != 0:
            logger.error(f"pdf2docx子进程异常退出: exitcode={proc.exitcode}")
            return False, "该PDF触发底层解析库崩溃，无法转换（文档结构复杂或不兼容）"

        # 读取子进程返回的结果
        try:
            return result_queue.get_nowait()
        except Exception:
            # 队列为空但进程正常退出，回退到检查输出文件
            return os.path.exists(output_path), "转换结果未知"

    def cancel(self):
        """
        取消转换（协作式）

        设置取消标志；若 pdf2docx 子进程正在运行则直接终止它。
        禁止跨线程关闭主进程内的 C 层对象，避免数据竞争导致崩溃。
        """
        self._is_cancelled = True
        proc = self._process
        if proc is not None and proc.is_alive():
            try:
                proc.terminate()
            except Exception:
                pass
