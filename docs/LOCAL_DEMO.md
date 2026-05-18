# Local Demo

Bu proje deploy etmeden full local demo verilebilir.

## Portlar

- `http://localhost:8000` -> NeonRetro store
- `http://localhost:10000` -> FastAPI backend API
- `http://localhost:5173` -> Admin dashboard
- `localhost:5432` -> PostgreSQL

## Tek Komutla Aç

Repo kökünden:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml up -d --build
```

Bu komut şunları açar:

- veritabanı
- backend
- store
- admin dashboard

## Çalışıyor mu Kontrol

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml ps
```

Beklenen:

- `store` -> `8000`
- `backend` -> `10000`
- `admin-frontend` -> `5173`
- `postgres` -> `5432`

## Dashboard Login

- Email: `admin@example.com`
- Password: `StrongPass123`

## Demo Akışı

1. `http://localhost:8000` aç
2. Ürünlere gir, birkaç tıklama yap, sepete ürün ekle
3. `http://localhost:5173` aç
4. Yukarıdaki kullanıcıyla giriş yap
5. Analytics sayfasından event’leri göster

## Kapatma

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml down
```

Veritabanı datası da silinsin istenirse:

```bash
docker compose -f Senior-Project-Website_Add_Optimizer/docker-compose.yml down -v
```

## Notlar

- Backend migration compose açılışında otomatik çalışır
- Store tracker local backend’e `http://localhost:10000` üzerinden event yollar
- CORS local demo için `8000` ve `5173` portlarına izinli
