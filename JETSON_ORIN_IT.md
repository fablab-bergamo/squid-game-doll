# Guida di Configurazione NVIDIA Jetson Orin

Questa guida copre la configurazione ottimale e l'ottimizzazione delle prestazioni per **NVIDIA Jetson Orin** con JetPack 6.1+ per prestazioni massime.

## Configurazione Rapida

### Prerequisiti
* NVIDIA Jetson Orin con JetPack 6.1+ installato
* Webcam USB (Logitech C920 raccomandata)
* Connessione internet per l'installazione dei pacchetti

### Comandi di Installazione

```bash
# Installa poetry e dipendenze
pip install poetry
poetry install

# Installa PyTorch con supporto CUDA per Jetson Orin
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl

# Installa ONNX Runtime con supporto GPU
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl

# IMPORTANTE: Se ONNX Runtime viene reinstallato durante la configurazione, reinstalla la versione GPU:
# poetry run pip uninstall onnxruntime -y && poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl
```

### Ottimizzazione Modello

```bash
# Esegui script di ottimizzazione (esporta in ONNX per default)
poetry run python optimize_for_jetson.py --int8  # Ottimizzazione completa con INT8
poetry run python optimize_for_jetson.py         # Ottimizzazione standard con FP16

# Per prestazioni massime: Esporta nel formato engine TensorRT
/usr/src/tensorrt/bin/trtexec --onnx=yolo11n.onnx --saveEngine=yolo11n.engine --memPoolSize=workspace:4096 --fp16 --verbose
/usr/src/tensorrt/bin/trtexec --onnx=yolo11l.onnx --saveEngine=yolo11l.engine --memPoolSize=workspace:4096 --fp16 --verbose
```

### Modalità Prestazioni
```bash
# Imposta Jetson alla modalità prestazioni massime
sudo nvpmodel -m 0 && sudo jetson_clocks
```

---

## Analisi delle Prestazioni

### Ottimizzazione delle Prestazioni Jetson Orin
La classe PlayerTrackerUL include ottimizzazioni specifiche per Jetson Orin:

**Rilevamento Automatico Formato Modello**: 
- Rileva automaticamente l'hardware Jetson Orin (aarch64 + /etc/nv_tegra_release)
- **Priorità Modello**: TensorRT (.engine) > PyTorch (.pt) per prestazioni massime
- Usa yolo11l.pt (modello large) per default per bilanciamento ottimale accuratezza vs velocità

**Ottimizzazioni Prestazioni**:
- Esecuzione TensorRT con librerie TensorRT di sistema
- Precisione FP16 per velocità migliorata
- Augmentation disabilitata durante inferenza
- Numero thread ottimizzato per processori ARM
- Input shapes statici per ottimizzazione TensorRT

### Prestazioni Misurate su Jetson Orin (Test nel Mondo Reale)

**Confronto Prestazioni Modello**:
- Modello PyTorch: ~80-100ms inferenza (10-12 FPS)
- ONNX GPU: Non compatibile (limitazioni API nella build GPU Jetson)

**Prestazioni Engine TensorRT** ⚡ **PRESTAZIONI MASSIME**:

**YOLO11n (Modello Nano)**:
  - **Preprocessing**: ~2ms (preparazione immagine)
  - **Inferenza TensorRT**: ~5-15ms (computazione rete neurale)
  - **Postprocessing**: ~3ms (NMS, formattazione output)
  - **Overhead Tracking**: ~15-20ms (algoritmo ByteTrack)
  - **Elaborazione Frame Totale**: ~25-40ms (25-40 FPS)

**YOLO11l (Modello Large)**:
  - **Preprocessing**: 2.7ms (preparazione immagine)
  - **Inferenza TensorRT**: 47.1ms (computazione rete neurale)
  - **Postprocessing**: 5.8ms (NMS, formattazione output)
  - **Overhead Tracking**: ~15-20ms (algoritmo ByteTrack)
  - **Elaborazione Frame Totale**: 68-72ms (14-16 FPS)

### Analisi Breakdown Prestazioni
- ✅ **Inferenza TensorRT**: Prestazioni eccellenti vs PyTorch
- ⚠️ **Collo di bottiglia tracking**: Algoritmo ByteTrack è la limitazione principale
- ✅ **Post-processing**: Transfer GPU→CPU ottimizzati
- 💡 **Scelta modello**: Modello Nano per velocità, Large per accuratezza

