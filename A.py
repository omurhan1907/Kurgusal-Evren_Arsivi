def karakter_guncelle_sql(karakter_id, isim, unvan, evren_id, grup_id, yas, cinsiyet, boy, nitelik, guc, cikis, onem, dogum, silah, zayiflik, amac, lore):
    conn = baglanti_kur()
    if not conn: return False
    cursor = conn.cursor()
    try:
        conn.autocommit = False # Transaction Başlangıcı
        sorgu = """UPDATE Karakterler SET KarakterAdi=?, ... WHERE KarakterID=?"""
        cursor.execute(sorgu, (isim, ..., karakter_id))
        conn.commit() # İşlemi Onayla
        return True
    except Exception as e:
        conn.rollback() # Hata varsa geri sar (Rollback)
        print("Güncelleme Hatası:", e)
        return False
    finally:
        conn.close()