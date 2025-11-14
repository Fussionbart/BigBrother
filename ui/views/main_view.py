from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

def build_bottom_menu():
    buttons = [
        ("[F2] Targets",),
        ("[F3] Threads",),
        ("[F4] Wordlist",),
        ("[F5] DNS",),
        ("[F6] Output",),
        ("[F7] Lang",),
        ("[F9] Run",),
        ("[F10] Quit",),
    ]

    button_windows = []
    for text, in buttons:
        button_windows.append(
            Window(
                content=FormattedTextControl(
                    text=text + "   ",
                    focusable=True
                ),
                style="class:menu",
                height=1,
                width=len(text) + 3,
            )
        )

    return VSplit(button_windows, style="class:menu")