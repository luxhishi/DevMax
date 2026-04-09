import re

from django import template
from django.utils.html import conditional_escape, format_html
from django.utils.safestring import mark_safe


register = template.Library()

CODE_BLOCK_RE = re.compile(r"```(.*?)```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")


def _render_plain_text(text):
    return conditional_escape(text).replace("\n", "<br>")


def _render_inline_markup(text):
    pieces = []
    cursor = 0

    for match in INLINE_CODE_RE.finditer(text):
        pieces.append(_render_plain_text(text[cursor:match.start()]))
        code_content = conditional_escape(match.group(1))
        pieces.append(
            str(
                format_html(
                    '<code class="inline-code-token">{}</code>',
                    code_content,
                )
            )
        )
        cursor = match.end()

    pieces.append(_render_plain_text(text[cursor:]))
    return "".join(pieces)


@register.filter
def render_post_content(value):
    if not value:
        return ""

    content = str(value)
    pieces = []
    cursor = 0

    for match in CODE_BLOCK_RE.finditer(content):
        pieces.append(_render_inline_markup(content[cursor:match.start()]))
        code_content = match.group(1).strip("\n")
        pieces.append(
            str(
                format_html(
                    '<div class="code-block-shell" data-code-shell>'
                    '<div class="code-block-toolbar">'
                    '<span class="code-block-label">Code</span>'
                    '<button type="button" class="code-copy-button" onclick="event.stopPropagation()" aria-label="Copy code block">Copy</button>'
                    "</div>"
                    '<pre class="code-block-pre" data-code-source><code>{}</code></pre>'
                    "</div>",
                    conditional_escape(code_content),
                )
            )
        )
        cursor = match.end()

    pieces.append(_render_inline_markup(content[cursor:]))
    return mark_safe("".join(pieces))
