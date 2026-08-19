# RealSense D455/D457 Chessboard Calibration

Kalibracija RGB + levog i desnog IR senzora na Intel RealSense D455/D457 kameri,
korišćenjem klasične šahovnice (chessboard) kao kalibracione table.

> Ovo je chessboard varijanta pipeline-a. Postoji i AprilGrid varijanta
> (preciznija detekcija, robustnija na delimično zaklonjenu tablu) — ako ti
> treba ta verzija umesto ove, javi.

## Kalibraciona tabla

- **9 × 6** unutrašnjih uglova (10×7 kvadrata)
- Veličina kvadrata: **29 mm**
- Standardna štampana šahovnica, mora se poklapati sa `COLS_INNER`,
  `ROWS_INNER`, `SQUARE_SIZE_MM` u kodu

> Tabla mora biti **potpuno ravna** (zalepljena na tvrdu podlogu, ne savijena
> na papiru) — `cv2.findChessboardCorners` je osetljiv na deformaciju ravni,
> mnogo više nego AprilGrid pristup.

## Struktura projekta

```
chessboard_calibration/
├── capture.py          # snimanje sinhronizovanih RGB + IR1 + IR2 slika
├── common.py             # zajedničke helper funkcije (detekcija, YAML I/O)
├── rgb_mono.py            # mono kalibracija RGB senzora
├── ir_mono.py             # mono kalibracija levog/desnog IR senzora
├── stereo.py              # stereo kalibracija (left-right, rgb-left)
├── calib_images/
│   ├── rgb/
│   ├── left_ir/
│   └── right_ir/
└── results/
    ├── rgb_intrinsics.yaml
    ├── left_ir_intrinsics.yaml
    ├── right_ir_intrinsics.yaml
    ├── stereo_left_right.yaml
    └── stereo_rgb_left.yaml
```

## Zavisnosti

```bash
pip3 install pyrealsense2 opencv-python numpy
```

(`opencv-python` je dovoljan ovde — za razliku od AprilGrid varijante, ne
treba `cv2.aruco` modul.)

## Redosled koraka

### 1. Snimanje slika

```bash
python3 capture.py
```

- `SPACE` — čuva sinhronizovani triplet (RGB + IR1 + IR2), samo ako je
  šahovnica detektovana u sva tri frejma
- `Q` — izlaz
- IR emiter (laser projektor) se automatski gasi tokom snimanja jer njegov
  tačkasti pattern ometa detekciju uglova šahovnice
- Preporuka: snimi 15–20+ slika (idealno više, 40–60) sa raznovrsnim uglovima,
  udaljenostima i pozicijama table u kadru, uključujući ivice/uglove slike

**Rezolucija/FPS** (`WIDTH, HEIGHT, FPS` na vrhu fajla) mora da odgovara onome
što tvoja USB veza podržava:

- USB3 veza: `1280, 720, 30` radi za sve tri strimove istovremeno
- USB2 veza: kamera ograničava kombinacije (Color max ~15Hz na 720p, IR max ~5Hz);
  proveri `rs-enumerate-devices -c` i po potrebi koristi `640, 480, 30`

> **Kritično**: ne menjaj rezoluciju između snimanja u isti `calib_images/` folder.
> Mešanje rezolucija u istom skupu slika tiho unosi sistemsku grešku u kalibraciju
> (RMS naraste 2–4×) bez ijedne greške pri izvršavanju. Ako menjaš rezoluciju,
> obriši stare slike i snimi ceo set iznova:
> ```bash
> rm -rf calib_images/rgb calib_images/left_ir calib_images/right_ir
> ```

### 2. Mono kalibracija (mora pre stereo koraka)

```bash
python3 rgb_mono.py calibrate
python3 ir_mono.py calibrate left
python3 ir_mono.py calibrate right
```

Svaka komanda:
- detektuje šahovnicu preko `cv2.findChessboardCorners`, pa je usitnjava na
  subpixel preciznost preko `cv2.cornerSubPix`
