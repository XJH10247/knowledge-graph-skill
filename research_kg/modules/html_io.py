"""PyVis / HTML 产物写出工具。"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def write_pyvis_html(net, output_path: str) -> str:
    """以 UTF-8 写出 PyVis HTML。

    Windows 上默认编码常为 cp1252，内联的 vis-network JS 会触发
    ``UnicodeEncodeError: 'charmap' codec can't encode characters``。
    这里优先走 ``generate_html`` 并显式 UTF-8 落盘，避免依赖系统编码。
    """
    html = None
    try:
        html = net.generate_html()
    except Exception as e:  # noqa: BLE001 — 兼容缺少 generate_html 的旧版 pyvis
        logger.debug("net.generate_html() unavailable, falling back to write_html: %s", e)

    if html is not None:
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(html)
        return output_path

    try:
        net.write_html(output_path, open_browser=False, notebook=False)
    except Exception as e:
        logger.warning(f"Failed to write HTML with browser option: {e}")
        net.write_html(output_path)
    return output_path
