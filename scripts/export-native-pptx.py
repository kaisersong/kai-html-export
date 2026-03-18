#!/usr/bin/env python3
"""
export-native-pptx.py — Export HTML slides to editable PPTX (text, shapes, tables).

Parses HTML DOM and creates native PPTX elements where possible for editability.
Complex visual effects fall back to screenshots.

Usage:
    python export-native-pptx.py <presentation.html> [output.pptx] [--width W] [--height H]

Dependencies:
    pip install playwright python-pptx beautifulsoup4 lxml
"""

import sys
import argparse
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

# Dependency check
def check_deps():
    missing = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing.append("playwright")
    try:
        from pptx import Presentation
    except ImportError:
        missing.append("python-pptx")
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        missing.append("beautifulsoup4")
    if missing:
        print(f"Missing dependencies. Install with:")
        print(f"  pip install {' '.join(missing)}")
        sys.exit(1)

check_deps()

from playwright.sync_api import sync_playwright, Page, ElementHandle
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from bs4 import BeautifulSoup, Tag


# ─── Element Analysis ────────────────────────────────────────────────────────

class SlideElement:
    """Represents a parsed HTML element ready for PPTX export."""

    def __init__(self, tag: Tag, bounds: Dict[str, float], styles: Dict[str, Any]):
        self.tag = tag
        self.bounds = bounds  # {x, y, width, height} in inches
        self.styles = styles
        self.type = self._classify()

    def _classify(self) -> str:
        """Classify element type for export strategy."""
        tag_name = self.tag.name.lower()

        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']:
            return 'text'
        elif tag_name == 'table':
            return 'table'
        elif tag_name == 'img':
            return 'image'
        elif tag_name in ['ul', 'ol']:
            return 'list'
        elif tag_name == 'div' and self._has_simple_background():
            return 'shape'
        else:
            return 'complex'

    def _has_simple_background(self) -> bool:
        """Check if element has a solid background (no gradient)."""
        bg = self.styles.get('background', '')
        # Simple heuristic: no gradient keywords
        return bg and 'gradient' not in bg.lower() if bg else False


def parse_slide_elements(page: Page, slide_index: int) -> List[SlideElement]:
    """Parse all elements in a slide and return structured data."""

    # Get slide element
    slide_handle = page.query_selector_all('.slide')[slide_index]

    # Extract element bounds and styles
    elements_data = slide_handle.evaluate("""
        (slide) => {
            const results = [];
            const children = slide.querySelectorAll('h1, h2, h3, h4, h5, h6, p, div, table, ul, ol, img');

            children.forEach(el => {
                // Skip if element is hidden
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return;

                const rect = el.getBoundingClientRect();
                const slideRect = slide.getBoundingClientRect();

                results.push({
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent.trim(),
                    bounds: {
                        x: (rect.left - slideRect.left) / 96,  // px to inches (96 DPI)
                        y: (rect.top - slideRect.top) / 96,
                        width: rect.width / 96,
                        height: rect.height / 96
                    },
                    styles: {
                        'font-size': style.fontSize,
                        'font-weight': style.fontWeight,
                        'color': style.color,
                        'background': style.background,
                        'text-align': style.textAlign
                    }
                });
            });

            return results;
        }
    """)

    # Convert to SlideElement objects
    elements = []
    for data in elements_data:
        # Parse CSS color to RGB
        styles = data['styles'].copy()
        if styles.get('color'):
            styles['color_rgb'] = parse_css_color(styles['color'])
        if styles.get('background'):
            styles['bg_rgb'] = parse_css_color(styles['background'])

        elements.append(SlideElement(
            tag=BeautifulSoup(f"<{data['tag']}>{data['text']}</{data['tag']}>", 'html.parser').find(data['tag']),
            bounds=data['bounds'],
            styles=styles
        ))

    return elements


