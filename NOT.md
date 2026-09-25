# DIY Particle Detector Yazılımı: Yöntem ve Uygulama Notu

**Sürüm:** 0.1.1  
**Depo:** <https://github.com/Mahmutakin99/diy-particle-detector-desktop>  
**Tarih:** 25 Eylül 2026

## 1. Amaç ve kapsam

Bu çalışma, DIY Particle Detector donanımından alınan ses tabanlı darbe sinyallerinin kaydedilmesi, sayılması, saklanması ve incelenmesi için geliştirilen yazılım bileşenlerini tanımlar. Sistem, eğitim ve maker kullanımına yönelik iki donanım profiliyle çalışır:

- **Elektron/beta dedektörü:** Düşük maliyetli dört fotodiyotlu düzenek için tasarlanmıştır. Başlıca elektron/beta olaylarının sayımında kullanılır.
- **Alfa spektrometresi:** Tek BPX61 fotodiyotlu düzenek için tasarlanmıştır. Uygun hazırlanmış diyot ve referans kalibrasyonu ile alfa darbelerinin genlik dağılımını incelemek için kullanılır.

Yazılım; PySide6 ile geliştirilmiş masaüstü uygulamasını, tarayıcıda çalışan kayıt arayüzünü, taşınabilir kayıt biçimini, komut satırı analiz aracını ve eski kayıtlar için içe aktarma işlevlerini kapsar. iPadPix alıcı ve çizim araçları, bu akıştan bağımsız komut satırı araçları olarak korunmuştur.

Bu yazılım, ham darbe genliğinden tek başına doz, izotop veya kesin enerji sonucu üretmez. Enerji ekseni yalnızca kullanıcı tarafından girilen en az iki fiziksel referans noktasıyla kalibrasyon sonrasında etkinleşir.

## 2. Ölçüm ilkesi

İyonlaştırıcı parçacıkların fotodiyotta oluşturduğu yük, ön yükselteç devresinde gerilim darbesine dönüştürülür. Dedektörün analog çıkışı ses girişine bağlanır. Böylece bilgisayarın veya harici ses kartının mikrofon/ses girişinden örneklenen zaman serisi, yazılım tarafından işlenir.

Her olay için temel gözlem büyüklüğü, kaydedilen dalga biçimindeki negatif tepe genliğidir. Olayların zaman damgaları ile dalga biçimleri birlikte saklanır. Bu yapı; sayım hızı, genlik histogramı ve sonradan yapılacak kalibrasyon çalışmalarının aynı ölçüm kaydı üzerinden yürütülmesini sağlar.

