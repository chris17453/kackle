import re
import json
import markdown
from dataclasses import dataclass, asdict
from typing import Optional
from typing import List, Tuple



def format_code(code: str, language: str) -> str:
    return f'<pre lang="{language}" line="1">{code}</pre>'

def convert_codeblocks(markdown: str) -> str:
    # Handle code blocks first
    pattern = r'```(\w+)\n(.*?)```'
    result = markdown
    
    for language, code in re.findall(pattern, markdown, re.DOTALL):
        original = f"```{language}\n{code}```"
        formatted = format_code(code.strip(), language.upper())
        result = result.replace(original, formatted)
    
    return result

def convert_markdown_to_wp(markdown_text: str) -> str:
    markdown_text=convert_codeblocks(markdown_text)
    # Convert markdown to HTML with extensions
    html = markdown.markdown(markdown_text, extensions=[
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.nl2br',
        'markdown.extensions.sane_lists'
    ])
    return html