### Raccomandazioni Ottimizzazione Prestazioni
- ✅ **Usa TensorRT**: Fornisce miglioramento significativo velocità inferenza
- ✅ **Modello raccomandato**: yolo11l.pt per migliore accuratezza, yolo11n per velocità massima se necessario
- ⚠️ **Limitazione tracking**: Algoritmo ByteTrack limita FPS complessivi
- 💡 **Per FPS più alti**: Considera modalità solo detection senza tracking
- 🎯 **Approccio bilanciato**: Le prestazioni attuali sono adatte per meccaniche Squid Game

---

## Risoluzione Problemi Jetson Orin

### Problemi CUDA

Se vedi messaggi come "CUDA not available" o "Using CPU..." nei log, segui questi passi:

**Problema**: PyTorch mostra "CUDA available: False"
```bash
# Soluzione: Installa wheel PyTorch e torchvision CUDA-enabled
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torch-2.5.0a0+872d972e41.nv24.08-cp310-cp310-linux_aarch64.whl
poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/torchvision-0.20.0a0+afc54f7-cp310-cp310-linux_aarch64.whl
```

**Problema**: ONNX Runtime mostra "Failed to start ONNX Runtime with CUDA. Using CPU..."
```bash
# Soluzione: Assicurati che sia installata la versione GPU di ONNX Runtime (potrebbe servire reinstallazione)
poetry run pip uninstall onnxruntime -y && poetry run pip install https://github.com/ultralytics/assets/releases/download/v0.0.0/onnxruntime_gpu-1.20.0-cp310-cp310-linux_aarch64.whl
```

### Comandi di Verifica

**Controlla supporto PyTorch CUDA**:
```bash
poetry run python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

**Controlla provider ONNX Runtime GPU**:
```bash
poetry run python -c "import onnxruntime as ort; print('Available providers:', ort.get_available_providers())"
```

**L'output atteso dovrebbe mostrare**:
- PyTorch: `CUDA available: True`
- ONNX Runtime: `['TensorrtExecutionProvider', 'CUDAExecutionProvider', 'CPUExecutionProvider']`

### Problemi Engine TensorRT

**Problema**: Engine TensorRT fallisce nel caricamento
- **Soluzione**: Assicurati che TensorRT di sistema sia accessibile e compatibile
- **Fallback**: Il sistema automaticamente torna al modello PyTorch
- **Controlla**: Cerca "System TensorRT X.X.X available" nei log

**Problema**: "AttributeError: module 'onnxruntime' has no attribute 'get_available_providers'"
- **Causa**: La versione GPU di ONNX Runtime per Jetson ha API limitate
- **Soluzione**: Il sistema automaticamente usa il modello PyTorch invece
- **Nota**: Questo è comportamento atteso, non un errore

---

## Integrazione Hardware

### Controller ESP32
Per il controllo fisico della bambola, vedi la configurazione ESP32 nella documentazione principale.

### Configurazione Webcam
- **Raccomandato**: Logitech C920 per migliore compatibilità
- **Requisiti**: Controllo esposizione manuale per rilevamento laser
- **Prestazioni**: Tipicamente 10-30 FPS a seconda della scelta del modello

### Sistema Laser (Opzionale)
- **Stato**: Lavoro in corso, targeting base implementato
- **Hardware**: Piattaforma pan-tilt con moduli laser rosso/verde
- **Sicurezza**: Necessarie considerazioni di sicurezza appropriate

---

## Installazione OpenCV CUDA

Per prestazioni ottimali, installa OpenCV con supporto CUDA per accelerare le operazioni di elaborazione immagini.

### Prerequisiti per OpenCV CUDA
- Jetson Orin con JetPack 6.1+ installato
- Almeno 8.5 GB memoria totale (RAM + swap)
- CUDA toolkit installato (verifica con `nvcc --version`)
- **Repository multiverse Ubuntu abilitato** (richiesto per codec multimediali)

### Controllo Sistema Attuale

Prima, verifica la tua installazione OpenCV attuale:

```bash
# Controlla versione OpenCV e supporto CUDA
python3 -c "import cv2; print('OpenCV version:', cv2.__version__); print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"

# Controlla CUDA toolkit
nvcc --version

# Controlla memoria disponibile
free -h && df -h /
```

### Metodi Installazione OpenCV CUDA

#### Metodo 1: Script Automatico (Raccomandato)

L'approccio più semplice usando lo script di installazione automatica di Q-Engineering:

```bash
# Scarica lo script di installazione
wget https://github.com/Qengineering/Install-OpenCV-Jetson-Nano/raw/main/OpenCV-4-13-0.sh

# Rendilo eseguibile
sudo chmod 755 ./OpenCV-4-13-0.sh