Donanımın fiziksel yapısı, diyot özellikleri ve referans enerji ölçümlerinin bilimsel arka planı, özgün DIY Particle Detector çalışmasında açıklanmıştır: O. Keller *ve ark.*, *Sensors* 2019, 19(19), 4264, doi: [10.3390/s19194264](https://doi.org/10.3390/s19194264).

## 3. Yazılım mimarisi

Masaüstü uygulaması dört ayrık katmandan oluşur:

| Bileşen | Görevi |
| --- | --- |
| `particle_detector.capture` | Ses aygıtını açar, ses bloklarını kuyruğa aktarır ve kayıt tamamlandığında dosyayı yazar. |
| `particle_detector.signal` | Filtreleme, eşikleme, tepe bulma, ölü zaman denetimi ve veri kaybı hesabını yapar. |
| `particle_detector.storage` | Sürüm numaralı `.pdet` biçimini okur/yazar; eski `.msgp` ve `.pkl` kayıtlarını içe aktarır. |
| `particle_detector.app` | Canlı ölçüm, kayıtlar, analiz ve ayarlar ekranlarını sunar. |

Bu ayrım, ses geri çağrısının kullanıcı arayüzünü veya disk yazımını beklememesini sağlar. Ses blokları sınırlı kapasiteli bir kuyruk üzerinden arka plan iş parçacığına aktarılır. Kuyruk dolarsa yeni blok bekletilmez; düşen örnek sayısı kayıt üst bilgisine eklenir. Böylece uzun ölçümlerde arayüzün yanıt vermeye devam etmesi ve veri kaybının görünür olması hedeflenmiştir.

## 4. Ses edinimi ve sinyal işleme

### 4.1 Örnekleme ve aygıt seçimi

Masaüstü uygulaması ses girişini `sounddevice` üzerinden tek kanallı, 32 bit kayan noktalı bloklar hâlinde alır. Varsayılan örnekleme hızı 48 kHz'dir. Kullanıcı kullanılabilir giriş aygıtları arasından seçim yapabilir. Tarayıcı arayüzü ise Web Audio API ile ses akışını alır ve 48 kHz örnekleme hızı ister.

Ses girişinin açılamaması, mikrofon izninin reddedilmesi, aygıtın bulunamaması veya aygıtın seçilen örnekleme hızını desteklememesi ayrı hata sınıfları olarak kullanıcıya bildirilir. Kayıt hedefinin yazılamaması da ayrı ele alınır.

### 4.2 Profil parametreleri

İki profil, darbe karakteristiklerine uygun başlangıç değerleri içerir. Kullanıcı eşik değerini arayüzden değiştirebilir.

| Parametre | Elektron/beta | Alfa |
| --- | ---: | ---: |
| Varsayılan negatif eşik | -800 | -300 |
| Bant geçiren filtrenin alt sınırı | 1 000 Hz | 80 Hz |
| Bant geçiren filtrenin üst sınırı | 12 000 Hz | 12 000 Hz |
| Ölü zaman | 2 ms | 2 ms |
| Görüntüleme/kayıt pencere uzunluğu | 256 örnek | 2 048 örnek |

Üst kesim frekansı, örnekleme frekansının yüzde 45'i ile sınırlandırılır. Bu denetim, düşük örnekleme hızlarında Nyquist sınırına yaklaşan geçersiz filtre tasarımlarını önler.

### 4.3 Filtreleme ve olay seçimi

Her ses bloğuna üçüncü dereceden Butterworth bant geçiren filtre uygulanır. Filtre, ikinci dereceden kesitler biçiminde (`SOS`) çalıştırılır; durum değişkenleri bloklar arasında taşınır. Bu nedenle ardışık bloklardaki filtreleme süreklidir.

Filtrelenmiş işaretin negatifi üzerinde `find_peaks` yöntemi kullanılır. Bir tepenin olay olarak kabul edilmesi için büyüklüğünün seçilen negatif eşik değerini aşması gerekir. Aynı fiziksel darbenin birden çok kez sayılmasını önlemek amacıyla kabul edilen iki olay arasında profile bağlı 2 ms ölü zaman uygulanır. Olayın zaman damgası, ses girişinin donanım zamanına ve blok içindeki örnek ofsetine göre mikrosaniye cinsinden hesaplanır.

Kayıtla birlikte saklanan dalga biçimi, filtrelenmemiş örneklerden alınır. Böylece filtre ayarları sonradan değişse bile ham olaya yakın veri korunur. Canlı görünümde son ses bloğu, anlık genlik ve olay sayısından hesaplanan CPS (*counts per second*) değeri gösterilir. Analiz ekranındaki histogram mutlak tepe genliklerinden oluşturulur.

### 4.4 Veri kaybının izlenmesi

Sistem iki tür olası veri kaybını sayar:

1. Ardışık ses bloklarının zaman damgaları arasındaki beklenenden büyük boşluklar, örnekleme boşluğu olarak kaydedilir.
2. Arka plan işleme kuyruğu dolduğunda kabul edilemeyen bloklardaki örnek sayısı kaydedilir.

Bu iki değer toplanarak `.pdet` oturum üst bilgisindeki `lost_samples` alanına yazılır. Böylece ölçüm süresince veri akışının bütünlüğü sonradan değerlendirilebilir.

## 5. Kalibrasyon ve analiz sınırları

Enerji kalibrasyonu, kullanıcı tarafından sağlanan genlik-enerji çiftlerine doğrusal en küçük kareler yaklaşımı uygulanarak yapılır:

\[
E(A) = m(A-\bar{A})+\bar{E}
\]

Burada \(A\) darbe genliği, \(E\) enerji (keV), \(m\) doğrusal eğim, \(\bar{A}\) ve \(\bar{E}\) referans noktalarının ortalamalarıdır. Kalibrasyonun kabul edilmesi için en az iki genlik değeri birbirinden farklı, tüm genlik ve enerji değerleri pozitif, eğim ise pozitif olmalıdır.

Kalibrasyon yokken arayüz yalnız genlik eksenini gösterir. Kalibrasyon tamamlanmadan keV/MeV ekseni açılmaz. Bu kural, ses kartı kazancı, dedektör devresi, eşik ayarı ve çevresel koşullar değiştiğinde ham genliğin fiziksel enerjiyle otomatik olarak eşlenmesini engeller. Aynı nedenle yazılımın mevcut sürümü doz hesabı veya otomatik izotop tanımlaması sunmaz.

Komut satırı aracı aşağıdaki şekilde kayıt üst bilgisini ve kalibrasyon durumunu inceler:

```bash
particle-detector-analyze recording.pdet
```

## 6. Kayıt biçimi ve geriye dönük uyumluluk

Yeni kayıtlar `.pdet` uzantısıyla, MessagePack tabanlı ve sürüm numaralı bir biçimde saklanır. Dosya yapısı aşağıdaki bilgileri içerir:

- Biçim adı ve sürüm numarası (`format: pdet`, `version: 1`)
- Oturum başlangıç zamanı (UTC, ISO 8601)
- Örnekleme hızı
- Dedektör profili
- Kayıp örnek sayısı
- Varsa kullanıcı kalibrasyon noktaları
- Her darbe için mikrosaniye zaman damgası, tepe genliği ve dalga biçimi

Dosya yazımı atomiktir. Önce aynı dizinde geçici dosya yazılır, içerik diske eşitlenir ve ardından hedef dosyanın yerine taşınır. Bu yöntem, kaydetme işlemi yarıda kesilirse önceki geçerli kaydın bozulma olasılığını azaltır.

Eski kayıtlar için iki içe aktarma yolu bulunur:

- **`.msgp`:** Eski web kaydedicinin MessagePack darbe listeleri okunur. Milisaniye zaman damgaları mikrosaniyeye dönüştürülür.
- **`.pkl`:** Tarihsel Pandas DataFrame düzenlerinin ikisi desteklenir: `ts/pulse` ve `timestamp/waveform/peak`.

Pickle biçimi kod çalıştırabildiğinden, `.pkl` içe aktarma işlemi yalnız kullanıcının açık onayıyla ve güvenilir yerel dosyalar için yapılır. Uygulama bu riski içe aktarma ekranında bildirir; komut satırında ise `--trusted-pickle` seçeneği gerekir.

Yeni kayıtların depodan ayrı bir uygulama veri dizininde tutulması amaçlanmıştır:

| İşletim sistemi | Varsayılan kayıt dizini |
| --- | --- |
| Windows | `%LOCALAPPDATA%/DIY Particle Detector/recordings` |
| macOS | `~/Library/Application Support/DIY Particle Detector/recordings` |
| Linux | `$XDG_DATA_HOME/DIY Particle Detector/recordings` veya `~/.local/share/DIY Particle Detector/recordings` |

## 7. Kullanıcı arayüzleri

### 7.1 Masaüstü uygulaması

PySide6 tabanlı masaüstü uygulaması dört sekmeden oluşur: **Canlı Ölçüm**, **Kayıtlar**, **Analiz** ve **Ayarlar**. Canlı ölçüm ekranında profil, giriş aygıtı ve eşik seçilir; anlık dalga biçimi, son darbe genliği ve sayım hızı izlenir. Kayıtlar ekranı `.pdet`, `.msgp` ve güvenilir `.pkl` dosyalarını içe aktarır. Analiz ekranı tepe genliği histogramını gösterir. Ayarlar ekranında dil, görünüm ve kalibrasyon referansları yönetilir.

Arayüz, işletim sisteminin dilini başlangıçta algılar; Türkçe ve İngilizce arasında çalışma sırasında geçiş yapılabilir. Açık, koyu ve sistem görünümü seçenekleri bulunur. Grafik eksenleri metinle etiketlenmiş, ana denetimler düğme ve klavye odağıyla erişilebilir olacak şekilde düzenlenmiştir.

### 7.2 Tarayıcı arayüzü

`data_recording_software/webGui` altındaki arayüz Web Audio API kullanır. Ses aygıtı seçimi, başlat/durdur akışı, Türkçe/İngilizce metinler, canlı dalga biçimi, sayım hızı, tepe genliği ve `.pdet` dışa aktarma işlevlerini içerir. Tarayıcı tarafındaki olay engelleme süresi 2 ms'dir; profil seçimine göre dalga biçimi analiz penceresi elektron/beta için 256, alfa için 2 048 örnektir.

Tarayıcı, mikrofon izni reddedildiğinde veya aygıt kullanılamadığında kullanıcıya açıklayıcı hata iletisi gösterir. Kullanıcının iki geçerli referans noktası girmesi durumunda bu noktalar dışa aktarılan `.pdet` üst bilgisine eklenir.

## 8. Doğrulama ve kalite güvence yöntemi

Doğrulama; birim testleri, sentetik ses blokları ve paketlenmiş uygulama açılış testleriyle yürütülmüştür.

| Doğrulama alanı | Uygulanan kontrol |
| --- | --- |
| Yeni kayıt biçimi | `.pdet` kodlama-kod çözme dönüşü, sürüm denetimi ve kalibrasyonun korunması |
| Kalibrasyon | Aynı genlikli referansların reddedilmesi ve doğrusal enerji hesabı |
| Eski veriler | `.msgp` ile iki farklı `.pkl` DataFrame düzeninin içe aktarılması |
| Darbe algılama | Her iki profil için sentetik iki darbenin blok sınırları arasında bir kez sayılması |
| Veri kaybı | Zaman damgası boşluğunun kayıp örnek sayısına yansıtılması |
| Arka plan kayıt işi | Kuyruk üzerinden kayıt ve atomik dosya kaydı |
| Hata işleme | İzin, aygıt, örnekleme hızı ve kaydetme hatalarının sınıflandırılması |
| Arayüz | Canlı grafik, spektrum grafiği, kayıt listesi ve örnek `.pdet` açılışı |

Sürüm 0.1.1 için yerel test takımında 14 test başarıyla çalıştırılmıştır. Her platform paketi, paketlenmiş uygulamanın sentetik iki alfa darbesi içeren örnek `.pdet` dosyasını açtığını denetleyen ayrıca bir açılış testinden geçirilmiştir.

Bu testler yazılım mantığını ve paket bütünlüğünü doğrular; gerçek dedektör, ses kartı, kablo, elektromanyetik ortam ve radyoaktif kaynakla yapılan cihaz ölçümünün yerine geçmez. Her fiziksel kurulumda eşik, gürültü düzeyi, ses kartı kazancı ve kalibrasyon referansları yeniden kontrol edilmelidir.

## 9. Dağıtım ve tekrarlanabilir derleme

GitHub Actions iş akışı, çapraz derleme yerine her hedef işletim sisteminde ayrı derleme yapar. PyInstaller ile oluşturulan masaüstü uygulaması, hedefe özgü paket biçimine dönüştürülür.

| Hedef | Paket biçimi |
| --- | --- |
| macOS Apple Silicon | DMG (`arm64`) |
| macOS Intel | DMG (`x64`) |
| Windows x64 | Inno Setup yükleyicisi (`Setup.exe`) |
| Windows ARM64 | Inno Setup yükleyicisi (`Setup.exe`) |
| Linux x64 | AppImage |
| Linux ARM64 | AppImage |

Linux paketinde PortAudio çalışma zamanı ile gerekli Qt/X11 bağımlılıklarının bulunması denetlenir. macOS paketi mikrofon kullanım açıklamasını içerir ve uygulama paketi doğrulanır. Windows paketinde PyInstaller çıktısı örnek kayıt açılışından sonra Inno Setup ile yükleyiciye dönüştürülür. Her altı hedefte testler ve paket açılış testi çalışmadan sürüm varlığı yayımlanmaz.

Sürüm 0.1.1 paketleri şu adreste yayımlanmıştır: <https://github.com/Mahmutakin99/diy-particle-detector-desktop/releases/tag/v0.1.1>

İlk dağıtım sürümünde Apple geliştirici sertifikasıyla imzalama, macOS noter onayı ve Windows kod imzalama yer almamaktadır. Bu nedenle işletim sistemi ilk çalıştırmada güvenlik onayı isteyebilir.

## 10. Sonuç

Geliştirilen yazılım, ses girişine dayalı DIY Particle Detector düzenekleri için kayıt, canlı sayım, veri saklama ve temel genlik spektrumu analizini tek bir akışta birleştirir. Profil tabanlı sinyal işleme, kullanıcı kontrollü kalibrasyon, taşınabilir kayıt biçimi, eski verilerle uyumluluk ve çoklu işletim sistemi paketleri; eğitim, laboratuvar uygulaması ve yurttaş bilimi çalışmalarında tekrarlanabilir kullanım için temel altyapıyı sağlar.

Bilimsel yorum için darbe sayısı, genlik spektrumu, kayıp örnek sayısı, kullanılan profil, örnekleme hızı, eşik değeri ve kalibrasyon referanslarının birlikte raporlanması gerekir. Ölçümün fiziksel geçerliliği, yazılım testlerinden bağımsız olarak kullanılan dedektörün kurulumu ve referans ölçümleriyle değerlendirilmelidir.
