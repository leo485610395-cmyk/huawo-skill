#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
huawo-website-skill · 质量检查脚本

检查 AI 生成的 HTML 是否符合交付标准:
1. 没有残留的占位符方括号(用户填了的应该都替换)
2. UTF-8 编码
3. 基本结构完整(<html>/<head>/<body>)
4. CSS 没被明显破坏(对照原模板)

用法:
    python check-quality.py 生成的网站.html [--template 原模板.html]

退出码:
    0 = 全过
    1 = 有问题(详细见输出)
"""

import sys
import re
import argparse
from pathlib import Path


def strip_html_comments(content: str) -> str:
    """移除 HTML 注释 <!-- ... -->，避免注释里的占位符示例干扰检查"""
    return re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)


def check_placeholders(content: str) -> list:
    """检查未替换的占位符(先剥离 HTML 注释,避免误报)。

    策略:匹配所有 [xxx] 形式的占位符,但排除:
    - [IMG: xxx] 图片占位(正常的)
    - 辅助描述占位(纯描述格式,如 [ 黑白 / 低饱和 ]、[ 4:5 竖版 ])
      这类以空格开头/结尾,或以方括号内的纯描述格式存在,不算待替换字段

    这样能覆盖模板里所有占位符类型,包括:
    - 短字段:[你的名字] [年份] [材料/形式]
    - 长描述:[简单介绍一下你的背景:...]
    - 英文:[YOUR NAME] [YOUR CITY]
    - 嵌套数字:[你的作品名 1] [主题标签 2]
    """
    issues = []
    # 只检查 body 内的占位符(剥离注释 + head 里的 title/description)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', content, re.DOTALL)
    if not body_match:
        return ["❌ 找不到 <body> 标签,无法检查占位符"]
    body = strip_html_comments(body_match.group(1))

    # 匹配所有 [xxx],除了:
    # - [IMG: ...] / [IMG:...] 图片占位
    # - [ xxx ] 这种带前后空格的辅助描述(如 [ 黑白 / 低饱和 ])
    # - [ 纯文字 / 纯文字 ] 这种图片尺寸/格式描述(以 / 分隔的纯描述)
    # 用迭代 + 手动过滤,比纯正则更可靠
    all_brackets = re.findall(r'\[([^\[\]]+)\]', body)

    missed = []
    for match in all_brackets:
        # 跳过图片占位
        if match.startswith('IMG:') or match.startswith('IMG :'):
            continue
        # 跳过辅助描述(以空格开头或结尾,通常是 IMG 框旁边的格式说明)
        if match.startswith(' ') or match.endswith(' '):
            continue
        # 跳过纯英文格式描述(如 "4:3 横版"、"4:5 竖版")
        if re.match(r'^\d+:\d+\s', match):
            continue
        # 这是待替换的占位符
        missed.append(match)

    if missed:
        # 去重显示,最多展示 8 个
        unique = list(dict.fromkeys(missed))
        preview = unique[:8]
        issues.append(
            f"❌ 发现 {len(missed)} 处未替换的占位符(去重后 {len(unique)} 种):"
            f"{preview}"
        )
    return issues


def check_encoding(content: str) -> list:
    """检查 UTF-8 编码声明"""
    issues = []
    if 'charset="UTF-8"' not in content and "charset='UTF-8'" not in content:
        issues.append("❌ 没有 <meta charset=\"UTF-8\">,中文可能乱码")
    return issues


def check_basic_structure(content: str) -> list:
    """检查基本 HTML 结构"""
    issues = []
    required_tags = ['<!DOCTYPE html>', '<html', '<head>', '<body>', '</html>']
    for tag in required_tags:
        if tag not in content:
            issues.append(f"❌ 缺少必要的 HTML 标签:{tag}")
    return issues


def check_broken_brackets(content: str) -> list:
    """检查破损的方括号(只有一半的)"""
    issues = []
    # 找 [xxx 后面没有跟着 ] 的
    # 简化检查:统计 [ 和 ] 数量,应该相等
    open_count = content.count('[')
    close_count = content.count(']')
    if open_count != close_count:
        issues.append(
            f"⚠️ 方括号数量不匹配:[ 有 {open_count} 个,] 有 {close_count} 个,可能有破损"
        )
    return issues


def check_css_intact(generated: str, template: str) -> list:
    """对照原模板,检查 CSS 是否被破坏。
    先剥离 HTML 注释,避免注释里的字面 <style> 字符串干扰提取。
    """
    issues = []
    try:
        # 先剥离注释
        def clean(html: str) -> str:
            return strip_html_comments(html)

        # 提取 <style> 标签内容(只在剥离注释之后做)
        def extract_style(html):
            match = re.search(r'<style[^>]*>(.*?)</style>', html, re.DOTALL)
            return match.group(1) if match else ""

        gen_css = extract_style(clean(generated))
        tpl_css = extract_style(clean(template))

        if not gen_css:
            issues.append("❌ 生成的 HTML 里没有 <style> 标签")
            return issues

        if not tpl_css:
            issues.append("⚠️ 模板里没有 <style>,无法对照")
            return issues

        # 严格字节级对比(最直接的检测)
        if gen_css == tpl_css:
            pass  # 完全一致,通过
        else:
            # 不一致,细查 :root 变量(关键设计 token)
            def extract_root(css):
                match = re.search(r':root\s*\{([^}]+)\}', css)
                return match.group(1) if match else ""

            gen_root = extract_root(gen_css).strip()
            tpl_root = extract_root(tpl_css).strip()

            if gen_root != tpl_root:
                issues.append("⚠️ :root CSS 变量跟模板不一致,可能颜色/字号被改了")
            else:
                # :root 一致但其他 CSS 不一致
                issues.append(
                    f"⚠️ CSS 跟模板不完全一致(模板 {len(tpl_css)} 字节,"
                    f"生成 {len(gen_css)} 字节)。:root 变量一致,但其他规则有改动"
                )

    except Exception as e:
        issues.append(f"⚠️ CSS 对照检查失败:{e}")
    return issues


def main():
    parser = argparse.ArgumentParser(description='检查生成的网站 HTML 质量')
    parser.add_argument('file', help='生成的网站 HTML 文件路径')
    parser.add_argument('--template', help='原模板 HTML 路径(用于对照 CSS)', default=None)
    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"❌ 文件不存在:{file_path}")
        sys.exit(1)

    # 读取文件
    try:
        content = file_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        print(f"❌ 文件不是 UTF-8 编码")
        sys.exit(1)

    print(f"🔍 检查 {file_path.name} ...\n")

    all_issues = []

    # 基本检查
    all_issues.extend(check_placeholders(content))
    all_issues.extend(check_encoding(content))
    all_issues.extend(check_basic_structure(content))
    all_issues.extend(check_broken_brackets(content))

    # 如果给了模板,对照 CSS
    if args.template:
        template_path = Path(args.template)
        if template_path.exists():
            template_content = template_path.read_text(encoding='utf-8')
            all_issues.extend(check_css_intact(content, template_content))
        else:
            print(f"⚠️ 模板文件不存在:{template_path}")

    # 输出结果
    if not all_issues:
        print("✅ 自动检查全过!\n")
        print("⚠️ 但自动检查不能替代视觉检查。")
        print("⚠️ 务必在浏览器里打开文件,检查:")
        print("   - 桌面端布局正常")
        print("   - 手机端不崩(用 F12 切换手机视图)")
        print("   - 颜色对比够,字号合适")
        sys.exit(0)
    else:
        print(f"❌ 发现 {len(all_issues)} 个问题:\n")
        for issue in all_issues:
            print(f"  {issue}")
        print("\n修复后再交付。")
        sys.exit(1)


if __name__ == '__main__':
    main()
