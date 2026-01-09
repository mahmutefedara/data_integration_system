import subprocess
import sys
import time
import signal
import os

def run_integration_system():
    processes = []


    try:
        # 1. API'yi Başlat (Uvicorn)
        # --reload modunu geliştirme aşamasında kullanabilirsin
        print("[1/2] API Sunucusu (FastAPI) başlatılıyor...")
        api_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=None, # Loglar doğrudan ana terminale akar
            stderr=None
        )
        processes.append(api_proc)

        # API'nin portu dinlemeye başlaması için kısa bir bekleme
        time.sleep(2)

        # 2. Worker Daemon'ı Başlat
        print("[2/2] Worker Daemon (Crawler) başlatılıyor...")
        worker_proc = subprocess.Popen(
            [sys.executable, "-m", "workers.worker_daemon"],
            stdout=None,
            stderr=None
        )
        processes.append(worker_proc)

        print("\nSistem aktif. Durdurmak için Control+C tuşlarına basın.\n")

        # Süreçleri sürekli izle
        while True:
            time.sleep(1)
            # Eğer süreçlerden biri kendi kendine kapandıysa (hata vb.)
            for proc in processes:
                poll = proc.poll()
                if poll is not None:
                    print(f"\nBir süreç beklenmedik şekilde durdu (Exit Code: {poll}).")
                    raise KeyboardInterrupt

    except KeyboardInterrupt:
        print("\nKapatma sinyali (SIGINT) alındı. Süreçler sonlandırılıyor...")
    except Exception as e:
        print(f"\n️ Beklenmedik Hata: {e}")
    finally:
        # Temizlik aşaması: Açık kalan süreçleri öldür
        for proc in processes:
            if proc.poll() is None: # Eğer hala çalışıyorsa
                print(f"--- Süreç kapatılıyor (PID: {proc.pid}) ---")
                proc.terminate() # Nazikçe kapatmayı dene
                
        # Süreçlerin tamamen kapanmasını bekle
        for proc in processes:
            proc.wait()
        
        print("Tüm sistem güvenle kapatıldı.")

if __name__ == "__main__":
    # Scriptin bulunduğu dizine geç (yolların şaşmaması için)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_integration_system()
