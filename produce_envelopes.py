import pandas as pd
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

_FONTS_DIR = Path(__file__).parent / "fonts"

_fonts_registered = False

def register_fonts():
    global _fonts_registered
    if _fonts_registered:
        return
    pdfmetrics.registerFont(
        TTFont("Petit Formal Script", str(_FONTS_DIR / "PetitFormalScript-Regular.ttf"))
    )
    pdfmetrics.registerFont(
        TTFont("Montserrat", str(_FONTS_DIR / "Montserrat-VariableFont_wght.ttf"))
    )
    _fonts_registered = True



def read_file(file_path):
    path = str(file_path) if not isinstance(file_path, str) else file_path
    if path.lower().endswith(".csv"):
        return pd.read_csv(file_path)
    return pd.read_excel(file_path)

def read_excel(file_path):
    df = pd.read_excel(file_path)
    return df[['Name', 'Address', 'CityStateZip']].rename(columns={
        'CityStateZip': 'Zip'
    })

def chunk_dataframe(df, chunk_size):
    for start in range(0, len(df), chunk_size):
        yield df.iloc[start:start + chunk_size]

import re

def proper_case(text):
    if not text or pd.isna(text):
        return ""

    text = str(text).strip()

    # Title-case the string
    text = text.title()

    # Fix common directional abbreviations
    text = re.sub(r'\b(N|S|E|W)\b', lambda m: m.group(1).upper(), text)
    text = re.sub(r'\b(Nw|Ne|Sw|Se)\b', lambda m: m.group(0).upper(), text)

    # Fix state abbreviations (UT, CA, etc.)
    text = re.sub(r'\b[A-Z]{2}\b', lambda m: m.group(0).upper(), text)

    return text

def draw_centered_address(
    c,
    page_width,
    page_height,
    name,
    address,
    zip_code,
    name_font="Petit Formal Script",
    name_size=21,
    address_font="Montserrat",
    address_size=15,
    line_spacing=1.25,
):
    # Normalize address fields
    address = "" if pd.isna(address) else str(address).strip()
    zip_code = "" if pd.isna(zip_code) else str(zip_code).strip()
    name = proper_case(name)

    if address:
        lines = [
            ("name", proper_case(name)),
            ("addr", proper_case(address)),
            ("addr", proper_case(zip_code)),
        ]
    else:
        # No address → name only
        lines = [
            ("name", str(name)),
        ]

    # --- Calculate total block height ---
    total_height = 0
    for line_type, _ in lines:
        size = name_size if line_type == "name" else address_size
        total_height += size * line_spacing

    # Vertical centering
    start_y = (page_height + total_height) / 2
    y = start_y

    # --- Draw lines ---
    for line_type, text in lines:
        if line_type == "name":
            font, size = name_font, name_size
        else:
            font, size = address_font, address_size

        c.setFont(font, size)
        text_width = pdfmetrics.stringWidth(text, font, size)
        x = (page_width - text_width) / 2

        c.drawString(x, y, text)
        y -= size * line_spacing

def create_envelope_pdf(
    addresses,
    output_path,
    envelope_size_inches=(7.25, 5.25),
    name_size=21,
    address_size=15,
):
    envelope_size = (
        envelope_size_inches[0] * inch,
        envelope_size_inches[1] * inch,
    )

    # canvas.Canvas accepts a filename string, Path, or file-like object (e.g. BytesIO)
    dest = output_path if hasattr(output_path, "write") else str(output_path)
    c = canvas.Canvas(dest, pagesize=envelope_size)
    width, height = envelope_size

    for _, row in addresses.iterrows():
        draw_centered_address(
            c,
            width,
            height,
            name=row["Name"],
            address=row["Address"],
            zip_code=row["Zip"],
            name_size=name_size,
            address_size=address_size,
        )
        c.showPage()

    c.save()


def main():
    register_fonts()

    excel_path = "addresses.xlsx"
    batch_size = 20

    output_dir = Path.cwd() / "output_envelopes"
    output_dir.mkdir(exist_ok=True)
    
    addresses = read_excel(excel_path)

    for i, batch in enumerate(chunk_dataframe(addresses, batch_size), start=1):
        output_path = output_dir / f"envelopes_batch_{i:02d}.pdf"
        create_envelope_pdf(batch, output_path)
        print(f"Created {output_path} ({len(batch)} envelopes)")


if __name__ == "__main__":
    main()
