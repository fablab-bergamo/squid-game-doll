# Bambola di Squid Game 🔴🟢

*[English](README.md) | **Italiano***

Un robot "Uno, Due, Tre... Stella!" alimentato da AI ispirato alla serie TV Squid Game. Questo progetto utilizza computer vision e machine learning per il riconoscimento e tracciamento dei giocatori in tempo reale, con una bambola animata che segnala le fasi di gioco e un sistema opzionale di puntamento laser per i giocatori eliminati.

**🎯 Caratteristiche:**
- Rilevamento e tracciamento giocatori in tempo reale usando reti neurali YOLO
- Riconoscimento facciale per la registrazione dei giocatori
- Bambola animata interattiva con occhi LED e testa controllata da servo
- Sistema opzionale di puntamento laser per giocatori eliminati *(in sviluppo)*
- Supporto per PC (con CUDA), NVIDIA Jetson Nano (con CUDA), e Raspberry Pi 5 (con Hailo AI Kit)
- Aree di gioco e parametri configurabili

**🏆 Stato:** Prima versione funzionante dimostrata all'Arduino Day 2025 al FabLab Bergamo, Italia.

## 🎮 Avvio Rapido

### Prerequisiti
- Python 3.9+ con Poetry
- Webcam (Logitech C920 consigliata)
- Opzionale: ESP32 per controllo bambola, hardware puntamento laser

### Installazione

**Per PC (Windows/Linux):**
```bash
# Installa Poetry
pip install poetry

# Installa dipendenze
poetry install

# Opzionale: supporto CUDA per GPU NVIDIA
poetry run pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --force-reinstall
```

**Per NVIDIA Jetson Nano:**
```bash
# Installa Poetry
pip install poetry

# Installa dipendenze
poetry install

# IMPORTANTE: Installa PyTorch con CUDA per Jetson Nano
poetry run pip uninstall torch torchvision torchaudio -y
poetry run pip install torch==2.8.0 torchvision==0.23.0 --index-url=https://pypi.jetson-ai-lab.io/jp6/cu126

# Opzionale: OpenCV CUDA per massime prestazioni (vedi OPENCV_JETSON_IT.md)
# Dopo aver compilato OpenCV CUDA a livello di sistema:
VENV_PATH=$(poetry env info --path)
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"
```

**Per Raspberry Pi 5 con Hailo AI Kit:**
```bash
poetry install
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git

# Scarica modelli Hailo pre-compilati
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
```

### Configurazione ed Esecuzione

1. **Configura aree di gioco** (prima configurazione):
```bash
poetry run python -m src.squid_game_doll.run --setup
```

2. **Avvia il gioco**:
```bash
poetry run python -m src.squid_game_doll.run
```

3. **Avvia con puntamento laser** (richiede configurazione ESP32):
```bash
poetry run python -m src.squid_game_doll.run -k -i 192.168.45.50
```

## 🎯 Come Funziona

### Flusso di Gioco
I giocatori si allineano a 8-10m dallo schermo e seguono questa sequenza:

1. **📝 Registrazione (15s)**: Resta nell'area di partenza mentre il sistema cattura il tuo volto
2. **🟢 Luce Verde**: Muoviti verso la linea del traguardo (bambola si gira, occhi spenti)
3. **🔴 Luce Rossa**: Fermo! Qualsiasi movimento causa l'eliminazione (bambola guarda avanti, occhi rossi)
4. **🏆 Vittoria/💀 Eliminazione**: Vinci raggiungendo il traguardo o vieni eliminato per esserti mosso durante la luce rossa

### Guida Visuale Fasi di Gioco

| Fase | Schermo | Stato Bambola | Azione |
|------|---------|---------------|---------|
| **Caricamento** | ![Schermo di caricamento](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/loading_screen.png?raw=true) | Movimento casuale | Attira la folla |
| **Registrazione** | ![registrazione](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/init.png?raw=true) | ![Frontale, nessun occhio](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_init.png?raw=true) | Cattura volto |
| **Luce Verde** | ![Luce verde](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/green_light.png?raw=true) | ![Girata, nessun occhio](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_off.png?raw=true) | I giocatori si muovono |
| **Luce Rossa** | ![Luce rossa](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/red_light.png?raw=true) | ![Frontale, occhi rossi](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/doll_on.png?raw=true) | Rilevamento movimento |

