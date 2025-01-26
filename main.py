import tkinter as tk
from tkinter import filedialog, messagebox, Toplevel
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
import os
import sqlite3
import time
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QUrl
import sys
import openpyxl
import pkg_resources
import json


DB_FILE = "data.db"
DAILY_LIMIT = 300

# Initialize PyQt5 Media Player
app = QApplication(sys.argv)
media_player = QMediaPlayer()
current_song_index = 0
song_list = [
    "Playboi Carti - Pissy Pamper.mp3", 
    "Playboi Carti - Spaceship (prod. Ricoworld).mp3", 
    "2024 prod. ojivolta, earlonthebeat, and Kanye West.mp3", 
    "Playboi Carti - Evil Jordan.mp3", 
    "Playboi Carti - Made It This Far.mp3"
]
MAX_SONGS = 5
song_list = song_list[:MAX_SONGS]  # Eğer şarkı listesi 5'ten fazla ise, 5'e kadar olan kısmı al

console_window = None
console_text = None

# Variable to track if the sound is muted
is_muted = False

# Play Song Function
def play_song(index):
    if 0 <= index < len(song_list):
        song_path = get_resource_path(song_list[index])
        media_player.setMedia(QMediaContent(QUrl.fromLocalFile(song_path)))
        media_player.play()
        current_song_var.set(song_list[index].replace('.mp3', ''))  # Uzantıyı kaldırarak şarkı adını göster

def media_status_changed(status):
    if status == QMediaPlayer.EndOfMedia:
        next_song()

media_player.mediaStatusChanged.connect(media_status_changed)

def get_database_path():
    """
    Veritabanı dosyasının doğru yolu PyInstaller tarafından 'onefile' modunda çalıştırıldığında bulunur.
    """
    if hasattr(sys, '_MEIPASS'):  # PyInstaller 'onefile' modunda çalışırken geçici dizin burada saklanır
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, DB_FILE)

