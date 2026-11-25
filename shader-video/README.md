# shader-video

Vidéo de 60 s générée à 100 % par code : un « fragment shader » implémenté en
numpy (aucune image, aucune ressource externe), rendu image par image puis
encodé en H.264 via le ffmpeg embarqué de `imageio-ffmpeg`.

## Pipeline du shader

- **Tunnel spiralé** : coordonnées polaires + torsion logarithmique, flux continu
- **Bruit fractal (fbm, 4 octaves)** avec double warp de domaine
- **Palette cosinus** (type Inigo Quilez) avec dérive chromatique sur la minute
- **Anneaux pulsés** toutes les 4 s
- **Shimmer kaléidoscopique** (6 secteurs) + **étoiles scintillantes** procédurales
- **Grade** : tonemap ACES approx, gamma 2.2, vignette, dithering anti-banding,
  fondu d'ouverture / fermeture

## Usage

```bash
pip install numpy imageio-ffmpeg

# rendu complet (1800 frames, ~20-25 min sur CPU) -> shader_video.mp4
python3 shader_video.py

# rendu d'un intervalle de frames (.movie partiel, pour test)
python3 shader_video.py 0 300 test.mp4
```

Sortie : 1280x720, 30 fps, 60 s, H.264 yuv420p (`+faststart`).