- računa `cv2.calibrateCamera` (K, distortion coefficients)
- ispisuje RMS reprojection error po celom skupu i po slici
- čuva rezultat u `results/*_intrinsics.yaml`

**`stereo.py` čita ove `.yaml` fajlove sa diska** — ne računa intrinsics iznova.
Ako ponovo snimiš slike (novi `capture.py` run), moraš ponovo pokrenuti sve
tri mono komande pre stereo koraka, inače stereo kalibracija koristi zastarele
intrinsics iz starog skupa slika.

### 3. Stereo kalibracija

```bash
python3 stereo.py calibrate left-right
python3 stereo.py calibrate rgb-left
```

- Koristi `cv2.CALIB_FIX_INTRINSIC` — mono intrinsics se ne menjaju, računa se
  samo relativna rotacija/translacija (R, T) između dva senzora
- Za svaki par slika zahteva da je šahovnica detektovana u OBA senzora
  istovremeno (`found1 and found2`); u suprotnom se par preskače
- Rezultat (K1, dist1, K2, dist2, R, T, E, F) se čuva u `results/stereo_*.yaml`

## Očekivani rezultati (orijentacija)

| RMS reprojection error | Kvalitet |
|---|---|
| < 0.5 px | vrhunski, pogodno za precizan depth/3D |
| 0.5 – 1.5 px | solidno, standard za robotiku (navigacija, docking) |
| > 2–3 px | problematično — proveri mešane rezolucije, loš fokus, ili savijenu tablu |

RGB senzor obično ima veći RMS od IR senzora (veća fabrička distorzija), i
`stereo_rgb_left` obično ispadne nešto lošiji od `stereo_left_right` (dva
različita tipa senzora umesto identičnog para) — to je očekivano, ne greška.

## Parametri koje treba menjati zajedno

`COLS_INNER`, `ROWS_INNER`, `SQUARE_SIZE_MM` su definisani identično u
`ir_mono.py`, `rgb_mono.py` i `stereo.py` (a `capture.py` ima svoje
`COLS_INNER`/`ROWS_INNER` koji takođe moraju da se poklapaju). Ako menjaš
tablu (drugačija dimenzija kvadrata ili broj polja), ove vrednosti moraju
biti usklađene u svim fajlovima.

## Ograničenja u odnosu na AprilGrid pristup

- Šahovnica mora biti **potpuno vidljiva** da bi se detektovala — jedan
  zaklonjeni ugao odbacuje ceo frejm. AprilGrid detektuje pojedinačne tagove
  nezavisno, pa delimično zaklonjena tabla i dalje daje upotrebljive podatke.
- Detekcija je osetljivija na ugao gledanja, refleksiju i savijenost table.
- Nema built-in ID sistema — ne može se razlikovati orijentacija/deo table
  ako je samo delimično u kadru.

## Debagovanje

- **`Couldn't resolve requests`** pri `capture.py` — tražena kombinacija
  rezolucije/FPS-a nije podržana na trenutnoj USB vezi; proveri
  `rs-enumerate-devices -c` i prilagodi `WIDTH, HEIGHT, FPS`
- **`ModuleNotFoundError: pyrealsense2`** — nije instaliran u aktivnom
  virtualenv-u (`pip3 install pyrealsense2`)
- **Nagli skok u RMS-u posle dodavanja novih slika** — skoro uvek mešane
  rezolucije u istom folderu; obriši i snimi iznova na jednoj rezoluciji
- **`stereo.py` javlja nerealno visok RMS iako su mono rezultati dobri** —
  proveri da li si pokrenula mono kalibracije NA TRENUTNOM skupu slika pre
  stereo koraka (vidi korak 2)
- **Mnogo odbačenih frejmova ("chessboard not found")** — proveri osvetljenje,
  fokus, i da li je tabla dovoljno ravna; šahovnica je manje tolerantna na
  ove faktore nego AprilGrid
