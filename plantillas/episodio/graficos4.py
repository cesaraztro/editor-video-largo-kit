"""Gráficos fijos de la v4 (PNG con alfa): panel lateral, máscaras redondeadas, marco de navegador, logo."""
import kit   # config.json del kit + episodio.json (kit.py se copia junto a estos scripts)
from PIL import Image, ImageDraw, ImageFont
from armar import W, FUENTES

G = W / "marca"; G.mkdir(exist_ok=True)
NAVY, ORO = kit.color("panel", "rgb"), kit.color("acento", "rgb")   # config.json → marca.colores
PANEL_W, OPACO = 1100, 760


def panel():
    im = Image.new("RGBA", (PANEL_W, 1080))
    px = im.load()
    for x in range(PANEL_W):
        a = 255 if x < OPACO else int(255 * (1 - (x - OPACO) / (PANEL_W - OPACO)) ** 1.6)
        for y in range(1080):
            px[x, y] = (*NAVY, a)
    im.save(G / "panel.png")


def ventana(w, h, r, nombre):
    """Máscara redondeada (blanca dentro) y su borde dorado fino."""
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], r, fill=255)
    m.save(G / f"{nombre}_mask.png")
    b = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(b).rounded_rectangle([0, 0, w - 1, h - 1], r, outline=(*ORO, 230), width=3)
    b.save(G / f"{nombre}_borde.png")


def navegador():
    w, barra = 640, 34
    im = Image.new("RGBA", (w, barra), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w - 1, barra + 20], 14, fill=(30, 41, 66, 255))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([16 + i * 20, 12, 26 + i * 20, 22], fill=c)
    d.rounded_rectangle([90, 7, w - 90, barra - 7], 10, fill=(14, 26, 51, 255))
    f = ImageFont.truetype(str(FUENTES / "poppins-600.ttf"), 15)
    d.text((w / 2, barra / 2), kit.MARCA["web"], font=f, fill=(225, 230, 240), anchor="mm")
    im.save(G / "barra.png")


def logo(ancho, nombre):
    lg = Image.open(G / "logo_blanco.png").convert("RGBA")
    lg.resize((ancho, round(lg.height * ancho / lg.width)), Image.LANCZOS).save(G / nombre)


def logo_sombra(ancho=250, pad=16):
    """Logo blanco con sombra suave para que se lea sobre fondos claros."""
    from PIL import ImageFilter
    lg = Image.open(G / "logo_blanco.png").convert("RGBA")
    lg = lg.resize((ancho, round(lg.height * ancho / lg.width)), Image.LANCZOS)
    im = Image.new("RGBA", (lg.width + 2 * pad, lg.height + 2 * pad), (0, 0, 0, 0))
    sombra = Image.new("RGBA", im.size, (0, 0, 0, 0))
    a = lg.split()[3].point(lambda v: int(v * 0.75))
    sombra.paste(Image.new("RGBA", lg.size, (0, 0, 0, 255)), (pad, pad + 2), a)
    sombra = sombra.filter(ImageFilter.GaussianBlur(5))
    im = Image.alpha_composite(sombra, im); im.alpha_composite(lg, (pad, pad))
    im.save(G / "logo_250_sombra.png")


if __name__ == "__main__":
    panel(); ventana(630, 354, 22, "win"); ventana(640, 434, 16, "web"); navegador()
    logo(250, "logo_250.png"); logo(980, "logo_980.png"); logo_sombra()
    print("ok")
