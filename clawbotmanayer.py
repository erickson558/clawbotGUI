import sys

try:
    import tkinter as tk
except ImportError:
    print("Tkinter no está disponible en este sistema.")
    sys.exit(1)

from app_ui import create_app


def main() -> None:
    root = tk.Tk()
    create_app(root)
    root.mainloop()


if __name__ == "__main__":
    main()
