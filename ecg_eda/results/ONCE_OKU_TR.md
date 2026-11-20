# ECG toplu EDA - kısa Türkçe açıklama

Ana LEMON grubunda 227 kişi var. Bu raporda grubun verdiği listedeki 206 kişi hedeflendi; önceki geniş tarama 213 ECG kaydını kapsıyordu.

- İşlenen: 206 / 206
- Dosyasının tamamı sayısal olarak okunabilen: 206
- Otomatik atım tespiti çalıştırılan: 206
- Henüz işlenmeyen: 0
- En az bir otomatik inceleme işareti bulunan: 198
- Aynı çekime ait tam MNI başlığı doğrulanan: 201
- Aynı çekime ait MNI başlığı doğrulanmayan: 5 (ECG EDA'sından çıkarılmadı).
- Kesin kullanılabilir kişi sayısı: henüz belirlenmedi.

**Ne yaptık?** Dosyaları açtık; süre, kanal sayısı, örnekleme hızı, eksik değerler, düz kalan bölümler, büyük sinyal sıçramaları ve çekim tetiklerini kontrol ettik. Otomatik atım adayları ve aralarındaki süreleri çıkardık. İlk 60 saniyede iki yöntemin aday sayılarını karşılaştırdık. Her kayıt için inceleme grafiği hazırladık.

**Ne yapmadık?** Her atımı elle doğrulamadık, güvenilir son RMSSD değerleri üretmedik, stres ilişkisi veya tahmin modeli hesaplamadık. Bir kaydın dosyası açılıyor olması ya da otomatik eşiklere takılmaması, kaydın iyi olduğu anlamına gelmez.

**Sonraki adım:** İnceleme işaretleri çıkan bölümlere ve önceden seçilmiş örnek pencerelere bakmak, kaçırılmış/yanlış atımları doğrulamak, kullanılacak süreyi ve düzeltme kurallarını belirlemek. fMRI ile fizyolojik düzeltme yapılacaksa solunum ve zaman hizalaması ayrıca kontrol edilmeli.

## Dosyalar
- LEMON_ECG_EDA_Group206_EN.pdf: İngilizce grup raporu.
- figures/: Sunuma konabilecek iki toplu EDA grafiği.
- private/participant_eda.csv: Kişi bazında tüm otomatik kontrol değerleri.
- Ayrıntılı inceleme grafikleri: önceki outputs/ecg_cohort_eda/private/qc_figures/ klasöründe; yeniden hesaplanmadı.

Kişi bazındaki dosyalar private/ altında tutuldu; Git'e eklenmemesi için .gitignore kondu. Yeni rapor, eski 12 kişilik ön raporu silmez veya otomatik olarak geçersiz kılmaz.
