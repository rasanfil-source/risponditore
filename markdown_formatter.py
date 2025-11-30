"""
Markdown to HTML Formatter Module
Converts Gemini's Markdown formatting to Gmail-compatible HTML
Only processes emails that actually contain Markdown markers

Author: Parish Secretary AI System
Version: 1.0
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class MarkdownFormatter:
    """
    Intelligent Markdown to HTML converter for email responses
    
    Features:
    - Detects Markdown presence before processing
    - Preserves layout and structure
    - Handles bold, italic, lists, headers
    - Safe: only processes when needed
    """
    
    def __init__(self):
        """Initialize formatter with Markdown patterns"""
        
        # Markdown detection patterns (quick check)
        self.detection_patterns = [
            r'\*\*[^*]+\*\*',           # **bold**
            r'\*[^*]+\*',               # *italic*
            r'^#{1,6}\s+',              # # Headers
            r'^\s*[-*]\s+',             # - lists
            r'^\s*\d+\.\s+',            # 1. numbered lists
            r'\[.+\]\(.+\)',            # [links](url)
        ]
        
        logger.info("✓ MarkdownFormatter initialized")
    
    def has_markdown(self, text: str) -> bool:
        """
        Check if text contains Markdown formatting
        
        Args:
            text: Text to check
            
        Returns:
            True if Markdown markers detected
        """
        for pattern in self.detection_patterns:
            if re.search(pattern, text, re.MULTILINE):
                logger.debug(f"   Markdown detected: pattern '{pattern[:20]}...'")
                return True
        return False
    
    def convert_to_html(self, markdown_text: str) -> Tuple[str, str]:
        """
        Convert Markdown text to HTML (both plain and formatted versions)
        
        Args:
            markdown_text: Text with Markdown formatting
            
        Returns:
            Tuple of (plain_text, html_text)
        """
        # Keep original for plain text version
        plain_text = self._strip_markdown(markdown_text)
        
        # Convert to HTML
        html_text = markdown_text
        
        # === STEP 1: Bold (**text** or __text__) ===
        html_text = re.sub(
            r'\*\*(.+?)\*\*',
            r'<strong>\1</strong>',
            html_text
        )
        html_text = re.sub(
            r'__(.+?)__',
            r'<strong>\1</strong>',
            html_text
        )
        
        # === STEP 2: Italic (*text* or _text_) ===
        # Avoid matching bold markers already converted
        html_text = re.sub(
            r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)',
            r'<em>\1</em>',
            html_text
        )
        html_text = re.sub(
            r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)',
            r'<em>\1</em>',
            html_text
        )
        
        # === STEP 3: Headers (# to ######) ===
        # Convert headers to styled paragraphs (safer for Gmail)
        html_text = re.sub(
            r'^######\s+(.+)$',
            r'<p style="font-size: 12px; font-weight: bold; margin: 8px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        html_text = re.sub(
            r'^#####\s+(.+)$',
            r'<p style="font-size: 13px; font-weight: bold; margin: 8px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        html_text = re.sub(
            r'^####\s+(.+)$',
            r'<p style="font-size: 14px; font-weight: bold; margin: 10px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        html_text = re.sub(
            r'^###\s+(.+)$',
            r'<p style="font-size: 16px; font-weight: bold; margin: 10px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        html_text = re.sub(
            r'^##\s+(.+)$',
            r'<p style="font-size: 18px; font-weight: bold; margin: 12px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        html_text = re.sub(
            r'^#\s+(.+)$',
            r'<p style="font-size: 20px; font-weight: bold; margin: 12px 0;">\1</p>',
            html_text,
            flags=re.MULTILINE
        )
        
        # === STEP 4: Unordered Lists (- or *) ===
        html_text = self._convert_unordered_lists(html_text)
        
        # === STEP 5: Links [text](url) ===
        html_text = re.sub(
            r'\[([^\]]+)\]\(([^)]+)\)',
            r'<a href="\2">\1</a>',
            html_text
        )

        # === STEP 6: Ordered Lists (1. 2. 3.) ===
        html_text = self._convert_ordered_lists(html_text)
        
        # === STEP 7: Line breaks (preserve paragraph structure) ===
        # Convert double newlines to paragraph breaks
        html_text = re.sub(r'\n\n+', '</p><p>', html_text)
        
        # Wrap in paragraph if not already wrapped
        if not html_text.strip().startswith('<'):
            html_text = f'<p>{html_text}</p>'
        
        # Convert single newlines to <br> (but not inside lists)
        html_text = re.sub(
            r'(?<!>)\n(?!<)',
            '<br>',
            html_text
        )
        
        return plain_text, html_text
    
    def _strip_markdown(self, text: str) -> str:
        """
        Strip Markdown markers to get plain text
        
        Args:
            text: Text with Markdown
            
        Returns:
            Plain text without Markdown markers
        """
        plain = text
        
        # Remove bold
        plain = re.sub(r'\*\*(.+?)\*\*', r'\1', plain)
        plain = re.sub(r'__(.+?)__', r'\1', plain)
        
        # Remove italic
        plain = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', plain)
        plain = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', plain)
        
        # Remove headers
        plain = re.sub(r'^#{1,6}\s+(.+)$', r'\1', plain, flags=re.MULTILINE)
        
        # Remove list markers (keep content)
        plain = re.sub(r'^\s*[-*]\s+', '', plain, flags=re.MULTILINE)
        plain = re.sub(r'^\s*\d+\.\s+', '', plain, flags=re.MULTILINE)
        
        return plain
    
    def _convert_unordered_lists(self, text: str) -> str:
        """
        Convert Markdown unordered lists to HTML
        
        Handles:
        - Simple lists
        - Nested lists (indented)
        """
        lines = text.split('\n')
        result = []
        in_list = False
        list_depth = 0
        
        for line in lines:
            # Check if this is a list item
            match = re.match(r'^(\s*)([-*])\s+(.+)$', line)
            
            if match:
                indent = len(match.group(1))
                content = match.group(3)
                
                # Calculate depth (every 2 spaces = 1 level)
                new_depth = indent // 2
                
                if not in_list:
                    # Start new list
                    result.append('<ul style="margin: 8px 0; padding-left: 20px;">')
                    in_list = True
                    list_depth = 0
                
                # Handle depth changes
                while list_depth < new_depth:
                    result.append('<ul style="padding-left: 20px;">')
                    list_depth += 1
                
                while list_depth > new_depth:
                    result.append('</ul>')
                    list_depth -= 1
                
                result.append(f'<li>{content}</li>')
            
            else:
                # Close list if we were in one
                if in_list:
                    while list_depth > 0:
                        result.append('</ul>')
                        list_depth -= 1
                    result.append('</ul>')
                    in_list = False
                
                result.append(line)
        
        # Close any remaining open lists
        if in_list:
            while list_depth > 0:
                result.append('</ul>')
                list_depth -= 1
            result.append('</ul>')
        
        return '\n'.join(result)
    
    def _convert_ordered_lists(self, text: str) -> str:
        """
        Convert Markdown ordered lists to HTML
        
        Handles:
        - Simple numbered lists
        - Nested numbered lists
        """
        lines = text.split('\n')
        result = []
        in_list = False
        list_depth = 0
        
        for line in lines:
            # Check if this is a numbered list item
            match = re.match(r'^(\s*)(\d+)\.\s+(.+)$', line)
            
            if match:
                indent = len(match.group(1))
                content = match.group(3)
                
                # Calculate depth
                new_depth = indent // 2
                
                if not in_list:
                    # Start new list
                    result.append('<ol style="margin: 8px 0; padding-left: 20px;">')
                    in_list = True
                    list_depth = 0
                
                # Handle depth changes
                while list_depth < new_depth:
                    result.append('<ol style="padding-left: 20px;">')
                    list_depth += 1
                
                while list_depth > new_depth:
                    result.append('</ol>')
                    list_depth -= 1
                
                result.append(f'<li>{content}</li>')
            
            else:
                # Close list if we were in one
                if in_list:
                    while list_depth > 0:
                        result.append('</ol>')
                        list_depth -= 1
                    result.append('</ol>')
                    in_list = False
                
                result.append(line)
        
        # Close any remaining open lists
        if in_list:
            while list_depth > 0:
                result.append('</ol>')
                list_depth -= 1
            result.append('</ol>')
        
        return '\n'.join(result)
    
    def format_email_response(self, response_text: str) -> Tuple[str, str, bool]:
        """
        Main entry point: format email response intelligently
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            Tuple of (plain_text, html_text, was_converted)
        """
        # Check if Markdown is present
        if not self.has_markdown(response_text):
            logger.info("   No Markdown detected, using plain text")
            return response_text, None, False
        
        logger.info("   Markdown detected, converting to HTML")
        
        # Convert to HTML
        plain_text, html_text = self.convert_to_html(response_text)
        
        logger.debug(f"   Plain text: {len(plain_text)} chars")
        logger.debug(f"   HTML text: {len(html_text)} chars")
        
        return plain_text, html_text, True


# ============================================================================
# TESTING
# ============================================================================

def test_markdown_formatter():
    """Test the Markdown formatter with various inputs"""
    
    formatter = MarkdownFormatter()
    
    print("=" * 80)
    print("TESTING MARKDOWN FORMATTER")
    print("=" * 80)
    
    # Test Case 1: Simple bold
    test1 = "Gentile Mario,\n\nGli orari sono: **lunedì-venerdì 8:00-12:00**.\n\nCordiali saluti"
    print("\nTest 1 - Simple Bold:")
    print(f"Input: {test1}")
    plain, html, converted = formatter.format_email_response(test1)
    if converted:
        print(f"Plain: {plain}")
        print(f"HTML: {html}")
    print(f"Converted: {converted}")
    
    # Test Case 2: Lists
    test2 = """Gentile Mario,

Per iscriversi:
- Compilare il modulo
- Portare certificato di battesimo
- Presentarsi in segreteria

Cordiali saluti"""
    
    print("\nTest 2 - Unordered List:")
    print(f"Input: {test2}")
    plain, html, converted = formatter.format_email_response(test2)
    if converted:
        print(f"HTML: {html[:200]}...")
    print(f"Converted: {converted}")
    
    # Test Case 3: Headers
    test3 = """Gentile Mario,

## Informazioni Catechesi

La catechesi **inizierà** il 21 settembre.

### Orari
- Domenica ore 10:00

Cordiali saluti"""
    
    print("\nTest 3 - Headers + Bold + List:")
    print(f"Input: {test3}")
    plain, html, converted = formatter.format_email_response(test3)
    if converted:
        print(f"HTML: {html[:300]}...")
    print(f"Converted: {converted}")
    
    # Test Case 4: No Markdown (should not convert)
    test4 = "Gentile Mario,\n\nGrazie per la sua email.\n\nCordiali saluti"
    print("\nTest 4 - No Markdown:")
    print(f"Input: {test4}")
    plain, html, converted = formatter.format_email_response(test4)
    print(f"Converted: {converted} (should be False)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    test_markdown_formatter()