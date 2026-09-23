MESSAGES = {
    "en": {
        "app": "DIY Particle Detector", "live": "Live measurement", "records": "Recordings", "analysis": "Analysis", "settings": "Settings",
        "start": "Start recording", "stop": "Stop and save", "profile": "Detector profile", "device": "Input device", "threshold": "Trigger threshold",
        "rate": "Count rate", "amplitude": "Pulse amplitude", "uncalibrated": "Amplitude axis (calibration required for keV/MeV)",
        "electron": "Electron / beta detector", "alpha": "Alpha spectrometer", "language": "Language", "appearance": "Appearance",
        "light": "Light", "dark": "Dark", "system": "System", "choose_file": "Import recording", "trust_pickle": "I trust this local pickle file",
        "pickle_warning": "Pickle files can execute code. Import only a file you trust.", "save_error": "Could not save recording", "audio_permission": "Microphone access was denied. Allow it in system settings.",
        "audio_device": "The selected audio input is unavailable. Connect it or choose another device.", "audio_sample_rate": "This device does not support the selected sample rate.",
        "audio_connection": "Could not open the audio input.", "calibration": "Calibration", "add_reference": "Add reference point", "energy_axis": "Energy axis", "no_calibration": "Add two reference points before enabling keV/MeV.",
    },
    "tr": {
        "app": "DIY Parçacık Dedektörü", "live": "Canlı ölçüm", "records": "Kayıtlar", "analysis": "Analiz", "settings": "Ayarlar",
        "start": "Kaydı başlat", "stop": "Durdur ve kaydet", "profile": "Dedektör profili", "device": "Giriş aygıtı", "threshold": "Tetikleme eşiği",
        "rate": "Sayım hızı", "amplitude": "Darbe genliği", "uncalibrated": "Genlik ekseni (keV/MeV için kalibrasyon gerekir)",
        "electron": "Elektron / beta dedektörü", "alpha": "Alfa spektrometresi", "language": "Dil", "appearance": "Görünüm",
        "light": "Açık", "dark": "Koyu", "system": "Sistem", "choose_file": "Kaydı içe aktar", "trust_pickle": "Bu yerel pickle dosyasına güveniyorum",
        "pickle_warning": "Pickle dosyaları kod çalıştırabilir. Yalnız güvendiğiniz dosyaları içe aktarın.", "save_error": "Kayıt kaydedilemedi", "audio_permission": "Mikrofon erişimi reddedildi. Sistem ayarlarından izin verin.",
        "audio_device": "Seçili ses girişi kullanılamıyor. Bağlayın veya başka bir aygıt seçin.", "audio_sample_rate": "Bu aygıt seçilen örnekleme hızını desteklemiyor.",
        "audio_connection": "Ses girişi açılamadı.", "calibration": "Kalibrasyon", "add_reference": "Referans noktası ekle", "energy_axis": "Enerji ekseni", "no_calibration": "keV/MeV eksenini açmak için iki referans noktası ekleyin.",
    },
}


def system_language() -> str:
    import locale
    return "tr" if (locale.getlocale()[0] or "").lower().startswith("tr") else "en"
