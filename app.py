import pyodbc
import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw, ImageFont
import os
import threading
import queue
import time
import shutil

resim_cache = {}
is_kuyrugu = queue.Queue()

RESIM_KLASORU = "karakter_resimleri"
if not os.path.exists(RESIM_KLASORU):
    os.makedirs(RESIM_KLASORU)

YAZAR_SIFRE = "1234"

# ==========================================
# RESİM YARDIMCI FONKSİYONLAR
# ==========================================

def akilli_resim_url_bul(karakter_adi):
    for uzanti in ['.jpg', '.jpeg', '.png', '.webp']:
        dosya_yolu = os.path.join(RESIM_KLASORU, f"{karakter_adi}{uzanti}")
        if os.path.exists(dosya_yolu):
            return dosya_yolu
    return None

def placeholder_resim_olustur(isim, boyut):
    try:
        w, h = boyut
        img = Image.new("RGB", (w, h), color="#1E293B")
        draw = ImageDraw.Draw(img)
        harf = isim[0].upper() if isim else "?"
        try:
            font = ImageFont.truetype("arial.ttf", min(w, h) // 2)
        except:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), harf, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(((w - tw) / 2, (h - th) / 2), harf, fill="#94A3B8", font=font)
        draw.rectangle([0, 0, w - 1, h - 1], outline="#334155", width=2)
        return img
    except:
        return Image.new("RGB", boyut, color="#1E293B")

def kuyruk_isleyici():
    global resim_cache
    while True:
        karakter_adi, _, label_objesi, boyut = is_kuyrugu.get()
        try:
            if label_objesi.winfo_exists():
                if karakter_adi in resim_cache:
                    label_objesi.configure(image=resim_cache[karakter_adi], text="")
                else:
                    yerel_yol = akilli_resim_url_bul(karakter_adi)
                    if yerel_yol:
                        img_data = Image.open(yerel_yol).convert("RGB").resize(boyut, Image.LANCZOS)
                        img_ctk = ctk.CTkImage(light_image=img_data, size=boyut)
                        resim_cache[karakter_adi] = img_ctk
                        if label_objesi.winfo_exists():
                            label_objesi.configure(image=img_ctk, text="")
                    else:
                        placeholder = placeholder_resim_olustur(karakter_adi, boyut)
                        img_ctk = ctk.CTkImage(light_image=placeholder, size=boyut)
                        if label_objesi.winfo_exists():
                            label_objesi.configure(image=img_ctk, text="")
            time.sleep(0.01)
        except Exception as ex:
            print("Resim yükleme hatası:", ex)
            if label_objesi.winfo_exists():
                label_objesi.configure(text="👤", font=("Helvetica", 32))
        finally:
            is_kuyrugu.task_done()

threading.Thread(target=kuyruk_isleyici, daemon=True).start()

def arka_planda_resim_yukle(karakter_adi, resim_url, label_objesi, boyut):
    is_kuyrugu.put((karakter_adi, resim_url, label_objesi, boyut))

