"""
"Buy us a coffee" support link and dialog - reusable in any Tkinter app.

Extracted from JJ's Musicians Setlist Organiser (Help > Support and Help > About).

Two pieces:
  add_coffee_link(parent)          - the orange "☕  Enjoying it? Buy us a coffee"
                                     link, for an About window (or anywhere).
  show_support(root, app_name)     - the Help > Support dialog: a friendly,
                                     no-pressure invitation with a PayPal link.

Usage in another app:

    from coffee_support import add_coffee_link, show_support

    help_menu.add_command(label=f"Support {APP_NAME} ☕…",
                          command=lambda: show_support(root, APP_NAME))
    ...
    add_coffee_link(about_frame).pack(anchor="w", pady=(6, 0))

Run this file directly to see both.
"""

import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from tkinter import ttk

DONATE_URL = "https://paypal.me/jellyjazzsoftware"
BRAND = "JELLY JAZZ"
LINK_BLUE = "#0a64c8"          # link colour
ORANGE = "#f57c00"             # coffee link, and links when hovered
GREY = "#666"                  # secondary text


def _font(size_delta=0, **options):
    """A copy of Tk's default font, resized/styled."""
    f = tkfont.nametofont("TkDefaultFont").copy()
    f.configure(size=f.cget("size") + size_delta, **options)
    return f


def _center_over(win, parent):
    """Centre a window over its parent, measuring the real outer edges
    (title bars, borders and the parent's menu bar)."""
    win.update()
    border = win.winfo_rootx() - win.winfo_x()
    outer_w = win.winfo_width() + 2 * border
    outer_h = win.winfo_height() + (win.winfo_rooty() - win.winfo_y()) + border
    main_border = parent.winfo_rootx() - parent.winfo_x()
    main_w = parent.winfo_width() + 2 * main_border
    main_h = parent.winfo_rooty() + parent.winfo_height() + main_border - parent.winfo_y()
    x = parent.winfo_x() + (main_w - outer_w) // 2
    y = parent.winfo_y() + (main_h - outer_h) // 2
    win.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    win.update_idletasks()


def add_coffee_link(parent, url=DONATE_URL, text="☕  Enjoying it? Buy us a coffee"):
    """Create (but don't place) a clickable orange link that opens the
    donate page. Pack/grid it yourself, e.g. .pack(anchor="w", pady=(6, 0))."""
    font = _font(underline=True)
    bg = ttk.Style(parent).lookup("TFrame", "background") or parent.cget("bg")
    link = tk.Label(parent, text=text, fg=ORANGE, cursor="hand2", font=font, bg=bg)
    link.font = font                                    # keep a reference
    link.bind("<Button-1>", lambda e: webbrowser.open(url))
    return link


def show_support(parent, app_name, url=DONATE_URL, brand=BRAND,
                 reason="It helps keep the music and the app going."):
    """Help > Support: a friendly, no-pressure invitation to donate, with
    a clickable link and a single Close button. reason matches the Qt version."""
    win = tk.Toplevel(parent)
    win.title(f"Support {app_name}")
    win.transient(parent)
    win.resizable(False, False)
    win.attributes("-alpha", 0.0)                       # hide until centred
    body = ttk.Frame(win, padding=22)
    body.pack(fill="both", expand=True)

    title_font = _font(8, weight="bold")
    ttk.Label(body, text="☕  Buy us a coffee", font=title_font).pack(anchor="w")
    ttk.Label(body, wraplength=440, justify="left", text=(
        f"{app_name} is free and open source, brought to you by {brand}.\n\n"
        "If it's useful to you, you can buy us a coffee - any amount, any time, "
        f"entirely optional. {reason}")).pack(
        anchor="w", pady=(10, 14))

    ttk.Label(body, text="Click the link to open our PayPal page:",
              foreground=GREY).pack(anchor="w")
    link_font = _font(8, underline=True)
    # Match the ttk frame, not the window - they differ under themes like "clam"
    body_bg = ttk.Style(win).lookup("TFrame", "background") or win.cget("bg")
    link = tk.Label(body, text=url.replace("https://", ""), fg=LINK_BLUE,
                    cursor="hand2", font=link_font, bg=body_bg)
    link.pack(anchor="w", pady=(2, 0))
    link.bind("<Button-1>", lambda e: webbrowser.open(url))
    link.bind("<Enter>", lambda e: link.configure(fg=ORANGE))
    link.bind("<Leave>", lambda e: link.configure(fg=LINK_BLUE))
    win._fonts = (title_font, link_font)                # keep references
    ttk.Label(body, text="(opens in your web browser)", foreground=GREY).pack(
        anchor="w", pady=(2, 0))

    close = ttk.Button(body, text="Close", command=win.destroy, default="active")
    close.pack(anchor="e", pady=(18, 0))
    win.bind("<Escape>", lambda e: win.destroy())
    win.bind("<Return>", lambda e: win.destroy())
    _center_over(win, parent)
    win.attributes("-alpha", 1.0)
    close.focus_set()
    return win


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Coffee support demo")
    root.geometry("500x300")
    frame = ttk.Frame(root, padding=20)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="In an About window:").pack(anchor="w")
    add_coffee_link(frame).pack(anchor="w", pady=(6, 20))
    ttk.Button(frame, text="Help > Support…",
               command=lambda: show_support(root, "My App")).pack(anchor="w")
    root.mainloop()
