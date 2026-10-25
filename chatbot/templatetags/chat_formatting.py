import bleach
import markdown
from django import template
from django.utils.safestring import mark_safe


register = template.Library()

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union(
    {
        "p",
        "pre",
        "h1",
        "h2",
        "h3",
        "h4",
        "hr",
        "br",
        "blockquote",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "input",
        "del",
        "div",
        "span",
    }
)
ALLOWED_ATTRIBUTES = {
    "*": ["class"],
    "a": ["href", "title", "rel"],
    "input": ["type", "checked", "disabled"],
}


@register.filter
def render_markdown(value):
    rendered = markdown.markdown(
        str(value),
        extensions=["fenced_code", "tables", "sane_lists", "codehilite", "nl2br"],
        extension_configs={
            "codehilite": {
                "guess_lang": False,
                "noclasses": False,
            }
        },
    )
    cleaned = bleach.clean(
        rendered,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    return mark_safe(cleaned)
