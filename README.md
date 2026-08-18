pipeline:

python3 capture.py                    
python3 rgb_mono.py calibrate         
python3 ir_mono.py calibrate left     
python3 ir_mono.py calibrate right    
python3 stereo.py calibrate left-right   
python3 stereo.py calibrate rgb-left     





                         D457
                           │
            capture synchronized frames
                           │
                           ▼
              ┌──────────────────────┐
              │ RGB / LEFT / RIGHT   │
              │ chessboard images    │
              └──────────┬───────────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
            RGB        LEFT       RIGHT
            MONO       MONO        MONO
              │          │          │
              ▼          ▼          ▼
            K_RGB      K_LEFT     K_RIGHT
            D_RGB      D_LEFT     D_RIGHT
              │          │          │
              │          └────┬─────┘
              │               ▼
              │         STEREO LEFT-RIGHT
              │               │
              │            R_LR,T_LR
              │               │
              └──────┐        │
                     ▼        │
                STEREO RGB-LEFT
                     │
                 R_RGBL,T_RGBL
                     │
                     ▼
              ┌─────────────────┐
              │ COMPLETE D457  │
              │ GEOMETRY MODEL │
              └─────────────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
           3D/DEPTH      RGB ALIGNMENT

