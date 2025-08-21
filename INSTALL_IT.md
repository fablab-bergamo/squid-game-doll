# Guida all'Installazione - Raspberry Pi 5 + Hailo AI KIT

> **Nota**: Questa guida all'installazione è specifica per Raspberry Pi 5 con hardware Hailo AI KIT. Per altre piattaforme (PC/Windows, Jetson Nano), consultare i file [README.md](README.md) ([Italiano](README-it.md)) e [CLAUDE.md](CLAUDE.md) principali.

## Prerequisiti

* Raspberry Pi 5 con Hailo AI KIT installato e configurato correttamente
* Webcam USB (testata) o modulo camera Raspberry Pi
* Scheda SD con Raspberry Pi OS (consigliato 64-bit)
* Connessione internet per l'installazione dei pacchetti

## Configurazione Hardware

### Configurazione Camera
Assicurarsi che la webcam sia collegata correttamente e riconosciuta:

```shell
# Elencare i dispositivi camera disponibili
v4l2-ctl --list-devices

# Testare la configurazione della camera (opzionale)
v4l2-ctl -v width=1920,height=1080,pixelformat=MJPG
v4l2-ctl --stream-mmap=3 --stream-to=/dev/null --stream-count=250
```

## Installazione Software

### 1. Installare lo Stack Software Hailo

Installare i pacchetti software Hailo AI Kit:

```shell
sudo apt update
sudo apt install hailo-all
sudo apt install python3-gi
sudo reboot
```

### 2. Verificare l'Installazione Hailo

Verificare che il chip Hailo sia riconosciuto correttamente:

```shell
hailortcli fw-control identify
```

L'output dovrebbe mostrare:
```
Executing on device: 0000:01:00.0
Identifying board
Control Protocol Version: 2
Firmware Version: 4.20.0 (release,app,extended context switch buffer)
Logger Version: 0
Board Name: Hailo-8
Device Architecture: HAILO8L
Serial Number: xxxxxxxxxxxxxxx
Part Number: HM21LB1C2LAE
Product Name: HAILO-8L AI ACC M.2 B+M KEY MODULE EXT TMP
```

### 3. Installare le Dipendenze del Progetto

Clonare il repository e installare il software Squid Game Doll:

```bash
# Installare Poetry (gestore dipendenze Python)
pip install poetry

# Installare le dipendenze del progetto e configurare l'ambiente virtuale
poetry install

# Installare le dipendenze specifiche per Hailo
poetry run pip install git+https://github.com/hailo-ai/hailo-apps-infra.git

# Scaricare il modello Hailo pre-addestrato
wget https://hailo-model-zoo.s3.eu-west-2.amazonaws.com/ModelZoo/Compiled/v2.14.0/hailo8l/yolov11m.hef
```

## Configurazione e Test

### 1. Trovare l'Indice della Camera

Testare l'applicazione per identificare il dispositivo camera corretto:

```bash
poetry run python -m src.squid_game_doll.run
```

L'applicazione elencherà le camere disponibili. Cercare i dispositivi webcam USB (tipicamente numeri più bassi) tra i dispositivi specifici del Raspberry Pi:

```
Hello from the pygame community. https://www.pygame.org/contribute.html
SquidGame(res=(1920, 1080) on #0, tracker disabled=True, ip=192.168.45.50)
Listing webcams with capabilities:
	 0: USB Camera: USB Camera          # <-- Webcam USB (usare questa)
	 1820: pispbe-input                 # <-- Dispositivi specifici Pi
	 1821: pispbe-tdn_input
	 1822: pispbe-stitch_input
	 [... altri dispositivi specifici Pi ...]
	 1819: rpivid
```

### 2. Configurare le Aree di Visione

Eseguire la modalità setup per configurare le aree di rilevamento:

```bash
# Usare l'indice webcam identificato (es. 0 per camera USB)
poetry run python -m src.squid_game_doll.run --setup -w 0
```

Seguire le istruzioni sullo schermo per definire:
- **Zona di Partenza**: Dove i giocatori registrano i loro volti
- **Zona Traguardo**: Area obiettivo che i giocatori devono raggiungere
- **Area di Visione**: Area di rilevamento per il monitoraggio del movimento

### 3. Eseguire il Gioco

Avviare il gioco con la camera configurata:

```bash
# Sostituire 0 con l'indice camera effettivo
poetry run python -m src.squid_game_doll.run -w 0
```

## Opzionale: Integrazione Laser ESP32

Per abilitare la bambola animata con puntamento laser:

```bash
# Abilitare il tracker ESP32 con IP specifico
poetry run python -m src.squid_game_doll.run -w 0 -k -i 192.168.45.50
```

Vedere la [documentazione ESP32](esp32/) per i dettagli di configurazione hardware.

## Risoluzione Problemi

### Problemi Camera
- Se non viene rilevata nessuna camera USB, controllare l'output di `lsusb`
- Provare porte USB o cavi diversi
- Verificare i permessi della camera: `ls -la /dev/video*`

### Problemi Hailo
- Assicurarsi che l'AI KIT sia inserito correttamente nello slot M.2
- Controllare `dmesg | grep hailo` per messaggi hardware
- Verificare l'installazione Hailo: `hailortcli scan`

Per ulteriore aiuto, consultare [CLAUDE.md](CLAUDE.md) per informazioni dettagliate sullo sviluppo.