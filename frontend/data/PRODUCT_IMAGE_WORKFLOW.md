# Product Image Workflow

`frontend/data/generate_products.py` artik `products.json` icin otomatik gorsel cozumleme yapar.

Calistirmak icin:

```bash
python frontend/data/generate_products.py
```

Script sunlari yapar:

- Urun adi + kategori + varsa brand/author bilgisiyle Openverse uzerinden gorsel arar.
- Uygun eslesme bulursa dosyayi `frontend/assets/products/` altina indirir.
- Eslesme zayifsa kategori bazli fallback SVG kullanir.
- `frontend/data/products.json` icindeki `image` alanlarini yerel relative path olarak yazar.
- `frontend/data/product_image_cache.json` icinde eslesme ve indirme cache'i tutar.

Notlar:

- Ilk calisma internet gerektirir ve veri setinin buyuklugune gore birkac dakika surebilir.
- Ikinci ve sonraki calismalarda cache sayesinde ayni dosyalar tekrar indirilmez.
- Eslesmeleri bastan uretmek istersen `frontend/data/product_image_cache.json` dosyasini silip scripti tekrar calistir.