def resim_sec_ve_kaydet(karakter_adi_var, onizleme_label=None):
    isim = karakter_adi_var.get().strip() if hasattr(karakter_adi_var, 'get') else str(karakter_adi_var)
    if not isim:
        messagebox.showwarning("Uyarı", "Lütfen önce karakter ismini girin.")
        return
    dosya_yolu = filedialog.askopenfilename(
        title="Karakter Resmi Seç",
        filetypes=[("Resim Dosyaları", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"), ("Tüm Dosyalar", "*.*")]
    )
    if not dosya_yolu:
        return
    uzanti = os.path.splitext(dosya_yolu)[1].lower()
    hedef_yol = os.path.join(RESIM_KLASORU, f"{isim}{uzanti}")
    try:
        for eski in ['.jpg', '.jpeg', '.png', '.webp']:
            eski_yol = os.path.join(RESIM_KLASORU, f"{isim}{eski}")
            if os.path.exists(eski_yol) and eski_yol != hedef_yol:
                os.remove(eski_yol)
        shutil.copy2(dosya_yolu, hedef_yol)
        if isim in resim_cache:
            del resim_cache[isim]
        messagebox.showinfo("Başarılı", f"'{isim}' için resim kaydedildi!\n📁 {hedef_yol}")
        if onizleme_label:
            onizleme_label.configure(text="⏳")
            arka_planda_resim_yukle(isim, "", onizleme_label, (160, 210))
    except Exception as e:
        messagebox.showerror("Hata", f"Resim kaydedilemedi:\n{e}")

# ==========================================
# VERİTABANI İŞLEMLERİ
# ==========================================
def baglanti_kur():
    try:
        return pyodbc.connect(r'DRIVER={SQL Server};SERVER=PARS\SQLEXPRESS;DATABASE=KarakterEvreni;Trusted_Connection=yes;')
    except Exception as e:
        messagebox.showerror("Hata", f"Veritabanı bağlantı hatası:\n{e}")
        return None

def listeleri_getir(sorgu, params=()):
    conn = baglanti_kur()
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute(sorgu, params)
        return cursor.fetchall()
    except:
        return []
    finally:
        conn.close()

def karakterleri_getir_by_evren(evren_adi):
    if "Soul Land" in evren_adi or "Douluo Dalu" in evren_adi:
        sorgu = "SELECT * FROM vw_KarakterDetay WHERE EvrenAdi LIKE '%Soul Land%' OR EvrenAdi LIKE '%Douluo Dalu%'"
        parametreler = ()
    else:
        sorgu = "SELECT * FROM vw_KarakterDetay WHERE EvrenAdi = ?"
        parametreler = (evren_adi,)

    conn = baglanti_kur()
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute(sorgu, parametreler)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except:
        return []
    finally:
        conn.close()

def iliskileri_getir(karakter_id):
    return listeleri_getir("EXEC sp_KarakterIliskileriniGetir @KarakterID = ?", (karakter_id,))

def yeni_karakter_ekle_sql_ile(isim, unvan, evren_id, grup_id, yas, cinsiyet, boy, nitelik, guc, cikis, onem, dogum, silah, zayiflik, amac, lore):
    conn = baglanti_kur()
    if not conn: return False
    cursor = conn.cursor()
    try:
        conn.autocommit = False
        sorgu = """INSERT INTO Karakterler
                   (KarakterAdi, Unvan, EvrenID, GrupID, Yas, Cinsiyet, Boy, OzelNitelik, GucSeviyesi, IlkOrtayaCikis, EvrenOnemi, DogumYeri, AnaSilah, Zayiflik, AmacIdeoloji, Lore)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor.execute(sorgu, (isim, unvan, evren_id, grup_id, yas, cinsiyet, boy, nitelik, guc, cikis, onem, dogum, silah, zayiflik, amac, lore))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("Ekleme Hatası:", e)
        return False
    finally:
        conn.close()

def karakter_guncelle_sql(karakter_id, isim, unvan, evren_id, grup_id, yas, cinsiyet, boy, nitelik, guc, cikis, onem, dogum, silah, zayiflik, amac, lore):
    conn = baglanti_kur()
    if not conn: return False
    cursor = conn.cursor()
    try:
        conn.autocommit = False
        sorgu = """UPDATE Karakterler SET
                                          KarakterAdi=?, Unvan=?, EvrenID=?, GrupID=?, Yas=?, Cinsiyet=?, Boy=?,
                                          OzelNitelik=?, GucSeviyesi=?, IlkOrtayaCikis=?, EvrenOnemi=?,
                                          DogumYeri=?, AnaSilah=?, Zayiflik=?, AmacIdeoloji=?, Lore=?
                   WHERE KarakterID=?"""
        cursor.execute(sorgu, (isim, unvan, evren_id, grup_id, yas, cinsiyet, boy, nitelik, guc, cikis, onem, dogum, silah, zayiflik, amac, lore, karakter_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("Güncelleme Hatası:", e)
        return False
    finally:
        conn.close()

def karakter_sil_sql(karakter_id):
    conn = baglanti_kur()
    if not conn: return False
    cursor = conn.cursor()
    try:
        conn.autocommit = False
        cursor.execute("DELETE FROM Karakterler WHERE KarakterID=?", (karakter_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("Silme Hatası:", e)
        return False
    finally:
        conn.close()

def evren_istatistik_getir():
    conn = baglanti_kur()
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM vw_EvrenIstatistik ORDER BY ToplamKarakter DESC")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print("İstatistik hatası:", e)
        return []
    finally:
        conn.close()

def silinen_karakterleri_getir():
    conn = baglanti_kur()
    if not conn: return []
    cursor = conn.cursor()
    try:
        cursor.execute("EXEC sp_SilinenKarakterleriGetir")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print("Silinen karakter hatası:", e)
        return []
    finally:
        conn.close()

def karakter_geri_yukle_sql(log_id):
    conn = baglanti_kur()
    if not conn: return False
    cursor = conn.cursor()
    try:
        conn.autocommit = False
        cursor.execute("EXEC sp_KarakterGeriYukle @LogID = ?", (log_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        print("Geri yükleme hatası:", e)
        return False
    finally:
        conn.close()

# ==========================================
# ARAYÜZ KURULUMU
# ==========================================
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("dark-blue")

app = ctk.CTk()
app.geometry("1350x850")
app.title("Çoklu Evren Gelişmiş Arşiv Sistemi")

ana_menu_frame    = ctk.CTkFrame(app, fg_color="transparent")
yazar_frame       = ctk.CTkFrame(app, fg_color="transparent")
duzenle_frame     = ctk.CTkFrame(app, fg_color="transparent")
silinen_frame     = ctk.CTkFrame(app, fg_color="transparent")
istatistik_frame  = ctk.CTkFrame(app, fg_color="transparent")
okur_evren_frame  = ctk.CTkFrame(app, fg_color="transparent")
okur_galeri_frame = ctk.CTkFrame(app, fg_color="transparent")
okur_wiki_frame   = ctk.CTkFrame(app, fg_color="transparent")

evren_buton_alani = None
aktif_evren = ""
aktif_evren_karakterleri = []
aktif_wiki_karakter = {}

def ekrani_temizle():
    for f in (ana_menu_frame, yazar_frame, duzenle_frame, silinen_frame,
              istatistik_frame, okur_evren_frame, okur_galeri_frame, okur_wiki_frame):
        f.pack_forget()

def sayfayi_ac_ana_menu(): ekrani_temizle(); ana_menu_frame.pack(fill="both", expand=True)

# ==========================================
# ŞİFRE KORUMALI YAZAR GİRİŞİ
# ==========================================
def sifre_dialogu_ac():
    dialog = ctk.CTkToplevel(app)
    dialog.title("Yazar Girişi")
    dialog.geometry("360x220")
    dialog.resizable(False, False)
    dialog.grab_set()
    dialog.focus()

    ctk.CTkLabel(dialog, text="🔐 Yazar Paneli", font=("Helvetica", 20, "bold"), text_color="#172554").pack(pady=(30, 8))
    ctk.CTkLabel(dialog, text="Devam etmek için şifreyi girin:", font=("Helvetica", 13), text_color="#475569").pack()

    sifre_giris = ctk.CTkEntry(dialog, placeholder_text="Şifre", show="●", width=220, height=38, font=("Helvetica", 14))
    sifre_giris.pack(pady=14)
    sifre_giris.focus()

    hata_lbl = ctk.CTkLabel(dialog, text="", font=("Helvetica", 12), text_color="#DC2626")
    hata_lbl.pack()

    def kontrol(event=None):
        if sifre_giris.get() == YAZAR_SIFRE:
            dialog.destroy()
            ekrani_temizle()
            yazar_frame.pack(fill="both", expand=True)
        else:
            hata_lbl.configure(text="❌ Hatalı şifre, tekrar deneyin.")
            sifre_giris.delete(0, "end")

    sifre_giris.bind("<Return>", kontrol)
    ctk.CTkButton(dialog, text="Giriş Yap", fg_color="#1E293B", font=("Helvetica", 13, "bold"), height=36, width=220, command=kontrol).pack(pady=(4, 0))

# ==========================================
# OKUR EVREN SEÇİM EKRANI (GERİ DÖNÜŞ BUTONLU)
# ==========================================
def sayfayi_ac_okur_evren():
    ekrani_temizle()
    okur_evren_frame.pack(fill="both", expand=True)

    for w in okur_evren_frame.winfo_children():
        w.destroy()

    # OKUR PANELİ ÜST BAR (ANA MENÜ BUTONU DAHİL)
    okur_ust_bar = ctk.CTkFrame(okur_evren_frame, fg_color="#0A192F", height=55)
    okur_ust_bar.pack(fill="x", side="top")
    okur_ust_bar.pack_propagate(False)

    ctk.CTkButton(okur_ust_bar, text="← Ana Menü", command=sayfayi_ac_ana_menu, fg_color="#334155", width=110).pack(side="left", padx=10, pady=10)
    ctk.CTkLabel(okur_ust_bar, text="🌌  Çoklu Evren Gezgini", font=("Helvetica", 18, "bold"), text_color="white").pack(side="left", padx=15, pady=12)

    global evren_buton_alani
    evren_buton_alani = ctk.CTkScrollableFrame(okur_evren_frame, fg_color="transparent")
    evren_buton_alani.pack(fill="both", expand=True, padx=40, pady=20)

    ctk.CTkLabel(evren_buton_alani, text="Keşfetmek İstediğiniz Evreni Seçin", font=("Helvetica", 28, "bold"), text_color="#172554").grid(row=0, column=0, columnspan=3, pady=(10, 30))

    evrenler = listeleri_getir("SELECT DISTINCT EvrenAdi FROM Evrenler")
    row_idx, col_idx = 1, 0
    for e in evrenler:
        evren_adi = e[0]
        btn = ctk.CTkButton(evren_buton_alani, text=str(evren_adi), font=("Helvetica", 18, "bold"), height=90, width=360, command=lambda ad=evren_adi: sayfayi_ac_okur_galeri(ad))
        btn.grid(row=row_idx, column=col_idx, padx=20, pady=20)
        col_idx += 1
        if col_idx == 3:
            col_idx = 0
            row_idx += 1

def sayfayi_ac_okur_galeri(evren_adi):
    global aktif_evren, aktif_evren_karakterleri
    aktif_evren = evren_adi
    ekrani_temizle()
    okur_galeri_frame.pack(fill="both", expand=True)
    galeri_baslik.configure(text=f"{evren_adi} — Karakter Galerisi")
    arama_cubugu.delete(0, 'end')
    aktif_evren_karakterleri = karakterleri_getir_by_evren(evren_adi)
    galeriyi_yenile(aktif_evren_karakterleri)

def karakter_ara(event):
    arama = arama_cubugu.get().lower().strip()
    if not arama: galeriyi_yenile(aktif_evren_karakterleri); return
    filtrelenmis = [k for k in aktif_evren_karakterleri if arama in k.get('KarakterAdi', '').lower()]
    galeriyi_yenile(filtrelenmis)

def galeriyi_yenile(gosterilecek_karakterler):
    for w in galeri_icerik.winfo_children(): w.destroy()
    if not gosterilecek_karakterler:
        ctk.CTkLabel(galeri_icerik, text="Karakter bulunamadı.", font=("Helvetica", 18), text_color="#64748B").pack(pady=60)
        return
    row, col = 0, 0
    for k_veri in gosterilecek_karakterler:
        isim = k_veri.get('KarakterAdi', 'Bilinmeyen')
        onem = k_veri.get('EvrenOnemi', '')
        kart = ctk.CTkFrame(galeri_icerik, fg_color="#F1F5F9", corner_radius=12, border_width=1, border_color="#CBD5E1")
        kart.grid(row=row, column=col, padx=20, pady=20)

        resim_cerceve = ctk.CTkFrame(kart, fg_color="#CBD5E1", corner_radius=8, width=182, height=242)
        resim_cerceve.pack(pady=(12, 5), padx=12)
        resim_cerceve.pack_propagate(False)

        lbl_resim = ctk.CTkLabel(resim_cerceve, text="⏳", width=180, height=240, font=("Helvetica", 28), text_color="#94A3B8")
        lbl_resim.pack(fill="both", expand=True)
        arka_planda_resim_yukle(isim, "", lbl_resim, (180, 240))

        badge_renk = {"Ana Karakter": "#2563EB", "Kötü Karakter (Antagonist)": "#DC2626", "Akıl Hocası (Mentor)": "#7C3AED", "Yan Karakter": "#475569"}.get(onem, "#475569")
        if onem:
            ctk.CTkLabel(kart, text=onem, font=("Helvetica", 10, "bold"), text_color="white", fg_color=badge_renk, corner_radius=6).pack(pady=(2, 0), padx=12, fill="x")

        ctk.CTkButton(kart, text=isim, font=("Helvetica", 15, "bold"), fg_color="#1E293B", hover_color="#334155", height=38, command=lambda v=k_veri: sayfayi_ac_wiki(v)).pack(pady=(4, 12), padx=12, fill="x")
        col += 1
        if col == 4: col = 0; row += 1

# ==========================================
# KARŞILAMA EKRANI
# ==========================================
ctk.CTkLabel(ana_menu_frame, text="Çoklu Evren Kütüphanesine Hoş Geldiniz", font=("Helvetica", 36, "bold"), text_color="#172554").pack(pady=(200, 50))
ctk.CTkButton(ana_menu_frame, text="Yazar (Admin) Girişi", width=300, height=60, font=("Helvetica", 18, "bold"), fg_color="#1E293B", command=sifre_dialogu_ac).pack(pady=15)
ctk.CTkButton(ana_menu_frame, text="Okur (Ziyaretçi) Girişi", width=300, height=60, font=("Helvetica", 18, "bold"), fg_color="#2563EB", command=sayfayi_ac_okur_evren).pack(pady=15)

# ==========================================
# YAZAR FORMU (YENİ EKLEME)
# ==========================================
yazar_ust_bar = ctk.CTkFrame(yazar_frame, fg_color="#0A192F", height=55)
yazar_ust_bar.pack(fill="x", side="top")
yazar_ust_bar.pack_propagate(False)
ctk.CTkButton(yazar_ust_bar, text="← Ana Menü", command=sayfayi_ac_ana_menu, fg_color="#334155", width=110).pack(side="left", padx=10, pady=10)
ctk.CTkLabel(yazar_ust_bar, text="⚙️  Yazar Paneli", font=("Helvetica", 20, "bold"), text_color="white").pack(side="left", padx=15, pady=12)
ctk.CTkButton(yazar_ust_bar, text="📊 Evren İstatistikleri", fg_color="#7C3AED", hover_color="#6D28D9", font=("Helvetica", 13, "bold"), height=34, width=175, command=lambda: sayfayi_ac_istatistik()).pack(side="right", padx=(5, 15), pady=10)
ctk.CTkButton(yazar_ust_bar, text="🗂 Silinmiş Karakterler", fg_color="#B45309", hover_color="#92400E", font=("Helvetica", 13, "bold"), height=34, width=190, command=lambda: sayfayi_ac_silinen()).pack(side="right", padx=5, pady=10)

ctk.CTkLabel(yazar_frame, text="Çoklu Evren Derin Lore Kayıt Girişi", font=("Helvetica", 22, "bold"), text_color="#172554").pack(pady=(8, 6))

form_alani = ctk.CTkScrollableFrame(yazar_frame, fg_color="#F8FAFC", border_width=1, border_color="#E2E8F0", corner_radius=10, height=620)
form_alani.pack(fill="both", expand=True, padx=50, pady=5)

satir1 = ctk.CTkFrame(form_alani, fg_color="transparent")
satir1.pack(fill="x", pady=5)
isim_grid = ctk.CTkEntry(satir1, placeholder_text="Karakter İsmi", width=180)
isim_grid.pack(side="left", padx=3)
unvan_giris = ctk.CTkEntry(satir1, placeholder_text="Ünvan", width=180)
unvan_giris.pack(side="left", padx=3)

evren_listesi_raw = listeleri_getir("SELECT EvrenID, EvrenAdi FROM Evrenler")
grup_listesi_raw  = listeleri_getir("SELECT GrupID, GrupAdi FROM Gruplar")

evren_secim = ctk.CTkComboBox(satir1, values=[e[1] for e in evren_listesi_raw] if evren_listesi_raw else ["Yok"], width=150)
evren_secim.pack(side="left", padx=3)
grup_secim  = ctk.CTkComboBox(satir1, values=[g[1] for g in grup_listesi_raw] if grup_listesi_raw else ["Yok"], width=180)
grup_secim.pack(side="left", padx=3)

satir2 = ctk.CTkFrame(form_alani, fg_color="transparent")
satir2.pack(fill="x", pady=5)
yas_giris      = ctk.CTkEntry(satir2, placeholder_text="Yaş", width=100)
yas_giris.pack(side="left", padx=3)
cinsiyet_giris = ctk.CTkEntry(satir2, placeholder_text="Cinsiyet", width=100)
cinsiyet_giris.pack(side="left", padx=3)
boy_giris      = ctk.CTkEntry(satir2, placeholder_text="Boy", width=100)
boy_giris.pack(side="left", padx=3)
cikis_giris    = ctk.CTkEntry(satir2, placeholder_text="İlk Ortaya Çıkış", width=150)
cikis_giris.pack(side="left", padx=3)
onem_secim     = ctk.CTkComboBox(satir2, values=["Ana Karakter", "Yan Karakter", "Kötü Karakter (Antagonist)", "Akıl Hocası (Mentor)"], width=200)
onem_secim.pack(side="left", padx=3)

satir3 = ctk.CTkFrame(form_alani, fg_color="transparent")
satir3.pack(fill="x", pady=5)
dogum_giris    = ctk.CTkEntry(satir3, placeholder_text="Doğum Yeri / Köken", width=220)
dogum_giris.pack(side="left", padx=3)
silah_giris    = ctk.CTkEntry(satir3, placeholder_text="Kullandığı Ana Silah/Ekipman", width=220)
silah_giris.pack(side="left", padx=3)
zayiflik_giris = ctk.CTkEntry(satir3, placeholder_text="En Büyük Zayıflığı", width=220)
zayiflik_giris.pack(side="left", padx=3)

satir4 = ctk.CTkFrame(form_alani, fg_color="transparent")
satir4.pack(fill="x", pady=5)
amac_giris  = ctk.CTkEntry(satir4, placeholder_text="Karakterin Amacı / İdeolojisi", width=670)
amac_giris.pack(side="left", padx=3)
dovus_giris = ctk.CTkEntry(satir4, placeholder_text="Özel Nitelik / Güç Türü", width=300)
dovus_giris.pack(side="left", padx=3)

slider_frame = ctk.CTkFrame(form_alani, fg_color="transparent")
slider_frame.pack(fill="x", pady=10)
guc_label = ctk.CTkLabel(slider_frame, text="Güç Seviyesi: 50", font=("Helvetica", 14, "bold"))
guc_label.pack(side="left", padx=10)
guc_slider = ctk.CTkSlider(slider_frame, from_=1, to=150, command=lambda d: guc_label.configure(text=f"Güç Seviyesi: {int(d)}"), width=400)
guc_slider.set(50)
guc_slider.pack(side="left", padx=20)

ctk.CTkLabel(form_alani, text="Gelişmiş Biyografi / Lore Hikayesi:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=5)
lore_giris = ctk.CTkTextbox(form_alani, width=1100, height=120, font=("Helvetica", 12))
lore_giris.pack(padx=5, pady=(0, 10))

resim_sekme = ctk.CTkFrame(form_alani, fg_color="#EFF6FF", border_width=1, border_color="#BFDBFE", corner_radius=8)
resim_sekme.pack(fill="x", padx=5, pady=8)
ctk.CTkLabel(resim_sekme, text="🖼  Karakter Fotoğrafı", font=("Helvetica", 13, "bold"), text_color="#1E3A8A").pack(anchor="w", padx=15, pady=(10, 4))

resim_icerik_frm = ctk.CTkFrame(resim_sekme, fg_color="transparent")
resim_icerik_frm.pack(fill="x", padx=15, pady=(0, 12))

form_onizleme = ctk.CTkLabel(resim_icerik_frm, text="👤", width=80, height=100, font=("Helvetica", 30), fg_color="#CBD5E1", corner_radius=6)
form_onizleme.pack(side="left", padx=(0, 15))

resim_bilgi = ctk.CTkFrame(resim_icerik_frm, fg_color="transparent")
resim_bilgi.pack(side="left", fill="x", expand=True)
ctk.CTkLabel(resim_bilgi, text="Desteklenen formatlar: JPG, JPEG, PNG, WEBP\nResim, karakter ismiyle klasöre otomatik kaydedilir.", font=("Helvetica", 11), text_color="#475569", anchor="w", justify="left").pack(anchor="w")
ctk.CTkButton(resim_bilgi, text="📁  Fotoğraf Seç ve Yükle", fg_color="#2563EB", hover_color="#1D4ED8", font=("Helvetica", 13, "bold"), height=36, width=220, command=lambda: resim_sec_ve_kaydet(isim_grid, onizleme_label=form_onizleme)).pack(anchor="w", pady=(8, 0))

def yazar_kaydet_basildi():
    try:
        e_id = [e[0] for e in evren_listesi_raw if e[1] == evren_secim.get()][0]
        g_id = [g[0] for g in grup_listesi_raw if g[1] == grup_secim.get()][0]
        if yeni_karakter_ekle_sql_ile(
                isim_grid.get(), unvan_giris.get(), e_id, g_id,
                yas_giris.get(), cinsiyet_giris.get(), boy_giris.get(),
                dovus_giris.get(), int(guc_slider.get()), cikis_giris.get(), onem_secim.get(),
                dogum_giris.get(), silah_giris.get(), zayiflik_giris.get(),
                amac_giris.get(), lore_giris.get("1.0", "end-1c").strip()
        ):
            messagebox.showinfo("Başarılı", "Derinlemesine Lore Bilgileri Veritabanına Kaydedildi!")
            sayfayi_ac_ana_menu()
        else:
            messagebox.showerror("Hata", "Veritabanına ekleme yapılamadı.")
    except Exception as ex:
        messagebox.showerror("Hata", f"Form Eksikliği: {ex}")

ctk.CTkButton(form_alani, text="💾  Derin Lore Verisini Kaydet", fg_color="#10B981", hover_color="#059669", font=("Helvetica", 14, "bold"), command=yazar_kaydet_basildi).pack(pady=15)

# ==========================================
# DÜZENLEME FORMU (MEVCUT KARAKTERİ GÜNCELLE)
# ==========================================
ctk.CTkButton(duzenle_frame, text="← Wiki'ye Dön", command=lambda: sayfayi_ac_wiki(aktif_wiki_karakter), fg_color="#64748B", width=130).pack(anchor="nw", padx=20, pady=10)
ctk.CTkLabel(duzenle_frame, text="✏️  Karakter Düzenleme", font=("Helvetica", 24, "bold"), text_color="#172554").pack(pady=(0, 10))

duzenle_alani = ctk.CTkScrollableFrame(duzenle_frame, fg_color="#F8FAFC", border_width=1, border_color="#E2E8F0", corner_radius=10, height=620)
duzenle_alani.pack(fill="both", expand=True, padx=50, pady=5)

d_satir1 = ctk.CTkFrame(duzenle_alani, fg_color="transparent")
d_satir1.pack(fill="x", pady=5)
d_isim    = ctk.CTkEntry(d_satir1, placeholder_text="Karakter İsmi", width=180)
d_isim.pack(side="left", padx=3)
d_unvan   = ctk.CTkEntry(d_satir1, placeholder_text="Ünvan", width=180)
d_unvan.pack(side="left", padx=3)
d_evren   = ctk.CTkComboBox(d_satir1, values=[e[1] for e in evren_listesi_raw] if evren_listesi_raw else ["Yok"], width=150)
d_evren.pack(side="left", padx=3)
d_grup    = ctk.CTkComboBox(d_satir1, values=[g[1] for g in grup_listesi_raw] if grup_listesi_raw else ["Yok"], width=180)
d_grup.pack(side="left", padx=3)

d_satir2 = ctk.CTkFrame(duzenle_alani, fg_color="transparent")
d_satir2.pack(fill="x", pady=5)
d_yas      = ctk.CTkEntry(d_satir2, placeholder_text="Yaş", width=100)
d_yas.pack(side="left", padx=3)
d_cinsiyet = ctk.CTkEntry(d_satir2, placeholder_text="Cinsiyet", width=100)
d_cinsiyet.pack(side="left", padx=3)
d_boy      = ctk.CTkEntry(d_satir2, placeholder_text="Boy", width=100)
d_boy.pack(side="left", padx=3)
d_cikis    = ctk.CTkEntry(d_satir2, placeholder_text="İlk Ortaya Çıkış", width=150)
d_cikis.pack(side="left", padx=3)
d_onem     = ctk.CTkComboBox(d_satir2, values=["Ana Karakter", "Yan Karakter", "Kötü Karakter (Antagonist)", "Akıl Hocası (Mentor)"], width=200)
d_onem.pack(side="left", padx=3)

d_satir3 = ctk.CTkFrame(duzenle_alani, fg_color="transparent")
d_satir3.pack(fill="x", pady=5)
d_dogum    = ctk.CTkEntry(d_satir3, placeholder_text="Doğum Yeri / Köken", width=220)
d_dogum.pack(side="left", padx=3)
d_silah    = ctk.CTkEntry(d_satir3, placeholder_text="Ana Silah/Ekipman", width=220)
d_silah.pack(side="left", padx=3)
d_zayiflik = ctk.CTkEntry(d_satir3, placeholder_text="En Büyük Zayıflığı", width=220)
d_zayiflik.pack(side="left", padx=3)

d_satir4 = ctk.CTkFrame(duzenle_alani, fg_color="transparent")
d_satir4.pack(fill="x", pady=5)
d_amac  = ctk.CTkEntry(d_satir4, placeholder_text="Amaç / İdeoloji", width=670)
d_amac.pack(side="left", padx=3)
d_dovus = ctk.CTkEntry(d_satir4, placeholder_text="Özel Nitelik / Güç Türü", width=300)
d_dovus.pack(side="left", padx=3)

d_slider_frame = ctk.CTkFrame(duzenle_alani, fg_color="transparent")
d_slider_frame.pack(fill="x", pady=10)
d_guc_label = ctk.CTkLabel(d_slider_frame, text="Güç Seviyesi: 50", font=("Helvetica", 14, "bold"))
d_guc_label.pack(side="left", padx=10)
d_guc_slider = ctk.CTkSlider(d_slider_frame, from_=1, to=150, command=lambda d: d_guc_label.configure(text=f"Güç Seviyesi: {int(d)}"), width=400)
d_guc_slider.set(50)
d_guc_slider.pack(side="left", padx=20)

ctk.CTkLabel(duzenle_alani, text="Biyografi / Lore:", font=("Helvetica", 12, "bold")).pack(anchor="w", padx=5)
d_lore = ctk.CTkTextbox(duzenle_alani, width=1100, height=140, font=("Helvetica", 12))
d_lore.pack(padx=5, pady=(0, 10))

def duzenle_kaydet_basildi():
    k = aktif_wiki_karakter
    try:
        e_id = [e[0] for e in evren_listesi_raw if e[1] == d_evren.get()][0]
        g_id = [g[0] for g in grup_listesi_raw if g[1] == d_grup.get()][0]
        if karakter_guncelle_sql(
                k.get('KarakterID'), d_isim.get(), d_unvan.get(), e_id, g_id,
                d_yas.get(), d_cinsiyet.get(), d_boy.get(),
                d_dovus.get(), int(d_guc_slider.get()), d_cikis.get(), d_onem.get(),
                d_dogum.get(), d_silah.get(), d_zayiflik.get(),
                d_amac.get(), d_lore.get("1.0", "end-1c").strip()
        ):
            messagebox.showinfo("Başarılı", "Karakter güncellendi!")
            isim = d_isim.get()
            if isim in resim_cache: del resim_cache[isim]
            guncel_liste = karakterleri_getir_by_evren(aktif_evren)
            guncel = next((x for x in guncel_liste if x.get('KarakterID') == k.get('KarakterID')), None)
            if guncel:
                sayfayi_ac_wiki(guncel)
            else:
                sayfayi_ac_okur_galeri(aktif_evren)
        else:
            messagebox.showerror("Hata", "Güncelleme başarısız.")
    except Exception as ex:
        messagebox.showerror("Hata", f"Form hatası: {ex}")

ctk.CTkButton(duzenle_alani, text="💾  Değişiklikleri Kaydet", fg_color="#10B981", hover_color="#059669", font=("Helvetica", 14, "bold"), command=duzenle_kaydet_basildi).pack(pady=15)

def sayfayi_ac_duzenle(k_dict):
    global aktif_wiki_karakter
    aktif_wiki_karakter = k_dict
    ekrani_temizle()
    duzenle_frame.pack(fill="both", expand=True)

    for entry, key in [
        (d_isim, 'KarakterAdi'), (d_unvan, 'Unvan'), (d_yas, 'Yas'),
        (d_cinsiyet,'Cinsiyet'), (d_boy, 'Boy'), (d_cikis, 'IlkOrtayaCikis'),
        (d_dogum, 'DogumYeri'), (d_silah, 'AnaSilah'), (d_zayiflik,'Zayiflik'),
        (d_amac, 'AmacIdeoloji'), (d_dovus, 'OzelNitelik'),
    ]:
        entry.delete(0, "end")
        entry.insert(0, str(k_dict.get(key, '') or ''))

    d_onem.set(k_dict.get('EvrenOnemi', 'Yan Karakter') or 'Yan Karakter')

    evren_adi, grup_adi = k_dict.get('EvrenAdi', ''), k_dict.get('GrupAdi', '')
    if evren_adi in [e[1] for e in evren_listesi_raw]: d_evren.set(evren_adi)
    if grup_adi in [g[1] for g in grup_listesi_raw]: d_grup.set(grup_adi)

    guc_val = k_dict.get('GucSeviyesi', 50)
    try:
        d_guc_slider.set(int(guc_val))
        d_guc_label.configure(text=f"Güç Seviyesi: {int(guc_val)}")
    except:
        d_guc_slider.set(50)

    d_lore.delete("1.0", "end")
    d_lore.insert("1.0", str(k_dict.get('Lore', '') or ''))

# ==========================================
# GALERİ ÜST BARI
# ==========================================
ust_bar_galeri = ctk.CTkFrame(okur_galeri_frame, height=60, fg_color="#0A192F")
ust_bar_galeri.pack(fill="x", side="top")
ctk.CTkButton(ust_bar_galeri, text="← Evrenler", command=sayfayi_ac_okur_evren, fg_color="#334155", width=120).pack(side="left", padx=10, pady=10)
galeri_baslik = ctk.CTkLabel(ust_bar_galeri, text="Karakter Galerisi", font=("Helvetica", 24, "bold"), text_color="white")
galeri_baslik.pack(side="left", padx=20, pady=15)
arama_cubugu = ctk.CTkEntry(ust_bar_galeri, placeholder_text="🔍 Karakter ara...", width=280)
arama_cubugu.pack(side="right", padx=20, pady=15)
arama_cubugu.bind("<KeyRelease>", karakter_ara)
galeri_icerik = ctk.CTkScrollableFrame(okur_galeri_frame, fg_color="transparent")
galeri_icerik.pack(fill="both", expand=True, padx=50, pady=20)

# ==========================================
# WİKİ DETAY SAYFASI
# ==========================================
ust_bar_wiki = ctk.CTkFrame(okur_wiki_frame, height=60, fg_color="#0A192F")
ust_bar_wiki.pack(fill="x", side="top")
ctk.CTkButton(ust_bar_wiki, text="← Galeri", command=lambda: sayfayi_ac_okur_galeri(aktif_evren), fg_color="#334155", width=120).pack(side="left", padx=10, pady=10)
ctk.CTkLabel(ust_bar_wiki, text="Detaylı Ansiklopedi", font=("Helvetica", 24, "bold"), text_color="white").pack(side="left", padx=20, pady=15)

wiki_admin_bar = ctk.CTkFrame(ust_bar_wiki, fg_color="transparent")
wiki_admin_bar.pack(side="right", padx=15, pady=10)

def wiki_sil_basildi():
    if not aktif_wiki_karakter: return
    isim = aktif_wiki_karakter.get('KarakterAdi', '?')
    if messagebox.askyesno("Silme Onayı", f"⚠️  '{isim}' karakterini kalıcı olarak silmek istediğinize emin misiniz?\n\nBu işlem geri alınamaz!"):
        if karakter_sil_sql(aktif_wiki_karakter.get('KarakterID')):
            messagebox.showinfo("Başarılı", f"'{isim}' veritabanından silindi.")
            sayfayi_ac_okur_galeri(aktif_evren)
        else:
            messagebox.showerror("Hata", "Silme işlemi başarısız.\nİlişkili kayıtlar olabilir.")

ctk.CTkButton(wiki_admin_bar, text="✏️  Düzenle", fg_color="#F59E0B", hover_color="#D97706", text_color="#1C1917", font=("Helvetica", 13, "bold"), height=34, width=110, command=lambda: sayfayi_ac_duzenle(aktif_wiki_karakter) if aktif_wiki_karakter else messagebox.showwarning("Uyarı", "Önce bir karakter seçin.")).pack(side="left", padx=(0, 8))
ctk.CTkButton(wiki_admin_bar, text="🗑  Sil", fg_color="#DC2626", hover_color="#B91C1C", font=("Helvetica", 13, "bold"), height=34, width=90, command=wiki_sil_basildi).pack(side="left")

icerik_alani = ctk.CTkFrame(okur_wiki_frame, fg_color="transparent")
icerik_alani.pack(fill="both", expand=True, padx=20, pady=20)

sag_kunye_frame = ctk.CTkScrollableFrame(icerik_alani, width=280, fg_color="#E2E8F0", corner_radius=10)
sag_kunye_frame.pack(side="right", fill="y", expand=False, padx=(10, 0))

orta_hikaye_frame = ctk.CTkScrollableFrame(icerik_alani, fg_color="white", border_width=1, border_color="#E2E8F0")
orta_hikaye_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

wiki_baslik = ctk.CTkLabel(orta_hikaye_frame, text="İsim", font=("Georgia", 32, "bold"), text_color="#1E293B")
wiki_baslik.pack(anchor="w", padx=30, pady=(20, 5))

ideoloji_blogu = ctk.CTkTextbox(orta_hikaye_frame, font=("Helvetica", 13, "italic"), height=60, text_color="#1E3A8A", fg_color="#EFF6FF", border_width=1, border_color="#BFDBFE")
ideoloji_blogu.pack(fill="x", padx=30, pady=10)

wiki_lore = ctk.CTkTextbox(orta_hikaye_frame, font=("Helvetica", 15), text_color="#334155", fg_color="transparent", height=430)
wiki_lore.pack(fill="both", expand=True, padx=30, pady=(5, 10))

alt_medya_bar = ctk.CTkFrame(orta_hikaye_frame, fg_color="#F8FAFC", border_width=1, border_color="#E2E8F0", corner_radius=8)
alt_medya_bar.pack(fill="x", padx=30, pady=(10, 20))
ctk.CTkLabel(alt_medya_bar, text="🎬 İLİŞKİLİ MEDYA VE DOKÜMANTASYONLAR", font=("Helvetica", 11, "bold"), text_color="#475569").pack(anchor="w", padx=15, pady=(5, 2))
kart_kutusu = ctk.CTkFrame(alt_medya_bar, fg_color="transparent")
kart_kutusu.pack(fill="x", padx=10, pady=(0, 8))
ctk.CTkButton(kart_kutusu, text="📺 The Originals Serisi", fg_color="#64748B", text_color="white", height=32, width=180, state="disabled").pack(side="left", padx=5, expand=True)
ctk.CTkButton(kart_kutusu, text="📚 Kronolojik Roman Alıntıları", fg_color="#64748B", text_color="white", height=32, width=180, state="disabled").pack(side="left", padx=5, expand=True)
ctk.CTkButton(kart_kutusu, text="🔗 Çapraz Evren Bağlantısı", fg_color="#64748B", text_color="white", height=32, width=180, state="disabled").pack(side="left", padx=5, expand=True)

kunye_baslik_frame = ctk.CTkFrame(sag_kunye_frame, fg_color="#172554", corner_radius=10)
kunye_baslik_frame.pack(fill="x", padx=10, pady=10)
kunye_isim = ctk.CTkLabel(kunye_baslik_frame, text="İsim", font=("Helvetica", 18, "bold"), text_color="white")
kunye_isim.pack(pady=8)

wiki_resim_cerceve = ctk.CTkFrame(sag_kunye_frame, fg_color="#CBD5E1", corner_radius=10, width=242, height=310)
wiki_resim_cerceve.pack(pady=10, padx=10)
wiki_resim_cerceve.pack_propagate(False)

resim_label_wiki = ctk.CTkLabel(wiki_resim_cerceve, text="")
resim_label_wiki.pack(fill="both", expand=True)

ctk.CTkButton(sag_kunye_frame, text="📁 Fotoğraf Yükle", fg_color="#2563EB", hover_color="#1D4ED8", font=("Helvetica", 12, "bold"), height=32, command=lambda: resim_sec_ve_kaydet(type('obj', (object,), {'get': lambda s: kunye_isim.cget("text")})(), onizleme_label=resim_label_wiki) if kunye_isim.cget("text") != "İsim" else None).pack(padx=10, pady=(0, 6), fill="x")

kunye_detay_frame = ctk.CTkFrame(sag_kunye_frame, fg_color="transparent")
kunye_detay_frame.pack(fill="x", padx=10, pady=5)

def detay_satiri_olustur(parent, baslik):
    satir = ctk.CTkFrame(parent, fg_color="transparent")
    satir.pack(fill="x", pady=2)
    ctk.CTkLabel(satir, text=baslik, font=("Helvetica", 11, "bold"), width=90, anchor="w").pack(side="left")
    deger_label = ctk.CTkLabel(satir, text="-", font=("Helvetica", 11), text_color="#0F172A", anchor="w", wraplength=150)
    deger_label.pack(side="left", fill="x", expand=True)
    return deger_label

lbl_grup     = detay_satiri_olustur(kunye_detay_frame, "Grup / Klan:")
lbl_unvan    = detay_satiri_olustur(kunye_detay_frame, "Unvan:")
lbl_dovus    = detay_satiri_olustur(kunye_detay_frame, "Özel Nitelik:")
lbl_guc      = detay_satiri_olustur(kunye_detay_frame, "Güç Seviyesi:")
lbl_dogum    = detay_satiri_olustur(kunye_detay_frame, "Doğum Yeri:")
lbl_silah    = detay_satiri_olustur(kunye_detay_frame, "Ana Silah:")
lbl_zayiflik = detay_satiri_olustur(kunye_detay_frame, "Zayıflık:")
lbl_cikis    = detay_satiri_olustur(kunye_detay_frame, "İlk Çıkış:")
lbl_onem     = detay_satiri_olustur(kunye_detay_frame, "Evren Rolü:")
lbl_yas      = detay_satiri_olustur(kunye_detay_frame, "Yaş:")
lbl_boy      = detay_satiri_olustur(kunye_detay_frame, "Boy:")

def sayfayi_ac_wiki(k_dict):
    global aktif_wiki_karakter
    aktif_wiki_karakter = k_dict
    ekrani_temizle()
    okur_wiki_frame.pack(fill="both", expand=True)
    isim = k_dict.get('KarakterAdi', '-')

    resim_label_wiki.configure(image=None, text="⏳")
    arka_planda_resim_yukle(isim, "", resim_label_wiki, (240, 308))

    kunye_isim.configure(text=isim)
    lbl_grup.configure(text=k_dict.get('GrupAdi', 'Bağımsız'))
    lbl_unvan.configure(text=k_dict.get('Unvan', '-'))
    lbl_yas.configure(text=k_dict.get('Yas', '-'))
    lbl_boy.configure(text=k_dict.get('Boy', '-'))
    lbl_dovus.configure(text=k_dict.get('OzelNitelik', '-'))
    lbl_guc.configure(text=str(k_dict.get('GucSeviyesi', '-')))
    lbl_cikis.configure(text=k_dict.get('IlkOrtayaCikis', '-'))
    lbl_onem.configure(text=k_dict.get('EvrenOnemi', '-'))
    lbl_dogum.configure(text=k_dict.get('DogumYeri', '-'))
    lbl_silah.configure(text=k_dict.get('AnaSilah', '-'))
    lbl_zayiflik.configure(text=k_dict.get('Zayiflik', '-'))
    wiki_baslik.configure(text=isim)

    ideoloji_blogu.configure(state="normal")
    ideoloji_blogu.delete("1.0", "end")
    ideoloji_blogu.insert("1.0", f"🎯 BAŞLICA AMACI & İDEOLOJİSİ:\n\"{k_dict.get('AmacIdeoloji', 'Bilinmiyor.')}\"")
    ideoloji_blogu.configure(state="disabled")

    tam_metin = f"{k_dict.get('Lore', 'Hikaye verisi bulunamadı.')}\n\n"
    iliskiler = iliskileri_getir(k_dict.get('KarakterID', 0))
    if iliskiler:
        tam_metin += "⚔️ BİLİNEN İLİŞKİLERİ & BAĞLANTILARI:\n"
        for i in iliskiler:
            tam_metin += f"  • {i[0]} : {i[1]}\n"

    wiki_lore.configure(state="normal")
    wiki_lore.delete("1.0", "end")
    wiki_lore.insert("1.0", tam_metin)
    wiki_lore.configure(state="disabled")

# ==========================================
# SİLİNMİŞ KARAKTERLER EKRANI
# ==========================================
def sayfayi_ac_silinen():
    ekrani_temizle()
    silinen_frame.pack(fill="both", expand=True)
    for w in silinen_frame.winfo_children(): w.destroy()

    ust = ctk.CTkFrame(silinen_frame, fg_color="#78350F", height=55)
    ust.pack(fill="x")
    ust.pack_propagate(False)
    ctk.CTkButton(ust, text="← Yazar Paneli", command=lambda: (ekrani_temizle(), yazar_frame.pack(fill="both", expand=True)), fg_color="#92400E", width=130).pack(side="left", padx=10, pady=10)
    ctk.CTkLabel(ust, text="🗂  Silinmiş Karakter Arşivi  (Trigger Logu)", font=("Helvetica", 20, "bold"), text_color="white").pack(side="left", padx=15, pady=12)

    veriler = silinen_karakterleri_getir()
    if not veriler:
        ctk.CTkLabel(silinen_frame, text="Henüz silinmiş karakter kaydı yok.", font=("Helvetica", 18), text_color="#92400E").pack(pady=80)
        return

    baslik_satir = ctk.CTkFrame(silinen_frame, fg_color="#1C1917", height=36)
    baslik_satir.pack(fill="x", padx=20, pady=(12, 0))
    baslik_satir.pack_propagate(False)
    for metin, genislik in [("Log ID", 70), ("Karakter Adı", 200), ("Ünvan", 160), ("Güç", 70), ("Silinme Tarihi", 180), ("Silen Kullanıcı", 160), ("İşlem", 110)]:
        ctk.CTkLabel(baslik_satir, text=metin, font=("Helvetica", 12, "bold"), text_color="white", width=genislik, anchor="w").pack(side="left", padx=6)

    liste_alani = ctk.CTkScrollableFrame(silinen_frame, fg_color="transparent")
    liste_alani.pack(fill="both", expand=True, padx=20, pady=(2, 20))

    for v in veriler:
        satir = ctk.CTkFrame(liste_alani, fg_color="#FEF3C7", border_width=1, border_color="#FCD34D", corner_radius=6, height=40)
        satir.pack(fill="x", pady=3)
        satir.pack_propagate(False)

        tarih = str(v.get('SilinmeTarihi', '-'))[:16]
        for metin, genislik in [(str(v.get('LogID', '-')), 70), (str(v.get('KarakterAdi', '-')), 200), (str(v.get('Unvan', '-') or '-'), 160), (str(v.get('GucSeviyesi', '-')), 70), (tarih, 180), (str(v.get('SilenKullanici', '-')), 160)]:
            ctk.CTkLabel(satir, text=metin, font=("Helvetica", 12), text_color="#1C1917", width=genislik, anchor="w").pack(side="left", padx=6)

        def olustur_geri_al_btn(log_id=v.get('LogID'), k_adi=v.get('KarakterAdi', '?')):
            def tetikle():
                if messagebox.askyesno("Geri Yükleme Onayı", f"'{k_adi}' karakteri veritabanına geri yüklensin mi?"):
                    if karakter_geri_yukle_sql(log_id):
                        messagebox.showinfo("Başarılı", f"'{k_adi}' geri yüklendi!")
                        sayfayi_ac_silinen()
                    else:
                        messagebox.showerror("Hata", "Geri yükleme başarısız.")
            return tetikle

        ctk.CTkButton(satir, text="↩ Geri Al", fg_color="#10B981", hover_color="#059669", font=("Helvetica", 11, "bold"), height=28, width=96, command=olustur_geri_al_btn()).pack(side="left", padx=6, pady=5)

# ==========================================
# EVREN İSTATİSTİK EKRANI
# ==========================================
def sayfayi_ac_istatistik():
    ekrani_temizle()
    istatistik_frame.pack(fill="both", expand=True)
    for w in istatistik_frame.winfo_children(): w.destroy()

    ust = ctk.CTkFrame(istatistik_frame, fg_color="#4C1D95", height=55)
    ust.pack(fill="x")
    ust.pack_propagate(False)
    ctk.CTkButton(ust, text="← Yazar Paneli", command=lambda: (ekrani_temizle(), yazar_frame.pack(fill="both", expand=True)), fg_color="#5B21B6", width=130).pack(side="left", padx=10, pady=10)
    ctk.CTkLabel(ust, text="📊  Evren İstatistikleri  (vw_EvrenIstatistik)", font=("Helvetica", 20, "bold"), text_color="white").pack(side="left", padx=15, pady=12)

    veriler = evren_istatistik_getir()
    if not veriler:
        ctk.CTkLabel(istatistik_frame, text="İstatistik verisi bulunamadı. SQL scriptini çalıştırdınız mı?", font=("Helvetica", 16), text_color="#7C3AED").pack(pady=80)
        return

    baslik_satir = ctk.CTkFrame(istatistik_frame, fg_color="#1E1B4B", height=36)
    baslik_satir.pack(fill="x", padx=20, pady=(12, 0))
    baslik_satir.pack_propagate(False)
    for metin, genislik in [("Evren", 200), ("Toplam", 80), ("Ort. Güç", 90), ("En Yüksek", 100), ("En Düşük", 90), ("Ana K.", 80), ("Antagonist", 100), ("Mentor", 80), ("Yan K.", 80)]:
        ctk.CTkLabel(baslik_satir, text=metin, font=("Helvetica", 12, "bold"), text_color="white", width=genislik, anchor="w").pack(side="left", padx=6)

    liste_alani = ctk.CTkScrollableFrame(istatistik_frame, fg_color="transparent")
    liste_alani.pack(fill="both", expand=True, padx=20, pady=(2, 20))

    for idx, v in enumerate(veriler):
        ort = v.get('OrtalamaGuc')
        ort_str = f"{ort:.1f}" if ort is not None else "-"
        renk = "#EDE9FE" if idx % 2 == 0 else "#F5F3FF"

        satir = ctk.CTkFrame(liste_alani, fg_color=renk, border_width=1, border_color="#DDD6FE", corner_radius=6, height=40)
        satir.pack(fill="x", pady=3)
        satir.pack_propagate(False)

        for metin, genislik in [(str(v.get('EvrenAdi', '-')), 200), (str(v.get('ToplamKarakter', 0)), 80), (ort_str, 90), (str(v.get('EnYuksekGuc', '-')), 100), (str(v.get('EnDusukGuc', '-')), 90), (str(v.get('AnaKarakterSayisi', 0)), 80), (str(v.get('AntagoniSayisi', 0)), 100), (str(v.get('MentorSayisi', 0)), 80), (str(v.get('YanKarakterSayisi', 0)), 80)]:
            ctk.CTkLabel(satir, text=metin, font=("Helvetica", 12), text_color="#1E1B4B", width=genislik, anchor="w").pack(side="left", padx=6)

if __name__ == '__main__':
    sayfayi_ac_ana_menu()
    app.mainloop()