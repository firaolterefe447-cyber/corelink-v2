import sys
from io import BytesIO
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


def optimize_for_web(image_file):
    """
    Takes an uploaded image file, resizes it to max 1920px width,
    converts it to WebP, and compresses it for the web.
    """
    try:
        # 1. Open Image
        img = Image.open(image_file)

        # 2. Fix Orientation (Phone cameras often rotate images via EXIF)
        img = ImageOps.exif_transpose(img)

        # 3. Convert to RGB (Standard web color space, handles PNG transparency issues)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        # 4. Smart Resize (Max Width 1920px - HD Standard)
        # We don't upscale small images, only downscale big ones.
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int((float(img.height) * float(ratio)))
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

        # 5. Save as WebP (The "Magic" part)
        output = BytesIO()
        img.save(output, format='WEBP', quality=85, optimize=True)
        output.seek(0)

        # 6. Generate new filename
        new_name = image_file.name.split('.')[0] + '.webp'

        # 7. Return Django-friendly File
        return InMemoryUploadedFile(
            output,
            'ImageField',
            new_name,
            'image/webp',
            sys.getsizeof(output),
            None
        )
    except Exception as e:
        # Fallback: If optimization fails, return original file
        print(f"Image optimization failed: {e}")
        return image_file


# In profiles/utils.py

def optimize_company_logo(image_file):
    """
    SPECIALIZED FOR LOGOS:
    1. Preserves Transparency (RGBA).
    2. Resizes to max 500x500px (Tiny file size).
    3. Converts to WebP lossless-ish.
    """
    try:
        img = Image.open(image_file)
        img = ImageOps.exif_transpose(img)

        # 1. Resize (Max 500px - plenty for icons/avatars)
        max_size = (500, 500)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # 2. Output to buffer
        output = BytesIO()

        # 3. Save as WebP
        # If it has transparency (RGBA), WebP handles it automatically.
        # 'lossless=True' is often better for logos with sharp lines/text.
        if img.mode == 'RGBA':
            img.save(output, format='WEBP', lossless=True, quality=90)
        else:
            # Fallback for standard JPG logos
            img.save(output, format='WEBP', quality=90, optimize=True)

        output.seek(0)

        # 4. Generate Filename
        new_name = image_file.name.split('.')[0] + '_icon.webp'

        return InMemoryUploadedFile(
            output,
            'ImageField',
            new_name,
            'image/webp',
            sys.getsizeof(output),
            None
        )
    except Exception as e:
        print(f"Logo optimization failed: {e}")
        return image_file