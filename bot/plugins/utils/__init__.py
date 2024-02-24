import typing


def hyperlink(text: str, url: typing.Optional[str] = None) -> str:
    if not url:
        return text
    return f"[{text}]({url})"
