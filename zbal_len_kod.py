import zipfile
import os

def zip_only_code():
    zip_filename = "moj_cisty_kod.zip"
    
    # Tieto priečinky KOMPLETNE IGNORUJEME
    ignore_folders = {'venv', '.git', '__pycache__', 'media', 'staticfiles', 'static', '.idea', 'node_modules'}

    print(f"📦 Balím LEN Python súbory (.py) do {zip_filename}...")
    
    count = 0
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk('.'):
            # Odstránime zakázané priečinky z prehľadávania
            dirs[:] = [d for d in dirs if d not in ignore_folders]
            
            for file in files:
                # Zoberieme LEN .py súbory (a html šablóny ak chceš, ale hlavne .py)
                if file.endswith('.py'):
                    # Vynecháme tento skript samotný
                    if file == 'zbal_len_kod.py': continue
                    
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, arcname=os.path.relpath(file_path, '.'))
                    print(f" + {file}")
                    count += 1

    print(f"\n✅ HOTOVO! Zabalil som {count} súborov.")
    print(f"👉 Pošli mi súbor: {zip_filename}")

if __name__ == "__main__":
    zip_only_code()