def init_database():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sent_email TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_limit (
            date TEXT PRIMARY KEY,
            remaining INTEGER
        )
        """
    )
    conn.commit()
    conn.close()

def update_daily_limit():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    date = time.strftime("%Y-%m-%d")
    cursor.execute("SELECT remaining FROM daily_limit WHERE date = ?", (date,))
    result = cursor.fetchone()
    if result is None:
        cursor.execute("INSERT INTO daily_limit (date, remaining) VALUES (?, ?)", (date, DAILY_LIMIT))
        remaining = DAILY_LIMIT
    else:
        remaining = result[0]
    conn.commit()
    conn.close()
    return remaining

def decrement_daily_limit():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    date = time.strftime("%Y-%m-%d")
    cursor.execute("UPDATE daily_limit SET remaining = remaining - 1 WHERE date = ?", (date,))
    conn.commit()
    conn.close()

# Select File Function
def select_file(entry):
    filepath = filedialog.askopenfilename()
    entry.delete(0, tk.END)
    entry.insert(0, filepath)

# Log to Console
def log_to_console(message):
    print(message)

    if console_text:
        console_text.config(state=tk.NORMAL)
        console_text.insert(tk.END, message + "\n")
        console_text.see(tk.END)
        console_text.config(state=tk.DISABLED)

def open_console():
    global console_window, console_text
    if console_window is None or not console_window.winfo_exists():
        console_window = Toplevel(root)
        console_window.title("Konsol")
        console_window.geometry("800x400")
        
        console_text = tk.Text(console_window, height=20, width=100)
        console_text.pack(expand=True, fill=tk.BOTH)
        console_text.config(state=tk.DISABLED)
        
        log_to_console("Konsol açıldı...")

stop_flag = False

def send_emails(sender_email, password, subject, body, attachment_file, excel_file, signature_file):
    global stop_flag
    try:
        receiver_emails = get_emails_from_excel(excel_file)
    except Exception as e:
        messagebox.showerror("Hata", f"Excel dosyasından e-posta adresleri alınırken bir hata oluştu: {e}")
        return

    last_sent_email = None

    for receiver_email in receiver_emails:
        if stop_flag:
            log_to_console("E-posta gönderimi durduruldu.")
            break

        remaining = update_daily_limit()
        if remaining <= 0:
            messagebox.showwarning("Limit Aşıldı", "Günlük e-posta gönderim limitinizi aştınız.")
            break

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = receiver_email
        message["Subject"] = subject

        message["X-Priority"] = "1"  # 1: Yüksek öncelik
        message["Importance"] = "High"  # Önemli

        html_body = f"""
        {body}
        <br>
        <img src="cid:signature_image" alt="İmza" style="display: block; margin: 20px 0; width: 500px; height: auto;">
        """
        message.attach(MIMEText(html_body, "html"))

        if signature_file:
            try:
                with open(signature_file, "rb") as img:
                    img_data = img.read()
                image = MIMEImage(img_data)
                image.add_header("Content-ID", "<signature_image>")
                message.attach(image)
            except Exception as e:
                log_to_console(f"İmza Görseli Hatası: Görsel eklenemedi: {e}")

        if attachment_file:
            try:
                with open(attachment_file, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(attachment_file)}")
                message.attach(part)
            except Exception as e:
                log_to_console(f"Ek Dosya Hatası: Ek dosya eklenemedi: {e}")

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(sender_email, password)
                server.send_message(message)
                decrement_daily_limit()
                last_sent_email = receiver_email

                conn = sqlite3.connect(get_database_path())
                cursor = conn.cursor()
                cursor.execute("INSERT INTO email_logs (sent_email) VALUES (?)", (last_sent_email,))
                conn.commit()
                conn.close()

                log_to_console(f"E-posta gönderildi: {receiver_email}")

        except Exception as e:
            log_to_console(f"E-posta Gönderim Hatası ({receiver_email}): {e}")

    log_to_console("Tüm işlemler tamamlandı.")
    return last_sent_email

def stop():
    global stop_flag
    stop_flag = True
    log_to_console("E-posta gönderimi durduruldu.")

def get_emails_from_excel(excel_file):
    wb = openpyxl.load_workbook(excel_file)
    sheet = wb.active
    return [cell.value for cell in sheet['A'] if cell.value]

def mute():
    global is_muted
    if is_muted:
        media_player.setMuted(False)
    else:
        media_player.setMuted(True)
    is_muted = not is_muted

def start_thread():
    global stop_flag
    stop_flag = False
    threading.Thread(target=start, daemon=True).start()

def start():
    sender_email = sender_email_entry.get()
    password = sender_password_entry.get()
    subject = subject_entry.get()
    body = content_text.get("1.0", tk.END).strip()
    attachment_file = ek_dosya_entry.get()
    excel_file = excel_entry.get()
    signature_file = imza_entry.get()

    if not all([sender_email, password, subject, body, excel_file]):
        messagebox.showwarning("Eksik Bilgi", "Lütfen tüm gerekli alanları doldurun.")
        return

    log_to_console("E-posta gönderimi başlatılıyor...")
    send_emails(sender_email, password, subject, body, attachment_file, excel_file, signature_file)

def get_last_sent_email():
    conn = sqlite3.connect(get_database_path())
    cursor = conn.cursor()
    cursor.execute("SELECT sent_email FROM email_logs ORDER BY timestamp DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Henüz gönderilen e-posta yok."

def show_about():
    last_sent_email = get_last_sent_email()
    remaining = update_daily_limit()
    about_window = Toplevel(root)
    about_window.title("Hakkında")
    about_window.geometry("400x300")
    
    about_label = tk.Label(about_window, text="BEST kulübü için yapılmıştır.\n Exceldeki e maillere sırasıyla belirtilen\ne postayı belirtilen imza ve ek \ndosyaları ile gönderir.\n\nVeritabanının sıfırlanması günlük e posta sınırını\n ve son e postanın hangi adrese gönderildiğini sıfırlar.")
    about_label.pack(pady=10)

    last_sent_label = tk.Label(about_window, text=f"En Son Gönderilen E-posta: {last_sent_email}")
    last_sent_label.pack(pady=5)

    remaining_label = tk.Label(about_window, text=f"Günlük Kalan E-posta Hakkı: {remaining}")
    remaining_label.pack(pady=5)

    about_label = tk.Label(about_window, text="alperen tarafından yazılmıştır.\n Bug ve istek güncellemeler için:\nalperen@gokdeniz.tr")
    about_label.pack(pady=10)

def save_config():
    """
    Kullanıcıdan dosya yolu alarak mevcut ayarları bir JSON dosyasına kaydeder.
    """
    config = {
        "sender_email": sender_email_entry.get(),
        "password": sender_password_entry.get(),
        "subject": subject_entry.get(),
        "body": content_text.get("1.0", tk.END).strip(),
        "attachment_file": ek_dosya_entry.get(),
        "signature_file": imza_entry.get(),
        "excel_file": excel_entry.get()
    }
    
    filepath = filedialog.asksaveasfilename(
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json")],
        title="Konfigürasyon Dosyasını Kaydet"
    )
    if filepath:
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            messagebox.showinfo("Başarılı", "Konfigürasyon kaydedildi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Konfigürasyon kaydedilemedi: {str(e)}")

def load_config():
    """
    Kullanıcıdan dosya yolu alarak bir JSON yapılandırmasını yükler ve GUI alanlarını doldurur.
    """
    filepath = filedialog.askopenfilename(
        filetypes=[("JSON Files", "*.json")],
        title="Konfigürasyon Dosyasını Yükle"
    )
    if filepath:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Alanları doldur
            sender_email_entry.delete(0, tk.END)
            sender_email_entry.insert(0, config.get("sender_email", ""))
            
            sender_password_entry.delete(0, tk.END)
            sender_password_entry.insert(0, config.get("password", ""))
            
            subject_entry.delete(0, tk.END)
            subject_entry.insert(0, config.get("subject", ""))
            
            content_text.delete("1.0", tk.END)
            content_text.insert("1.0", config.get("body", ""))
            
            ek_dosya_entry.delete(0, tk.END)
            ek_dosya_entry.insert(0, config.get("attachment_file", ""))
            
            imza_entry.delete(0, tk.END)
            imza_entry.insert(0, config.get("signature_file", ""))
            
            excel_entry.delete(0, tk.END)
            excel_entry.insert(0, config.get("excel_file", ""))
            
            messagebox.showinfo("Başarılı", "Konfigürasyon yüklendi!")
        except Exception as e:
            messagebox.showerror("Hata", f"Konfigürasyon yüklenemedi: {str(e)}")

def show_help():
    help_window = Toplevel(root)
    help_window.title("Rehber")
    help_window.geometry("600x500")

    help_label = tk.Label(help_window, text="Burada uygulamanın detaylı bir şekilde nasıl kullanılacağı yazılmıştır.\n İlk önce e postaların hangi e posta adresinden gönderileceğini belirleyin.\n Gönderici e posta kutucuğuna belirlediğiniz e postayı yazın.\nŞimdi uygulama şifresi almanız gerekecek. \nhttps://myaccount.google.com/apppasswords adresine gidip bir uygulama şifresi alın.\nNOT: Google hesabınızda 2 aşamalı doğrulamanın aktif olması gerekmektedir.\n Uygulama oluşturun ismine istediğinizi girin ve şifrenizi kopyalayıp o kutucuğa yapıştırın.\nKonu zaten normal e maillerdeki başlık kısmı. E posta içeriği ise ana yazmak istediğiniz şey.\n Bunu HTML olarak yazarsanız daha çok kişiselleştirme yapabilirsiniz.(font,boyut vb.)\n Örnek HTML dosyasını https://nigga.tr/ornek.txt adresinden bulabilirsiniz.\n Yazanları sadece kopyalayıp E posta içeriği yazan yere yapıştrın.\n Ek dosyayı seçin. Örneğin BEST ISTANBUL BOGAZICI.pdf.\n İmza görselini seçin. Örneğin imza.png.\n Alıcı e postaların bulunduğu excel dosyasını seçin.\nNOT: Uygulama şu an sadece A sütununda bulunan değerlere e posta atıyor.\n Yani excel dosyanızı buna göre şekillendirmeniz gerek.\n Ya da eski excel dosyasındaki e posta satırlarını kopyalayıp \nyeni bir excel dosyasının A sütununa yapıştırabilirsiniz.\nBaşlat tuşu e posta gönderimini başlatır. Başlatmadan önce konsolun açık olması tercihimdir. \nKonsoldan detaylı bilgi öğrenebilirsiniz. \nE posta gönderim işlemini durdurmak isterseniz Durdur tuşuna basın.\n Uygulama son gönderilen e posta kime gönderilmiş kaydını tutar.\n Durdurduktan sonra tekrar başlatmak isterseniz lütfen hakkında kısmından \n en son e posta kime gönderilmiş bakın ve o dahil önceki e postaları excel dosyasından silin.\n Uygulama tekrar açıldığında boşlukları doldurmaya gerek kalmasın diye config kaydedip yükleyebilirsiniz.\n\n Eklenecekler:\nUygulamanın durdurulduktan sonra kaldığı yerden devam etmesi.")
    help_label.pack(pady=20)

def reset_database():
    try:
        # Veritabanını sıfırlama işlemleri
        connection = sqlite3.connect(get_database_path())  # Veritabanı dosyasının adı
        cursor = connection.cursor()

        cursor.execute("UPDATE email_logs SET sent_email = NULL")


        # daily_limit tablosundaki remaining değerlerini sıfırlama
        cursor.execute("UPDATE daily_limit SET remaining = 300")

        connection.commit()
        connection.close()

        # Ekrandaki tüm giriş kutularını temizleme
        sender_email_entry.delete(0, tk.END)
        sender_password_entry.delete(0, tk.END)
        subject_entry.delete(0, tk.END)
        content_text.delete("1.0", tk.END)  # Text widget için başlangıçtan sonuna kadar silme
        ek_dosya_entry.delete(0, tk.END)
        imza_entry.delete(0, tk.END)
        excel_entry.delete(0, tk.END)

        messagebox.showinfo("Başarılı", "Veritabanı ve ekran girişleri sıfırlandı!")
    except Exception as e:
        messagebox.showerror("Hata", f"Bir hata oluştu: {str(e)}")

def next_song():
    global current_song_index
    # Sonraki şarkıya geçiş, sona gelince başa dön
    current_song_index = (current_song_index + 1) % len(song_list)
    play_song(current_song_index)

def previous_song():
    global current_song_index
    # Önceki şarkıya geçiş, başa gelince sona dön
    current_song_index = (current_song_index - 1) % len(song_list)
    play_song(current_song_index)

def get_resource_path(resource_name):
    try:
        return pkg_resources.resource_filename(__name__, resource_name)
    except Exception:
        return resource_name  # For local debugging without packaging

def resource_path(relative_path):
    """Derslerin pyinstaller ile çalışmasını sağlamak için dosya yolunu ayarlar."""
    try:
        # PyInstaller ile çalışırken geçici bir dizin oluşturur
        base_path = sys._MEIPASS
    except Exception:
        # Normal geliştirme sürecinde dosya yolunu ayarlamak
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)


# Initialize Database
init_database()

# Create GUI
root = tk.Tk()
root.title("BEST KULÜBÜ CONFİDENTİAL MAİL TACİZCİSİ")
root.iconbitmap(resource_path("logo.ico"))
current_song_var = tk.StringVar()

# Initialize and play first song automatically
play_song(0)


# Gönderici E-posta ve Şifre
sender_email_label = tk.Label(root, text="Gönderici E-posta:")
sender_email_label.grid(row=0, column=0, sticky="w", padx=5, pady=5)

sender_email_entry = tk.Entry(root, width=30)
sender_email_entry.grid(row=0, column=1, padx=5, pady=5)

sender_password_label = tk.Label(root, text="Uygulama Şifresi:")
sender_password_label.grid(row=0, column=2, sticky="w", padx=5, pady=5)

sender_password_entry = tk.Entry(root, width=30, show="*")
sender_password_entry.grid(row=0, column=3, padx=5, pady=5)

# Hakkında ve Nasıl Kullanılır
about_button = tk.Button(root, text="Hakkında", width=12, command=show_about)
about_button.grid(row=0, column=4, padx=5, pady=5)

help_button = tk.Button(root, text="Nasıl Kullanılır", width=12, command=show_help)
help_button.grid(row=0, column=5, padx=5, pady=5)

# Mute Button
mute_button = tk.Button(root, text="🔇", command=mute, width=3, height=1)
mute_button.grid(row=0, column=6, padx=5, pady=5)

# Konu ve Müzik Kontrolleri
subject_label = tk.Label(root, text="Konu:")
subject_label.grid(row=1, column=0, sticky="w", padx=5, pady=5)

subject_entry = tk.Entry(root, width=30)
subject_entry.grid(row=1, column=1, padx=5, pady=5)

current_song_label = tk.Label(root, text="Şu Anda Çalıyor:")
current_song_label.grid(row=1, column=2, sticky="w", padx=5, pady=5)

current_song_entry = tk.Entry(root, width=30, textvariable=current_song_var, state="normal", disabledbackground="white", disabledforeground="black")
current_song_entry.grid(row=1, column=3, padx=5, pady=5)

# Mouse etkileşimini engelleme
current_song_entry.bind("<Button-1>", lambda e: "break")

previous_button = tk.Button(root, text="⏮ Önceki", command=previous_song)
previous_button.grid(row=1, column=4, padx=5, pady=5)

next_button = tk.Button(root, text="Sonraki ⏭", command=next_song)
next_button.grid(row=1, column=5, padx=5, pady=5)

# HTML İçerik
content_label = tk.Label(root, text="E-posta İçeriği (HTML):")
content_label.grid(row=2, column=0, sticky="w", padx=5, pady=5)

content_text = tk.Text(root, height=10, width=80)
content_text.grid(row=3, column=0, columnspan=6, padx=5, pady=5)

# Ek Dosya ve İmza Dosyası
file_label = tk.Label(root, text="Ek Dosya:")
file_label.grid(row=4, column=0, sticky="w", padx=5, pady=5)

ek_dosya_entry = tk.Entry(root, width=50)
ek_dosya_entry.grid(row=4, column=1, columnspan=2, padx=5, pady=5)

file_button = tk.Button(root, text="Dosya Seç", command=lambda: select_file(ek_dosya_entry))
file_button.grid(row=4, column=3, padx=5, pady=5)

imza_label = tk.Label(root, text="İmza Görseli:")
imza_label.grid(row=5, column=0, sticky="w", padx=5, pady=5)

imza_entry = tk.Entry(root, width=50)
imza_entry.grid(row=5, column=1, columnspan=2, padx=5, pady=5)

imza_button = tk.Button(root, text="Dosya Seç", command=lambda: select_file(imza_entry))
imza_button.grid(row=5, column=3, padx=5, pady=5)

# Excel Dosyası ve İşlem Butonları
excel_label = tk.Label(root, text="Alıcı E-posta Excel Dosyası:")
excel_label.grid(row=6, column=0, sticky="w", padx=5, pady=5)

excel_entry = tk.Entry(root, width=50)
excel_entry.grid(row=6, column=1, columnspan=2, padx=5, pady=5)

excel_button = tk.Button(root, text="Dosya Seç", command=lambda: select_file(excel_entry))
excel_button.grid(row=6, column=3, padx=5, pady=5)

# Konfigürasyon Butonlarını Düzenleme
save_config_button = tk.Button(root, text="Config Kaydet", command=save_config, width=12)
save_config_button.grid(row=4, column=4, padx=5, pady=5, sticky="e")  # Kaydedicinin üstünde

load_config_button = tk.Button(root, text="Config Yükle", command=load_config, width=12)
load_config_button.grid(row=4, column=5, padx=5, pady=5)



# Sıfırla Butonu
reset_button = tk.Button(root, text="Sıfırla", command=reset_database, width=12)
reset_button.grid(row=6, column=4, padx=5, pady=5)

start_button = tk.Button(root, text="Başlat", command=start_thread, width=12)
start_button.grid(row=5, column=4, padx=5, pady=5, sticky="e")

stop_button = tk.Button(root, text="Durdur", command=stop, width=12)
stop_button.grid(row=5, column=5, padx=5, pady=5)

# Console Output
console_button = tk.Button(root, text="Konsolu Aç", command=open_console, width=12)
console_button.grid(row=3, column=5, padx=5, pady=5)

exit_button = tk.Button(root, text="Çıkış", command=root.quit, width=12)
exit_button.grid(row=6, column=5, padx=5, pady=5)

# Start the Tkinter event loop
root.mainloop()
