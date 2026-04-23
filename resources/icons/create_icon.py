"""
生成黑色猫主题的应用程序图标
"""
from PIL import Image, ImageDraw
import os


def create_cat_icon():
    """创建黑色猫图标"""
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # 背景圆形 - 深蓝色调
    bg_color = (30, 35, 50, 255)  # 深蓝灰色背景
    center = size // 2
    radius = size // 2 - 10
    draw.ellipse([center - radius, center - radius, center + radius, center + radius], fill=bg_color)
    
    # 猫的轮廓颜色
    cat_color = (20, 20, 25, 255)  # 近黑色
    highlight_color = (60, 65, 80, 255)  # 高光色
    
    # 猫头（圆形）
    head_center = (center, center + 20)
    head_radius = 70
    draw.ellipse([
        head_center[0] - head_radius, head_center[1] - head_radius,
        head_center[0] + head_radius, head_center[1] + head_radius
    ], fill=cat_color)
    
    # 猫耳朵（三角形）
    # 左耳
    left_ear = [
        (head_center[0] - 50, head_center[1] - 40),  # 底部左侧
        (head_center[0] - 70, head_center[1] - 90),  # 顶部
        (head_center[0] - 20, head_center[1] - 60),  # 底部右侧
    ]
    draw.polygon(left_ear, fill=cat_color)
    
    # 右耳
    right_ear = [
        (head_center[0] + 50, head_center[1] - 40),  # 底部右侧
        (head_center[0] + 70, head_center[1] - 90),  # 顶部
        (head_center[0] + 20, head_center[1] - 60),  # 底部左侧
    ]
    draw.polygon(right_ear, fill=cat_color)
    
    # 眼睛（发光效果）
    eye_color = (100, 200, 255, 255)  # 亮蓝色眼睛
    eye_glow = (150, 220, 255, 150)  # 眼睛发光
    
    # 左眼
    left_eye_center = (head_center[0] - 25, head_center[1] - 10)
    draw.ellipse([
        left_eye_center[0] - 12, left_eye_center[1] - 15,
        left_eye_center[0] + 12, left_eye_center[1] + 15
    ], fill=eye_glow)
    draw.ellipse([
        left_eye_center[0] - 8, left_eye_center[1] - 12,
        left_eye_center[0] + 8, left_eye_center[1] + 12
    ], fill=eye_color)
    
    # 右眼
    right_eye_center = (head_center[0] + 25, head_center[1] - 10)
    draw.ellipse([
        right_eye_center[0] - 12, right_eye_center[1] - 15,
        right_eye_center[0] + 12, right_eye_center[1] + 15
    ], fill=eye_glow)
    draw.ellipse([
        right_eye_center[0] - 8, right_eye_center[1] - 12,
        right_eye_center[0] + 8, right_eye_center[1] + 12
    ], fill=eye_color)
    
    # 瞳孔（垂直缝状）
    pupil_color = (10, 15, 25, 255)
    draw.ellipse([
        left_eye_center[0] - 3, left_eye_center[1] - 8,
        left_eye_center[0] + 3, left_eye_center[1] + 8
    ], fill=pupil_color)
    draw.ellipse([
        right_eye_center[0] - 3, right_eye_center[1] - 8,
        right_eye_center[0] + 3, right_eye_center[1] + 8
    ], fill=pupil_color)
    
    # 鼻子
    nose_color = (255, 150, 180, 255)  # 粉色鼻子
    nose_center = (head_center[0], head_center[1] + 15)
    draw.polygon([
        (nose_center[0], nose_center[1] - 5),
        (nose_center[0] - 6, nose_center[1] + 5),
        (nose_center[0] + 6, nose_center[1] + 5),
    ], fill=nose_color)
    
    # 胡须
    whisker_color = (80, 85, 100, 200)
    # 左侧胡须
    draw.line([(head_center[0] - 50, head_center[1] + 10), (head_center[0] - 80, head_center[1] + 5)], fill=whisker_color, width=2)
    draw.line([(head_center[0] - 50, head_center[1] + 20), (head_center[0] - 80, head_center[1] + 25)], fill=whisker_color, width=2)
    # 右侧胡须
    draw.line([(head_center[0] + 50, head_center[1] + 10), (head_center[0] + 80, head_center[1] + 5)], fill=whisker_color, width=2)
    draw.line([(head_center[0] + 50, head_center[1] + 20), (head_center[0] + 80, head_center[1] + 25)], fill=whisker_color, width=2)
    
    return img


def save_icon():
    """保存为ICO格式"""
    # 确保目录存在
    icon_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(icon_dir, exist_ok=True)
    
    # 创建图标
    img = create_cat_icon()
    
    # 生成多个尺寸用于ICO文件
    sizes = [256, 128, 64, 48, 32, 16]
    icons = []
    
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # 保存为ICO
    ico_path = os.path.join(icon_dir, 'app.ico')
    icons[0].save(ico_path, format='ICO', sizes=[(s, s) for s in sizes])
    
    # 同时保存一个PNG版本供预览
    png_path = os.path.join(icon_dir, 'app.png')
    img.save(png_path, 'PNG')
    
    print(f"图标已生成:")
    print(f"  ICO: {ico_path}")
    print(f"  PNG: {png_path}")
    
    return ico_path


if __name__ == '__main__':
    save_icon()
