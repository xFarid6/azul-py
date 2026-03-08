import sys
import os

try:
    from PIL import Image
    import pypdf
except ImportError as e:
    print(f"Libraries missing: {e}")
    sys.exit(1)

def extract_tiles():
    img_path = 'azul-tiles.png'
    out_dir = 'assets/tiles'
    os.makedirs(out_dir, exist_ok=True)
    
    img = Image.open(img_path)
    w, h = img.size
    print(f"Image size: {w}x{h}")
    # User says: "the image has changed, now its 299x55, and it contains the 5 colored tiles with some grey padding between them. tiles should all be 55x55"
    tile_w = 55
    padding = 6
    colors = ['blue', 'yellow', 'red', 'black', 'white']
    for i, color in enumerate(colors):
        left = i * (tile_w + padding)
        top = 0
        right = left + tile_w
        bottom = tile_w
        tile = img.crop((left, top, right, bottom))
        tile.save(f'{out_dir}/{color}.png')
    print("Tiles extracted successfully.")

def extract_rules():
    pdf_path = 'EN-Azul-Rules.pdf'
    out_path = 'docs/rules.txt'
    os.makedirs('docs', exist_ok=True)
    
    with open(pdf_path, 'rb') as f:
        reader = pypdf.PdfReader(f)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
            
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(text)
    print("Rules extracted successfully.")

if __name__ == '__main__':
    extract_tiles()
    extract_rules()