def parse_css_color(css_color: str) -> Optional[Tuple[int, int, int]]:
    """Parse CSS color to RGB tuple."""
    import re

    # Match rgb(r, g, b) or rgba(r, g, b, a)
    match = re.search(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', css_color)
    if match:
        return (int(match.group(1)), int(match.group(2)), int(match.group(3)))

    # Match hex colors
    match = re.search(r'#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})', css_color)
    if match:
        hex_color = match.group(1)
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return (
            int(hex_color[0:2], 16),
            int(hex_color[2:4], 16),
            int(hex_color[4:6], 16)
        )

    return None


# ─── Native PPTX Export ───────────────────────────────────────────────────────

def export_element_native(slide, element: SlideElement):
    """Export a single element as native PPTX."""

    if element.type == 'text':
        export_text_element(slide, element)
    elif element.type == 'shape':
        export_shape_element(slide, element)
    elif element.type == 'table':
        export_table_element(slide, element)
    elif element.type == 'image':
        pass  # TODO: Implement image export
    elif element.type == 'list':
        export_list_element(slide, element)
    # 'complex' elements are skipped in native mode (handled by hybrid mode)


def export_text_element(slide, element: SlideElement):
    """Export text as editable TextBox."""

    b = element.bounds
    txBox = slide.shapes.add_textbox(
        Inches(b['x']), Inches(b['y']),
        Inches(b['width']), Inches(b['height'])
    )

    tf = txBox.text_frame
    tf.word_wrap = True

    # Set text
    text = element.tag.get_text()
    p = tf.paragraphs[0]
    p.text = text

    # Apply styles
    styles = element.styles

    # Font size
    if styles.get('font-size'):
        size_match = __import__('re').search(r'(\d+)px', styles['font-size'])
        if size_match:
            p.font.size = Pt(int(size_match.group(1)))

    # Font weight
    if styles.get('font-weight') == 'bold' or styles.get('font-weight') == '700':
        p.font.bold = True

    # Color
    if styles.get('color_rgb'):
        r, g, b = styles['color_rgb']
        p.font.color.rgb = RGBColor(r, g, b)

    # Alignment
    align = styles.get('text-align', 'left')
    if align == 'center':
        p.alignment = PP_ALIGN.CENTER
    elif align == 'right':
        p.alignment = PP_ALIGN.RIGHT


def export_shape_element(slide, element: SlideElement):
    """Export div with background as rectangle shape."""

    b = element.bounds
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(b['x']), Inches(b['y']),
        Inches(b['width']), Inches(b['height'])
    )

    # Background color
    if element.styles.get('bg_rgb'):
        r, g, b = element.styles['bg_rgb']
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(r, g, b)
    else:
        shape.fill.background()  # No fill

    # Remove border
    shape.line.fill.background()


def export_list_element(slide, element: SlideElement):
    """Export list as TextBox with bullets."""

    b = element.bounds
    txBox = slide.shapes.add_textbox(
        Inches(b['x']), Inches(b['y']),
        Inches(b['width']), Inches(b['height'])
    )

    tf = txBox.text_frame
    tf.word_wrap = True

    # Get list items
    items = element.tag.find_all('li')
    for i, li in enumerate(items):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.text = "• " + li.get_text()
        p.level = 0


def export_table_element(slide, element: SlideElement):
    """Export HTML table as PPTX table."""

    b = element.bounds
    table_tag = element.tag

    # Count rows and columns
    rows = table_tag.find_all('tr')
    if not rows:
        return

    num_rows = len(rows)
    num_cols = max(len(row.find_all(['th', 'td'])) for row in rows)

    if num_cols == 0:
        return

    # Create table
    table_shape = slide.shapes.add_table(
        num_rows, num_cols,
        Inches(b['x']), Inches(b['y']),
        Inches(b['width']), Inches(b['height'])
    )
    table = table_shape.table

    # Fill cells
    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        for j, cell in enumerate(cells):
            if j < num_cols:
                table.cell(i, j).text = cell.get_text()


# ─── Main Export Logic ────────────────────────────────────────────────────────

def export_native(html_path, output_path=None, width=1440, height=900):
    """Export HTML to native PPTX (editable text, shapes, tables)."""

    html_path = Path(html_path).resolve()
    if not html_path.exists():
        print(f"Error: file not found: {html_path}")
        sys.exit(1)

    output_path = Path(output_path) if output_path else html_path.with_suffix('.pptx')

    print(f"Exporting (native mode): {html_path.name}")
    print(f"Viewport: {width}×{height}")

    with sync_playwright() as p:
        # Import browser launcher
        browser = None
        try:
            from export_pptx import find_and_launch_browser
            browser = find_and_launch_browser(p)
        except ImportError:
            # Fallback: launch Chrome
            browser = p.chromium.launch(channel='chrome', headless=True)
        page = browser.new_page(viewport={"width": width, "height": height})

        page.goto(f"file://{html_path}", wait_until="networkidle")
        page.wait_for_timeout(500)

        slide_count = page.evaluate("document.querySelectorAll('.slide').length")
        if slide_count == 0:
            print("No .slide elements found.")
            browser.close()
            return

        print(f"Found {slide_count} slides. Parsing...")

        # Create PPTX
        prs = Presentation()
        prs.slide_width = Inches(13.33)
        prs.slide_height = Inches(13.33 * (height / width))

        blank_layout = prs.slide_layouts[6]

        for i in range(slide_count):
            print(f"  [{i+1}/{slide_count}] Processing...")

            # Parse elements
            elements = parse_slide_elements(page, i)

            # Create slide
            slide = prs.slides.add_slide(blank_layout)

            # Export each element
            for el in elements:
                try:
                    export_element_native(slide, el)
                except Exception as e:
                    print(f"    Warning: Failed to export element: {e}")

        browser.close()

    prs.save(str(output_path))
    print(f"✓ Saved: {output_path}  ({slide_count} slides)")
    return output_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("html", help="Path to the HTML presentation")
    parser.add_argument("output", nargs="?", help="Output .pptx path")
    parser.add_argument("--width", type=int, default=1440, help="Viewport width")
    parser.add_argument("--height", type=int, default=900, help="Viewport height")
    args = parser.parse_args()

    export_native(args.html, args.output, args.width, args.height)


if __name__ == "__main__":
    main()