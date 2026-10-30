import shutil
from pathlib import Path

from django.apps import AppConfig
from django.conf import settings


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"

    def ready(self):
        # Auto-restore foto produk bawaan ke media/products jika belum ada (misal saat container PWS baru selesai di-redeploy)
        try:
            foto_dir = Path(__file__).resolve().parent / "data" / "foto"
            dest_dir = Path(settings.MEDIA_ROOT) / "products"
            if foto_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in foto_dir.iterdir():
                    if f.is_file() and f.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                        dest_file = dest_dir / f.name
                        if not dest_file.exists():
                            shutil.copy2(f, dest_file)
        except Exception:
            pass

