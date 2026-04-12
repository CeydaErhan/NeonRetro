# CLAUDE.md — Simple-Test-Website

## Ne İşe Yarar?
Bu dosya **Claude Code** tarafından her oturumda otomatik olarak okunur.
Projeye özgü kuralları, yapıyı ve geliştirme kılavuzlarını burada tutmak,
her seferinde aynı bağlamı tekrar açıklamak zorunda kalmamamızı sağlar.

---

## Proje Genel Bakış
"NOVA" adlı minimal bir e-ticaret demo mağazası. Asıl amacı sayfa izleme
(page tracking) ve tıklama analitiği (click analytics) implementasyonlarını
test etmektir. Framework ya da derleme adımı yoktur — saf HTML + JS.

## Teknoloji Yığını
- HTML5 / Vanilla JavaScript
- Tailwind CSS (CDN üzerinden)
- Browser localStorage (sepet ve oturum kalıcılığı)
- `tracker.js` → analitik arka ucuna olaylar gönderir

## Önemli Dosyalar
| Dosya | Amaç |
|---|---|
| `index.html` | Ana sayfa, elektronik kategorisi |
| `clothes.html` | Giyim kategorisi |
| `cosmetics.html` | Kozmetik kategorisi |
| `product.html` | Dinamik ürün detayı (`?id=` query parametresi kullanır) |
| `cart.html` | Alışveriş sepeti + ödeme |
| `tracker.js` | Oturum başlatma ve etkinlik izleme — dikkatli değiştirilmeli |

## Analitik
`tracker.js`, oturum/sayfa görüntüleme/tıklama verilerini şu adrese POST eder:
```
https://senior-project-website-add-optimizer.onrender.com
```
Elementler `data-track` nitelikleri aracılığıyla izlenir.

## Geliştirme Kuralları
- `tracker.js` dosyasını analitik sözleşmeyi anlamadan **değiştirme**.
- Tüm stillendirmeyi Tailwind utility sınıfları içinde tut; özel CSS dosyası ekleme.
- Değişikliklerden sonra tüm sayfaları tarayıcıda test et (otomatik test paketi yok).
- Sepet durumu `localStorage` anahtarı `cart` içinde; oturum ID'si `sessionId` içinde saklanır.

## Sık Yapılan Görevler
- **Ürün ekle**: İlgili HTML dosyasında bir ürün kartını kopyala ve `product.html`
  içindeki `products` dizisine eşleşen bir giriş ekle.
- **İzlemeyi test et**: Tıklamaların ardından analitik arka ucuna giden POST
  isteklerini görmek için tarayıcı DevTools Network sekmesini aç.
