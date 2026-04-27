from PIL import Image, ImageOps
from io import BytesIO
from django.core.files.base import ContentFile
import os


# ENGINE A: FOR AVATARS (Square Crop)
def optimize_avatar(image_field, size=(1024, 1024)):
    """
    Ultra-Res Image Engine:
    - Forced 1024px density.
    - Lanczos Sharpness.
    - 95% Quality WebP.
    """
    if not image_field:
        return None

    img = Image.open(image_field)
    img = ImageOps.exif_transpose(img)

    if img.mode != 'RGB':
        img = img.convert('RGB')

    img.thumbnail(size, Image.Resampling.LANCZOS)

    output = BytesIO()
    img.save(output, format='WebP', quality=95, method=6)
    output.seek(0)

    name = os.path.splitext(os.path.basename(image_field.name))[0]
    return ContentFile(output.read(), name=f"{name}.webp")
# ENGINE B: FOR PROJECTS/COVERS (Maintain Aspect Ratio)
def optimize_standard_image(image_field, max_size=(1200, 1200)):
    if not image_field: return None
    img = Image.open(image_field)
    img = ImageOps.exif_transpose(img)

    # Resize while keeping aspect ratio
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = BytesIO()
    img.save(output, format='WebP', quality=80, method=6)
    output.seek(0)
    return ContentFile(output.read(), name=f"{os.path.splitext(image_field.name)[0]}.webp")


import sys
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile


def optimize_cover_image(image):
    """
    Specific optimization for Hero/Cover images.
    Allows 4K resolution (3840px width) and maintains high quality.
    """
    if not image:
        return None

    # Open the image
    im = Image.open(image)

    # Convert to RGB if necessary
    if im.mode in ('RGBA', 'P'):
        im = im.convert('RGB')

    # Resize only if width is massive (over 4K), otherwise keep original high res
    # We use 3840 (4K width) as the standard high-res limit
    max_width = 3840
    if im.width > max_width:
        ratio = max_width / float(im.width)
        new_height = int((float(im.height) * float(ratio)))
        im = im.resize((max_width, new_height), Image.Resampling.LANCZOS)

    # Save logic
    output = BytesIO()
    # Quality 95 for hero images (very low compression)
    im.save(output, format='WEBP', quality=95, method=6)
    output.seek(0)

    return InMemoryUploadedFile(
        output,
        'ImageField',
        f"{image.name.split('.')[0]}.webp",
        'image/webp',
        sys.getsizeof(output),
        None
    )