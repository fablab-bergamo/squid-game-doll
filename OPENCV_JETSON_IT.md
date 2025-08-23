# Guida Installazione OpenCV CUDA per Jetson Nano

Questa guida fornisce istruzioni dettagliate per installare OpenCV con supporto CUDA su Jetson Nano.

## Prerequisiti

- Jetson Nano con JetPack installato
- Almeno 8.5 GB di memoria totale (RAM + swap)
- CUDA toolkit installato (verificare con `nvcc --version`)
- **Repository multiverse Ubuntu abilitato** (richiesto per codec multimediali)

## Controllo Sistema Attuale

Prima, verifica la tua installazione OpenCV attuale:

```bash
# Verifica versione OpenCV e supporto CUDA
python3 -c "import cv2; print('OpenCV version:', cv2.__version__); print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"

# Verifica CUDA toolkit
nvcc --version

# Verifica memoria disponibile
free -h && df -h /
```

## Metodi di Installazione

### Metodo 1: Script Automatico (Raccomandato)

L'approccio più semplice usando lo script automatico di Q-Engineering:

```bash
# Scarica lo script di installazione
wget https://github.com/Qengineering/Install-OpenCV-Jetson-Nano/raw/main/OpenCV-4-13-0.sh

# Rendilo eseguibile
sudo chmod 755 ./OpenCV-4-13-0.sh

# Esegui l'installazione (richiede 2-3 ore)
./OpenCV-4-13-0.sh
```

## Problemi Comuni e Soluzioni

### Abilita Repository Multiverse

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

### Errore Pacchetto libfaac-dev Mancante

Se incontri `E: Unable to locate package libfaac-dev`:

```bash
# Installa codec AAC alternativo
sudo apt update
sudo apt install libfdk-aac-dev

# Installa codec multimediali aggiuntivi (richiede multiverse abilitato)
sudo apt install ubuntu-restricted-extras
sudo apt install libfdk-aac-dev libmp3lame-dev libx264-dev libx265-dev
```

### Requisiti di Memoria

- **Minimo**: 8.5 GB di memoria totale (RAM + swap)
- **Tempo di build**: 2-3 ore
- **Raccomandazione**: Imposta swap a 8GB per ridurre tempo di build da 2.5 ore a 1.5 ore

## Verifica

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

## Integrazione con Progetti Poetry

### Metodo 1: Copia OpenCV CUDA nell'Ambiente Poetry (Raccomandato)

Dopo aver compilato OpenCV CUDA a livello di sistema, integralo con il tuo progetto Poetry:

```bash
# Ottieni percorso ambiente virtuale Poetry
VENV_PATH=$(poetry env info --path)

# Copia OpenCV CUDA di sistema nell'ambiente Poetry
cp -r /usr/lib/python3/dist-packages/cv2* "$VENV_PATH/lib/python3.10/site-packages/"

# Verifica supporto CUDA
poetry run python -c "import cv2; print('CUDA devices:', cv2.cuda.getCudaEnabledDeviceCount())"
```


## Integrazione con Progetto Squid Game

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

## Vantaggi Prestazioni

- **Modelli più grandi**: Effetti di accelerazione CUDA più pronunciati
- **Elaborazione tensor**: Migliori prestazioni con più operazioni tensor simultanee
- **Elaborazione immagini**: Significativo speedup per resize, conversione colore e operazioni di filtraggio
- **Combinato con TensorRT**: Prestazioni ottimali per inferenza YOLO + preprocessing OpenCV

## Risoluzione Problemi

### Risoluzione Problemi Integrazione Poetry

**Problema: "CUDA non rilevato nell'ambiente Poetry"**
```bash
# Soluzione: Verifica che la copia sia avvenuta con successo
poetry run python -c "import cv2; print('Location:', cv2.__file__); print('CUDA:', cv2.cuda.getCudaEnabledDeviceCount())"
```

---

*Ultimo aggiornamento: 2025-08-23*
*Compatibile con: JetPack 5.x, Ubuntu 22.04 LTS, Poetry 1.8+*