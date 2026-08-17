"""Interactive arrow-key selector using prompt_toolkit for cross-platform support."""
import sys
from typing import List, Tuple, Optional, Any
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import Window, HSplit
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.styles import Style


def select_menu_option(
    title: str,
    options: List[Tuple[str, str, Any]],  # [(label, description, value)]
    default_index: int = 0,
    header_extra: str = ""
) -> Optional[Any]:
    """
    Renders an interactive arrow-key navigable menu.
    Allows navigating with Up/Down/j/k and selecting with Enter.
    """
    if not options:
        return None

    selected_index = [default_index if 0 <= default_index < len(options) else 0]

    def get_formatted_text():
        result = []
        if title:
            result.append(("class:title", f"╭──────────────────────────── {title} ────────────────────────────╮\n"))
        if header_extra:
            result.append(("class:extra", f"│  {header_extra:<84}  │\n"))
            result.append(("class:border", "├────────────────────────────────────────────────────────────────────────────────────┤\n"))

        for idx, (label, desc, _) in enumerate(options):
            if idx == selected_index[0]:
                line = f"  ❯ {label:<14}  —  {desc}"
                result.append(("class:selected", f"│ {line:<84} │\n"))
            else:
                line = f"    {label:<14}  —  {desc}"
                result.append(("class:unselected", f"│ {line:<84} │\n"))

        result.append(("class:border", "├────────────────────────────────────────────────────────────────────────────────────┤\n"))
        hint = "  (Use ↑/↓ or 1-9 to navigate · Enter to select · Esc/q to exit)"
        result.append(("class:hint", f"│ {hint:<84} │\n"))
        result.append(("class:title", "╰────────────────────────────────────────────────────────────────────────────────────╯\n"))
        return result

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def move_up(event):
        selected_index[0] = (selected_index[0] - 1) % len(options)

    @kb.add("down")
    @kb.add("j")
    def move_down(event):
        selected_index[0] = (selected_index[0] + 1) % len(options)

    for i in range(1, min(10, len(options) + 1)):
        idx_to_select = i - 1
        @kb.add(str(i))
        def pick_num(event, idx=idx_to_select):
            selected_index[0] = idx
            event.app.exit(result=options[idx][2])

    @kb.add("enter")
    def select(event):
        event.app.exit(result=options[selected_index[0]][2])

    @kb.add("escape")
    @kb.add("q")
    @kb.add("c-c")
    def cancel(event):
        event.app.exit(result=None)

    style = Style.from_dict({
        "title": "ansicyan bold",
        "border": "ansicyan",
        "extra": "ansiwhite dim",
        "selected": "ansibrightcyan bold bg:ansiblack",
        "unselected": "ansiwhite",
        "hint": "ansibrightblack italic",
    })

    # If running in non-interactive environment (CI, unit tests, redirected pipes)
    if not sys.stdin or not hasattr(sys.stdin, "isatty") or not sys.stdin.isatty():
        return options[selected_index[0]][2]

    try:
        control = FormattedTextControl(get_formatted_text)
        layout = Layout(HSplit([Window(control)]))

        app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=False,
            erase_when_done=True
        )
        return app.run()
    except Exception:
        # Fallback to default selection if interactive TUI cannot attach to console screen buffer
        return options[selected_index[0]][2]