## ⚙️ Configurazione

La modalità setup permette di configurare le aree di gioco e le impostazioni della telecamera per prestazioni ottimali.

### Configurazione Aree
Devi definire tre aree critiche:

- **🎯 Area Visione** (Gialla): L'area fornita alla rete neurale per il rilevamento giocatori
- **🏁 Area Traguardo**: I giocatori devono raggiungere questa area per vincere
- **🚀 Area Partenza**: I giocatori devono registrarsi inizialmente in questa area

![Interfaccia di Configurazione](https://github.com/fablab-bergamo/squid-game-doll/blob/main/doc/config.png?raw=true)

### Passi di Configurazione
1. Avvia modalità setup: `poetry run python -m src.squid_game_doll.run --setup`
2. Disegna rettangoli per definire aree di gioco (l'area visione deve intersecare con aree partenza/traguardo)
3. Regola impostazioni nel menu IMPOSTAZIONI (livelli di confidenza, contrasto)
4. Testa prestazioni usando "Anteprima rete neurale"
5. Salva configurazione in `config.yaml`

### Note Importanti
- L'area visione dovrebbe escludere luci esterne e zone non di gioco
- La risoluzione webcam influisce sull'input della rete neurale (tipicamente ridimensionata a 640x640)
- Una configurazione appropriata delle aree è essenziale per il funzionamento delle meccaniche di gioco

## 🔧 Requisiti Hardware

### Piattaforme Supportate
| Piattaforma | Accelerazione AI | Prestazioni | Ideale Per |
|-------------|-----------------|-------------|------------|
| **PC con GPU NVIDIA** | CUDA | 30+ FPS | Sviluppo, Alte Prestazioni |
| **NVIDIA Jetson Nano** | CUDA | 15-25 FPS | Distribuzione Mobile, Edge Computing |
| **Raspberry Pi 5 + Hailo AI Kit** | Hailo 8L | 10-15 FPS | Distribuzione Produzione |
| **PC (solo CPU)** | Nessuna | 3-5 FPS | Test Base |

### Componenti Richiesti

#### Sistema Core
- **Computer**: PC (Windows/Linux), NVIDIA Jetson Nano, o Raspberry Pi 5
- **Webcam**: Logitech C920 HD Pro (consigliata) o webcam USB compatibile
- **Display**: Monitor o proiettore per interfaccia di gioco

#### Hardware Bambola
- **Controller**: Scheda ESP32C2 MINI Wemos
- **Servo**: 1x servo motore SG90 (movimento testa)
- **LED**: 2x LED Rossi (occhi)
- **Parti 3D**: Componenti bambola stampabili (vedi `hardware/doll-model/`)

#### Sistema Puntamento Laser Opzionale *(In Sviluppo)*
⚠️ **Avviso Sicurezza**: Usa appropriate misure di sicurezza laser e rispetta le normative locali.

**Stato**: Puntamento base implementato ma richiede perfezionamento per uso produzione.

**Componenti:**
- **Servo**: 2x servo motori SG90 per meccanismo pan-tilt
- **Piattaforma**: [Piattaforma pan-tilt (~11 EUR)](https://it.aliexpress.com/item/1005005666356097.html)
- **Laser**: Scegli un'opzione:
  - **Verde 5mW**: Maggiore visibilità, più sicuro per gli occhi, meno messa a fuoco precisa
  - **Rosso 5mW**: Messa a fuoco migliore, costo più basso
- **Parti 3D**: Supporto laser (vedi `hardware/proto/Laser Holder v6.stl`)

### Requisiti Spazio di Gioco
- **Area**: Spazio interno 10m x 10m consigliato
- **Distanza**: I giocatori partono a 8-10m dallo schermo
- **Illuminazione**: Illuminazione controllata per prestazioni ottimali di computer vision

### Installazione Dettagliata
- **Setup PC**: Vedi istruzioni di installazione sopra
- **Raspberry Pi 5**: Vedi [INSTALL.md](INSTALL.md) ([Italiano](INSTALL_IT.md)) per setup completo Hailo AI Kit
- **Programmazione ESP32**: Usa [Thonny IDE](https://thonny.org/) con MicroPython (vedi cartella `esp32/`)

## 🎲 Opzioni Linea di Comando

```bash
poetry run python -m src.squid_game_doll.run [OPZIONI]
```

### Opzioni Disponibili
| Opzione | Descrizione | Esempio |
|---------|-------------|---------|
| `-m, --monitor` | Indice monitor (base 0) | `-m 0` |
| `-w, --webcam` | Indice webcam (base 0) | `-w 0` |
| `-k, --killer` | Abilita sparatore laser ESP32 | `-k` |
| `-i, --tracker-ip` | Indirizzo IP ESP32 | `-i 192.168.45.50` |
| `-j, --joystick` | Indice joystick | `-j 0` |
| `-n, --neural_net` | Modello rete neurale personalizzato | `-n yolov11m.hef` |
| `-c, --config` | Percorso file configurazione | `-c my_config.yaml` |
| `-s, --setup` | Modalità setup per configurazione aree | `-s` |

### Comandi di Esempio

**Setup base:**
```bash
# Configurazione prima volta
poetry run python -m src.squid_game_doll.run --setup -w 0

# Avvia gioco con impostazioni predefinite
poetry run python -m src.squid_game_doll.run
```

**Configurazione avanzata:**
```bash
# Setup completo con puntamento laser
poetry run python -m src.squid_game_doll.run -m 0 -w 0 -k -i 192.168.45.50

# Modello e configurazione personalizzati
poetry run python -m src.squid_game_doll.run -n custom_model.hef -c custom_config.yaml
```

## 🤖 AI & Computer Vision

### Modelli Rete Neurale
- **PC (Ultralytics)**: Modelli YOLOv8/v11 per rilevamento oggetti e tracciamento
- **NVIDIA Jetson Nano**: Modelli YOLO ottimizzati CUDA con rilevamento automatico piattaforma
- **Raspberry Pi (Hailo)**: Modelli Hailo pre-compilati ottimizzati per edge AI
- **Rilevamento Volti**: Haar cascades OpenCV per registrazione e identificazione giocatori

### Ottimizzazione Prestazioni

#### Ottimizzazioni Specifiche per Piattaforma
**NVIDIA Jetson Nano:**
- **Accelerazione CUDA automatica** con wheel PyTorch ottimizzati
- **Supporto OpenCV CUDA** per elaborazione immagini accelerata GPU (opzionale)
- **Dimensione input ridotta** (416px vs 640px) per inferenza più veloce
- **Precisione FP16** per miglioramento velocità 2x
- **Conteggio thread ottimizzato** per processori ARM
- **Selezione modello specifica Jetson** (yolo11n.pt per bilanciamento ottimale velocità/accuratezza)
- **Ottimizzazione TensorRT** disponibile tramite script `optimize_for_jetson.py`

**Raspberry Pi 5 + Hailo:**
- **Inferenza accelerata hardware** usando processore AI Hailo 8L
- **Modelli .hef ottimizzati** compilati specificamente per architettura Hailo
- **Elaborazione parallela** tra ARM CPU e acceleratore AI Hailo

**PC con GPU NVIDIA:**
- **Accelerazione CUDA completa** con risoluzione input massima
- **Modelli alta precisione** per miglior accuratezza
- **Elaborazione multi-thread** per prestazioni tempo reale

#### Prestazioni Generali
- **Rilevamento Oggetti**: 3-30+ FPS a seconda dell'hardware e ottimizzazione
- **Estrazione Volti**: CPU-bound con Haar cascades OpenCV (accelerata GPU con OpenCV CUDA)
- **Elaborazione Immagini**: Speedup 2-5x con OpenCV CUDA per conversioni colore e ridimensionamento
- **Rilevamento Laser**: Pipeline computer vision usando soglia + dilatazione + cerchi di Hough

### Risorse Modelli
- [Hailo Model Zoo](https://github.com/hailo-ai/hailo_model_zoo/blob/master/docs/public_models/HAILO8L/HAILO8L_object_detection.rst)
- [Dettagli Implementazione Rete Neurale](https://www.fablabbergamo.it/2025/03/30/primi-passi-con-lai-raspberry-pi-5-hailo/)

## 🛠️ Sviluppo & Test

### Strumenti Qualità Codice
```bash
# Installa dipendenze sviluppo
poetry install --with dev

# Formattazione codice
poetry run black .

# Linting
poetry run flake8 .

# Esegui test
poetry run pytest
```

### Profilazione Prestazioni
```bash
# Profila l'applicazione
poetry run python -m cProfile -o game.prof -m src.squid_game_doll.run

# Visualizza risultati profilazione
poetry run snakeviz ./game.prof
```

### Interfaccia di Gioco

![Interfaccia di Gioco](https://github.com/user-attachments/assets/4f3aed2e-ce2e-4f75-a8dc-2d508aff0b47)

Il gioco usa PyGame come motore di rendering con overlay di tracciamento giocatori in tempo reale.

## 🎯 Sistema Puntamento Laser (Avanzato)

### Pipeline Computer Vision
Il sistema di puntamento laser usa un approccio sofisticato di computer vision per rilevare e tracciare punti laser:

![Esempio Rilevamento Laser](https://github.com/user-attachments/assets/b3f5dd56-1ecf-4783-9174-87988d44a1f1)

### Algoritmo di Rilevamento
1. **Selezione Canale**: Estrai canali R, G, B o converti in scala di grigi
2. **Sogliatura**: Trova pixel più luminosi usando `cv2.threshold()`
3. **Operazioni Morfologiche**: Applica dilatazione per evidenziare punti
4. **Rilevamento Cerchi**: Usa Trasformata di Hough per localizzare punti laser circolari
5. **Validazione**: Regolazione soglia adattiva per rilevamento punto singolo

```python
# Passi di elaborazione chiave
diff_thr = cv2.threshold(channel, threshold, 255, cv2.THRESH_TOZERO)
masked_channel = cv2.dilate(masked_channel, None, iterations=4)
circles = cv2.HoughCircles(masked_channel, cv2.HOUGH_GRADIENT, 1, minDist=50,
                          param1=50, param2=2, minRadius=3, maxRadius=10)
```

### Considerazioni Critiche
- **Esposizione Webcam**: Controllo esposizione manuale richiesto (tipicamente -10 a -5 per C920)
- **Riflettività Superficie**: Superfici diverse influenzano visibilità laser
- **Scelta Colore**: I laser verdi spesso funzionano meglio di quelli rossi
- **Tempistica**: Tempo di convergenza 10-15 secondi per puntamento accurato

### Risoluzione Problemi
| Problema | Soluzione |
|----------|-----------|
| Avvio lento Windows | Imposta `OPENCV_VIDEOIO_MSMF_ENABLE_HW_TRANSFORMS=0` |
| Rilevamento laser scarso | Regola impostazioni esposizione, controlla tipi superficie |
| Multipli falsi positivi | Aumenta soglia, maschera sorgenti luce esterne |

## 🚧 Problemi Noti & Miglioramenti Futuri

### Limitazioni Attuali
- **Sistema Visione**: Combinare rilevamento laser a bassa esposizione con tracciamento giocatori a esposizione normale
- **Prestazioni Laser**: Tempo di convergenza puntamento 10-15 secondi
- **Dipendenza Hardware**: Calibrazione esposizione webcam manuale richiesta

### Roadmap
- [ ] Riaddestrare modello YOLO per rilevamento combinato laser/giocatori
- [ ] Implementare stima profondità per posizionamento laser più veloce
- [ ] Sistema calibrazione esposizione automatica
- [ ] Compensazione riflesso superficie migliorata

### Funzionalità Completate
- ✅ Bambola stampabile 3D con testa animata e occhi LED
- ✅ Registrazione giocatori e rilevamento linea traguardo
- ✅ Soglie sensibilità movimento configurabili
- ✅ GitHub Actions CI/CD e test automatizzati

## 📚 Risorse Aggiuntive

- **Guida Installazione**: [INSTALL.md](INSTALL.md) ([Italiano](INSTALL_IT.md)) per setup Raspberry Pi
- **Setup OpenCV CUDA**: [OPENCV_JETSON_IT.md](OPENCV_JETSON_IT.md) per accelerazione GPU Jetson Nano
- **Sviluppo ESP32**: Usa [Thonny IDE](https://thonny.org/) per MicroPython
- **Reti Neurali**: [Dettagli implementazione Hailo AI](https://www.fablabbergamo.it/2025/03/30/primi-passi-con-lai-raspberry-pi-5-hailo/)
- **Ottimizzazione Telecamera**: [Consigli prestazioni telecamera OpenCV](https://forum.opencv.org/t/opencv-camera-low-fps/567/4)

## 📄 Licenza

Questo progetto è open source. Vedi il file LICENSE per i dettagli.