# Esegui l'installazione (richiede 2-3 ore)
./OpenCV-4-13-0.sh
```

#### Abilita Repository Multiverse

**IMPORTANTE**: Prima di installare pacchetti multimediali, abilita il repository multiverse:

**Metodo GUI (Raccomandato):**
1. Apri l'utility "Software e Aggiornamenti"
2. Vai alla scheda "Software Ubuntu"
3. Spunta la casella per "Software limitato da copyright o questioni legali (multiverse)"
4. Clicca "Chiudi" e ricarica gli elenchi dei pacchetti quando richiesto

**Metodo Linea di Comando:**
```bash
# Abilita repository multiverse
sudo add-apt-repository multiverse
sudo apt update
```

#### Problemi Comuni Installazione OpenCV

**Errore Pacchetto libfaac-dev Mancante**

Se incontri `E: Unable to locate package libfaac-dev`:

```bash
# Installa codec AAC alternativo
sudo apt update
sudo apt install libfdk-aac-dev

# Installa codec multimediali aggiuntivi (richiede multiverse abilitato)
sudo apt install ubuntu-restricted-extras
sudo apt install libfdk-aac-dev libmp3lame-dev libx264-dev libx265-dev
```

#### Requisiti di Memoria
- **Minimo**: 8.5 GB memoria totale (RAM + swap)
- **Tempo build**: 2-3 ore
- **Raccomandazione**: Imposta swap a 8GB per ridurre tempo di build da 2.5 ore a 1.5 ore

### Verifica OpenCV CUDA

Dopo l'installazione, verifica il supporto CUDA:

```bash
# Testa installazione OpenCV CUDA
python3 -c "
import cv2
print('OpenCV version:', cv2.__version__)
print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    print('✅ Supporto OpenCV CUDA abilitato')
else:
    print('❌ Supporto OpenCV CUDA non trovato')
"
```

### Integrazione con Progetti Poetry

#### Copia CUDA OpenCV nell'Ambiente Poetry (Raccomandato)

Dopo aver compilato CUDA OpenCV a livello di sistema, integralo con il tuo progetto Poetry:

```bash
# Ottieni percorso ambiente virtuale Poetry
VENV_PATH=$(poetry env info --path)

# Copia OpenCV CUDA di sistema nell'ambiente Poetry
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"

# Verifica supporto CUDA
poetry run python -c "import cv2; print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"
```

### Integrazione OpenCV CUDA Squid Game

Il progetto include rilevamento CUDA automatico e accelerazione GPU:

```python
from .cuda_utils import cuda_cvt_color, cuda_resize, is_cuda_opencv_available

# Accelerazione GPU automatica con fallback CPU
gray = cuda_cvt_color(frame, cv2.COLOR_BGR2GRAY)  # Usa GPU se disponibile
resized = cuda_resize(frame, (320, 240))  # Usa GPU se disponibile

# Controlla stato CUDA
if is_cuda_opencv_available():
    print("🚀 OpenCV CUDA abilitato - accelerazione GPU attiva")
else:
    print("ℹ️ Elaborazione OpenCV solo CPU")
```

**Operazioni Accelerate GPU:**
- Conversioni colore (BGR↔RGB, BGR↔Gray)
- Ridimensionamento e scaling immagini
- Filtro Gaussian blur
- Fallback automatico a CPU se le operazioni GPU falliscono

### Benefici Prestazioni OpenCV CUDA

- **Modelli più grandi**: Effetti di accelerazione CUDA più pronunciati
- **Elaborazione tensor**: Migliori prestazioni con più operazioni tensor simultanee
- **Elaborazione immagini**: Significativo speedup per resize, conversione colore e operazioni di filtraggio
- **Combinato con TensorRT**: Prestazioni ottimali per inferenza YOLO + preprocessing OpenCV

### Risoluzione Problemi OpenCV CUDA

**Problema: "CUDA non rilevato nell'ambiente Poetry"**
```bash
# Soluzione: Verifica che la copia sia avvenuta con successo
poetry run python -c "import cv2; print('Location:', cv2.__file__); print('CUDA:', cv2.cuda.getCudaEnabledDeviceCount())"
```

---

## Note di Sviluppo

- L'esposizione della webcam deve essere controllata manualmente per rilevamento laser affidabile
- Le aree di visione devono essere configurate correttamente per far funzionare le meccaniche di gioco
- Il rilevamento volti usa OpenCV Haar cascades per migliore compatibilità cross-platform
- L'elaborazione volti migliorata include rimozione sfondo e miglioramento contorni
- Il targeting laser richiede calibrazione accurata dei parametri di soglia (Lavoro in Corso)
- L'accelerazione OpenCV CUDA fornisce miglioramenti significativi delle prestazioni per elaborazione immagini
- TensorRT + CUDA OpenCV combinati danno prestazioni ottimali per applicazioni real-time