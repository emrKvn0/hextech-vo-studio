#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
⚡ LoL Voice & Media Studio - Modular HTML Assembler / Builder
Birleştirici: web/index.template.html içindeki modüler parçaları okuyarak
yüksek performanslı ve eksiksiz web/index.html dosyasını derler.
"""

import os
import re
import sys

# Ensure UTF-8 stdout on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
WEB_DIR = os.path.join(ROOT_DIR, "web")
TEMPLATE_PATH = os.path.join(WEB_DIR, "index.template.html")
OUTPUT_PATH = os.path.join(WEB_DIR, "index.html")

INCLUDE_PATTERN = re.compile(r'<!--\s*@include\s+["\']([^"\']+)["\']\s*-->')

_last_mtimes = {}
_cached_html = None


def get_all_template_files(web_dir=None):
    """Şablon ve tüm alt include dosyalarının listesini döner."""
    if web_dir is None:
        web_dir = WEB_DIR
    template_path = os.path.join(web_dir, "index.template.html")
    files = [template_path]

    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
            for match in INCLUDE_PATTERN.finditer(content):
                rel_path = match.group(1)
                full_path = os.path.join(web_dir, rel_path)
                files.append(full_path)
        except Exception:
            pass
    return files


def has_changes(web_dir=None):
    """Dosyalarda değişiklik olup olmadığını kontrol eder (Hot-reload / In-memory cache)."""
    global _last_mtimes
    files = get_all_template_files(web_dir)
    changed = False
    for fp in files:
        if os.path.exists(fp):
            mtime = os.path.getmtime(fp)
            if _last_mtimes.get(fp) != mtime:
                _last_mtimes[fp] = mtime
                changed = True
        else:
            if fp in _last_mtimes:
                del _last_mtimes[fp]
                changed = True
    return changed


def build_html_content(web_dir=None):
    """
    web/index.template.html ve ilişkili include parçalarını bellek içinde birleştirir.
    Bellek içi önbellekleme (in-memory caching) ile 0 ms gecikmeyle çalışır.
    """
    global _cached_html
    if web_dir is None:
        web_dir = WEB_DIR

    template_file = os.path.join(web_dir, "index.template.html")
    if not os.path.exists(template_file):
        # Eğer şablon dosyası yoksa mevcut index.html'i oku
        index_file = os.path.join(web_dir, "index.html")
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                return f.read()
        return "<html><body><h1>index.template.html bulunamadı</h1></body></html>"

    # Önbellek kontrolü
    if _cached_html is not None and not has_changes(web_dir):
        return _cached_html

    with open(template_file, 'r', encoding='utf-8') as f:
        template_content = f.read()

    def replace_include(match):
        rel_path = match.group(1)
        full_path = os.path.join(web_dir, rel_path)
        if not os.path.exists(full_path):
            print(f"⚠️ [Build HTML] Uyarı: Parça dosya bulunamadı: {full_path}")
            return f"<!-- MISSING INCLUDE: {rel_path} -->"
        try:
            with open(full_path, 'r', encoding='utf-8') as pf:
                return pf.read()
        except Exception as e:
            print(f"❌ [Build HTML] Hata ({rel_path}): {e}")
            return f"<!-- ERROR INCLUDING {rel_path}: {e} -->"

    built_content = INCLUDE_PATTERN.sub(replace_include, template_content)
    _cached_html = built_content
    return built_content


def build_html(web_dir=None, output_path=None):
    """
    Modüler HTML'i derler ve diske (web/index.html) yazar.
    """
    if web_dir is None:
        web_dir = WEB_DIR
    if output_path is None:
        output_path = os.path.join(web_dir, "index.html")

    html_content = build_html_content(web_dir)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"✅ [Build HTML] Modüler index.html başarıyla derlendi: {output_path} ({len(html_content):,} bayt)")
    return output_path


if __name__ == "__main__":
    build_html()
