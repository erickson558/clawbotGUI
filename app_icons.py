from __future__ import annotations

try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageTk = None


class ButtonIconFactory:
    def __init__(self, size: int = 30) -> None:
        self.size = size
        self._cache: dict[tuple[str, int], object] = {}

    def build(self, kind: str) -> object | None:
        if Image is None or ImageDraw is None or ImageTk is None:
            return None

        key = (kind, self.size)
        if key in self._cache:
            return self._cache[key]

        image = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        stroke = max(2, self.size // 11)
        margin = max(3, self.size // 8)
        white = (248, 251, 255, 255)

        if kind == "start":
            draw.polygon(
                [
                    (margin + 2, margin),
                    (self.size - margin, self.size // 2),
                    (margin + 2, self.size - margin),
                ],
                fill=white,
            )
        elif kind == "stop":
            draw.rounded_rectangle(
                (margin + 2, margin + 2, self.size - margin - 2, self.size - margin - 2),
                radius=4,
                fill=white,
            )
        elif kind == "restart":
            draw.arc(
                (margin, margin + 1, self.size - margin, self.size - margin),
                start=35,
                end=325,
                fill=white,
                width=stroke,
            )
            draw.polygon(
                [
                    (self.size - margin - 2, self.size // 2 - 7),
                    (self.size - margin + 5, self.size // 2),
                    (self.size - margin - 2, self.size // 2 + 7),
                ],
                fill=white,
            )
        elif kind == "refresh":
            draw.arc(
                (margin, margin, self.size - margin, self.size - margin),
                start=35,
                end=190,
                fill=white,
                width=stroke,
            )
            draw.arc(
                (margin, margin, self.size - margin, self.size - margin),
                start=215,
                end=360,
                fill=white,
                width=stroke,
            )
            draw.polygon(
                [
                    (self.size - margin - 3, self.size // 2 - 7),
                    (self.size - margin + 4, self.size // 2),
                    (self.size - margin - 3, self.size // 2 + 7),
                ],
                fill=white,
            )
            draw.polygon(
                [
                    (margin + 3, self.size // 2 - 7),
                    (margin - 4, self.size // 2),
                    (margin + 3, self.size // 2 + 7),
                ],
                fill=white,
            )
        elif kind == "dashboard":
            draw.rounded_rectangle(
                (margin, margin, self.size - margin, self.size - margin),
                radius=5,
                outline=white,
                width=stroke,
            )
            bar_width = stroke + 2
            base_y = self.size - margin - 2
            draw.rectangle((margin + 4, base_y - 8, margin + 4 + bar_width, base_y), fill=white)
            draw.rectangle((self.size // 2 - bar_width // 2, base_y - 13, self.size // 2 + bar_width // 2, base_y), fill=white)
            draw.rectangle((self.size - margin - 4 - bar_width, base_y - 18, self.size - margin - 4, base_y), fill=white)
        elif kind == "browser":
            draw.rounded_rectangle(
                (margin, margin + 2, self.size - margin, self.size - margin),
                radius=5,
                outline=white,
                width=stroke,
            )
            draw.line((margin + 2, margin + 9, self.size - margin - 2, margin + 9), fill=white, width=stroke)
            draw.ellipse((margin + 4, margin + 4, margin + 8, margin + 8), fill=white)
            draw.line((self.size // 2 - 5, self.size // 2 + 1, self.size // 2 + 4, self.size // 2 + 1), fill=white, width=stroke)
            draw.line((self.size // 2 - 5, self.size // 2 + 7, self.size // 2 + 8, self.size // 2 + 7), fill=white, width=stroke)
        elif kind == "kill":
            draw.ellipse((margin, margin, self.size - margin, self.size - margin), outline=white, width=stroke)
            draw.line((margin + 5, margin + 5, self.size - margin - 5, self.size - margin - 5), fill=white, width=stroke)
            draw.line((self.size - margin - 5, margin + 5, margin + 5, self.size - margin - 5), fill=white, width=stroke)
        elif kind == "clear":
            draw.rectangle((self.size // 2 - 6, margin + 8, self.size // 2 + 6, self.size - margin), outline=white, width=stroke)
            draw.line((self.size // 2 - 9, margin + 8, self.size // 2 + 9, margin + 8), fill=white, width=stroke)
            draw.line((self.size // 2 - 4, margin + 4, self.size // 2 + 4, margin + 4), fill=white, width=stroke)
            draw.line((self.size // 2 - 2, margin + 11, self.size // 2 - 2, self.size - margin - 3), fill=white, width=stroke)
            draw.line((self.size // 2 + 2, margin + 11, self.size // 2 + 2, self.size - margin - 3), fill=white, width=stroke)
        elif kind == "exit":
            draw.rounded_rectangle(
                (margin, margin + 2, self.size // 2 + 1, self.size - margin),
                radius=4,
                outline=white,
                width=stroke,
            )
            draw.line((self.size // 2 + 3, self.size // 2, self.size - margin - 2, self.size // 2), fill=white, width=stroke)
            draw.polygon(
                [
                    (self.size - margin - 8, self.size // 2 - 6),
                    (self.size - margin + 1, self.size // 2),
                    (self.size - margin - 8, self.size // 2 + 6),
                ],
                fill=white,
            )
        else:
            draw.ellipse((margin, margin, self.size - margin, self.size - margin), fill=white)

        tk_image = ImageTk.PhotoImage(image)
        self._cache[key] = tk_image
        return tk_image
