import os
import re
import logging
import base64
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import pdfplumber
from PIL import Image
import io

logger = logging.getLogger(__name__)


class PDFToMarkdownConverter:
    def __init__(self):
        self.pdf_file: Optional[pdfplumber.PDF] = None
    
    def convert(
        self, 
        pdf_path: str, 
        output_folder: str,
        base_name: str = None
    ) -> tuple[bool, str]:
        """
        将PDF转换为Markdown文档（文件夹结构）
        
        Args:
            pdf_path: PDF文件路径
            output_folder: 输出文件夹路径（如：output/文件名/）
            base_name: 基础文件名（用于生成index.md）
            
        Returns:
            (是否成功, 消息/错误信息)
        """
        try:
            if not os.path.exists(pdf_path):
                return False, f"PDF文件不存在: {pdf_path}"
            
            # 确保输出文件夹存在
            output_path = Path(output_folder)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # 创建assets子文件夹存放图片
            assets_dir = output_path / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成index.md路径
            if base_name is None:
                base_name = Path(pdf_path).stem
            md_file_path = output_path / "index.md"
            
            markdown_content = []
            image_count = 0
            
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 提取文本
                    text = page.extract_text()
                    if text:
                        # 转换文本为Markdown格式
                        md_text = self._convert_text_to_markdown(text, page_num)
                        markdown_content.append(md_text)
                    
                    # 提取表格
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 0:
                            md_table = self._convert_table_to_markdown(table)
                            markdown_content.append(md_table)
                    
                    # 提取并保存图片
                    try:
                        images = page.images
                        for img_idx, img in enumerate(images):
                            image_count += 1
                            # 保存图片到assets文件夹
                            img_filename = f"image_{page_num}_{img_idx + 1}.png"
                            img_path = assets_dir / img_filename
                            
                            # 尝试提取并保存图片
                            if self._save_image_from_pdf(page, img, str(img_path)):
                                # 生成相对路径的Markdown图片引用
                                rel_path = f"assets/{img_filename}"
                                img_markdown = f"\n![图片_{image_count}]({rel_path})\n"
                                markdown_content.append(img_markdown)
                    except Exception as e:
                        # 图片提取失败不影响主流程
                        logger.info(f"提取第{page_num}页图片时出错: {e}")
                        continue
                    
                    # 分页符
                    markdown_content.append("\n---\n")
            
            # 写入index.md文件
            full_content = "\n".join(markdown_content)
            with open(md_file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            return True, f"成功转换到: {output_folder}"
            
        except Exception as e:
            return False, f"转换失败: {str(e)}"
    
    def _save_image_from_pdf(self, page, img_dict, output_path: str) -> bool:
        """
        从PDF页面提取并保存图片
        
        Args:
            page: pdfplumber页面对象
            img_dict: 图片字典信息
            output_path: 输出图片路径
            
        Returns:
            是否成功保存
        """
        try:
            # 尝试使用pdfplumber提取图片
            # 注意：这需要PDF中包含可提取的图片数据
            
            # 获取图片的边界框
            bbox = (img_dict['x0'], img_dict['top'], img_dict['x1'], img_dict['bottom'])
            
            # 裁剪页面到图片区域
            cropped = page.crop(bbox)
            
            # 将裁剪区域转换为图片
            try:
                # 尝试使用to_image方法
                im = cropped.to_image(resolution=150)
                im.save(output_path, format="PNG")
                return True
            except:
                # 如果失败，尝试直接截图
                pass
            
            return False
            
        except Exception as e:
            logger.info(f"保存图片失败: {e}")
            return False
    
    def _convert_text_to_markdown(self, text: str, page_num: int) -> str:
        """将普通文本转换为Markdown格式"""
        lines = text.split('\n')
        md_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # 检测标题（根据字体大小、位置等启发式规则）
            # 这里简化处理：假设较短的行可能是标题
            if len(line) < 50 and line and not line.endswith('.') and not line.endswith('。'):
                if len(line) < 20:
                    md_lines.append(f"## {line}")
                else:
                    md_lines.append(f"### {line}")
            else:
                md_lines.append(line)
        
        return '\n\n'.join(md_lines)
    
    def _convert_table_to_markdown(self, table: List[List]) -> str:
        """将表格转换为Markdown格式"""
        if not table or len(table) == 0:
            return ""
        
        md_lines = []
        
        # 表头
        header = table[0]
        md_lines.append("| " + " | ".join(str(cell or "").strip() for cell in header) + " |")
        
        # 分隔符
        md_lines.append("| " + " | ".join("---" for _ in header) + " |")
        
        # 数据行
        for row in table[1:]:
            md_lines.append("| " + " | ".join(str(cell or "").strip() for cell in row) + " |")
        
        return "\n".join(md_lines)
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        # 移除控制字符
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        return text.strip()
    
    def get_pdf_info(self, pdf_path: str) -> Dict:
        """获取PDF基本信息"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                info = {
                    'page_count': len(pdf.pages),
                    'metadata': pdf.metadata or {}
                }
                return info
        except Exception as e:
            return {'error': str(e)}
