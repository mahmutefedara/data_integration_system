🚀 CrawlerZero: Advanced Data Integration System

CrawlerZero, web sitelerinden hiyerarşik olarak veri toplayan, dökümanları (PDF, DOCX, vb.) ayıklayan ve bunları hem yerel dosya sisteminde hem de PostgreSQL üzerinde indeksleyen yüksek performanslı bir asenkron tarayıcı sistemidir.
✨ Öne Çıkan Özellikler

    ⚡ Asenkron Mimari: asyncio ve asyncpg ile aynı anda onlarca sayfayı ve dosyayı tarayabilir.

    📂 Akıllı Döküman İşleme: PDF, DOC, DOCX, PPTX ve XLSX dosyalarından otomatik metin çıkarma.

    🎯 Path Mode: Sadece belirli bir alt dizin (path) altındaki içeriğe odaklanma.

    📄 Documents Only Modu: HTML sayfalarını sadece link bulmak için kullanıp, veritabanını sadece değerli dökümanlarla doldurma.

    🔄 Incremental Crawling: content_hash kontrolü ile sadece değişen veya yeni eklenen içerikleri işleme.

    🛡️ Hata Toleransı: Bozuk dosyalar veya karakter seti (encoding) sorunlarına karşı dayanıklı yapı.

🛠️ Kurulum
1. Gereksinimler

    Python 3.10+

    PostgreSQL 14+

    Virtualenv (Önerilir)

2. Bağımlılıkların Yüklenmesi
Bash

git clone https://github.com/kullanici/crawler_zero.git
cd crawler_zero
pip install -r requirements.sh

3. Veritabanı Hazırlığı

PostgreSQL üzerinde aşağıdaki tabloları oluşturun:
SQL

-- İş Takip Tablosu
CREATE TABLE jobs (
    job_id UUID PRIMARY KEY,
    start_url TEXT NOT NULL,
    config JSONB,
    documents_only BOOLEAN DEFAULT FALSE,
    status TEXT DEFAULT 'PENDING',
    agent_id TEXT,
    project_id INT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Veri Tablosu
CREATE TABLE raw_documents (
    id SERIAL PRIMARY KEY,
    source_type TEXT, -- 'page' veya 'file'
    source_id TEXT,
    url TEXT,
    site TEXT,
    raw_text TEXT,
    content_hash TEXT UNIQUE,
    content_type TEXT,
    text_len INT,
    agent_id TEXT,
    project_id INT,
    created_at TIMESTAMP DEFAULT NOW()
);

🚀 Çalıştırma

Sistemi tek bir komutla ayağa kaldırmak için launcher.py scriptini kullanabilirsiniz:
Bash

python3 launcher.py

Bu komut hem FastAPI sunucusunu hem de Worker Daemon'ı paralel olarak başlatır.
📑 API Kullanımı
Yeni Bir Tarama Başlatma

POST /jobs endpoint'ine bir JSON göndererek işlemi başlatın:
Bash

curl -X POST http://127.0.0.1:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://docs.python.org/3/tutorial/",
    "path_mode": true,
    "documents_only": true,
    "concurrency": 8,
    "agent_id": "agent_007",
    "project_id": 1
  }'

Parametre Açıklamaları
Parametre	Açıklama
path_mode	true ise sadece başlangıç URL'inin alt klasörlerini tarar.
documents_only	true ise HTML metinlerini DB'ye kaydetmez, sadece dosyaları (PDF vb.) kaydeder.
download_only_same_domain	Dış sitelere verilen döküman linklerini indirmeyi engeller.
incremental	Daha önce çekilen ve değişmeyen içerikleri atlar.
📂 Dosya Yapısı

    api/: FastAPI endpointleri ve istek modelleri.

    workers/: Arka planda çalışan tarayıcı (crawler) mantığı.

    storage/: Yerel dosya sistemi (JSON index) yönetimi.

    db/: PostgreSQL bağlantı ve sorgu katmanı.

    utils/: Hashleme, domain ayıklama ve metin temizleme araçları.

📝 Lisans

Bu proje MIT lisansı altında korunmaktadır.
