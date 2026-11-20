# Held-out real-fridge evaluation (160 photos)

Produced by `ml/diagnose_real_fridge.py --data data/real_fridge/data_heldout.yaml`. Weights: `baseline_v8n`; imgsz 640; NMS iou 0.7; matching at IoU >= 0.5, one-to-one, greedy by confidence. Ignored classes: ['jar']. These 160 photos are never used for training or tuning.

160 photos, 663 ground-truth boxes after ignoring (302 ignored-class boxes removed).

## Headline

| conf | Localization recall | Class-correct share (localized) | End-to-end recall | Predictions/image | End-to-end precision |
|---|---|---|---|---|---|
| 0.25 | 11.9% (79/663) | 38.0% | 4.7% (31/663) | 2.7 | 7.2% |
| 0.001 | 73.9% (490/663) | 22.7% | 29.7% (197/663) | 156.6 | 0.8% |

Predictions that landed on an ignored-class box and were not counted: conf 0.25: 58, conf 0.001: 745.

## Per class (localization / end-to-end recall)

| Class | GT boxes | conf 0.25 | conf 0.001 |
|---|---|---|---|
| cheese | 94 | 9% / 1% | 77% / 35% |
| egg | 92 | 10% / 3% | 83% / 41% |
| milk | 91 | 21% / 19% | 86% / 58% |
| yogurt | 76 | 11% / 5% | 71% / 34% |
| butter | 63 | 3% / 2% | 67% / 21% |
| cream | 54 | 37% / 0% | 94% / 11% |
| apple | 51 | 0% / 0% | 35% / 4% |
| avocado | 16 | 0% / 0% | 44% / 6% |
| spinach | 15 | 0% / 0% | 80% / 13% |
| chicken | 12 | 17% / 0% | 92% / 17% |
| tomato | 11 | 36% / 36% | 91% / 73% |
| lemon | 10 | 10% / 0% | 90% / 40% |
| beef (low support) | 9 | 11% / 0% | 89% / 11% |
| onion (low support) | 9 | 11% / 0% | 89% / 0% |
| strawberries (low support) | 9 | 11% / 11% | 100% / 44% |
| bell_pepper (low support) | 7 | 14% / 0% | 71% / 14% |
| chocolate (low support) | 7 | 14% / 0% | 86% / 0% |
| bread (low support) | 6 | 0% / 0% | 100% / 17% |
| lime (low support) | 5 | 0% / 0% | 20% / 20% |
| orange (low support) | 5 | 0% / 0% | 0% / 0% |
| carrot (low support) | 5 | 0% / 0% | 20% / 0% |
| blueberries (low support) | 5 | 20% / 0% | 20% / 20% |
| mushrooms (low support) | 3 | 0% / 0% | 100% / 0% |
| pomegranate (low support) | 2 | 0% / 0% | 0% / 0% |
| bacon (low support) | 2 | 0% / 0% | 0% / 0% |
| banana (low support) | 1 | 0% / 0% | 100% / 0% |
| corn (low support) | 1 | 0% / 0% | 0% / 0% |
| ham (low support) | 1 | 0% / 0% | 100% / 0% |
| mango (low support) | 1 | 0% / 0% | 0% / 0% |

## Confusion at conf 0.25: true class -> predicted class (correctly localized boxes, IoU >= 0.5)

79 boxes localized; 30 with the right class; 49 with a wrong class. Top wrong pairs:

| True class | Predicted | Count |
|---|---|---|
| cream | milk | 18 |
| cheese | butter | 3 |
| yogurt | milk | 3 |
| cheese | yogurt | 2 |
| milk | sugar | 2 |
| egg | yogurt | 2 |
| butter | cheese | 1 |
| cheese | chocolate | 1 |
| cheese | shrimp | 1 |
| cream | egg | 1 |
| bell_pepper | egg | 1 |
| yogurt | butter | 1 |
| lemon | cheese | 1 |
| chicken | milk | 1 |
| milk | yogurt | 1 |
| blueberries | milk | 1 |
| chicken | yogurt | 1 |
| egg | flour | 1 |
| onion | egg | 1 |
| chocolate | cream | 1 |
| cream | butter | 1 |
| beef | bacon | 1 |
| egg | potato | 1 |
| egg | bread | 1 |
| egg | shrimp | 1 |

Per true class, the most common predictions among localized boxes:

| True class | Localized | Predicted classes (count) |
|---|---|---|
| cream | 20 | milk 18, egg 1, butter 1 |
| milk | 19 | milk 16, sugar 2, yogurt 1 |
| egg | 9 | egg 3, yogurt 2, flour 1, potato 1 |
| cheese | 8 | butter 3, yogurt 2, chocolate 1, shrimp 1 |
| yogurt | 8 | yogurt 4, milk 3, butter 1 |
| tomato | 4 | tomato 4 |
| butter | 2 | cheese 1, butter 1 |
| chicken | 2 | milk 1, yogurt 1 |
| bell_pepper | 1 | egg 1 |
| lemon | 1 | cheese 1 |
| blueberries | 1 | milk 1 |
| strawberries | 1 | strawberries 1 |
| onion | 1 | egg 1 |
| chocolate | 1 | cream 1 |
| beef | 1 | bacon 1 |

## Confusion at conf 0.001: true class -> predicted class (correctly localized boxes, IoU >= 0.5)

490 boxes localized; 111 with the right class; 379 with a wrong class. Top wrong pairs:

| True class | Predicted | Count |
|---|---|---|
| cream | milk | 35 |
| egg | cheese | 13 |
| butter | milk | 13 |
| cheese | milk | 11 |
| butter | cheese | 11 |
| egg | yogurt | 10 |
| cheese | yogurt | 9 |
| cheese | butter | 9 |
| milk | yogurt | 8 |
| milk | sugar | 8 |
| yogurt | milk | 6 |
| onion | egg | 6 |
| yogurt | butter | 6 |
| cheese | egg | 6 |
| egg | milk | 6 |
| yogurt | blueberries | 6 |
| egg | potato | 5 |
| apple | tomato | 5 |
| cheese | chocolate | 5 |
| cheese | flour | 5 |
| cream | sugar | 4 |
| milk | egg | 4 |
| egg | bread | 4 |
| cheese | ham | 4 |
| apple | cheese | 4 |

Per true class, the most common predictions among localized boxes:

| True class | Localized | Predicted classes (count) |
|---|---|---|
| milk | 78 | milk 39, yogurt 8, sugar 8, egg 4 |
| egg | 76 | egg 18, cheese 13, yogurt 10, milk 6 |
| cheese | 72 | cheese 13, milk 11, yogurt 9, butter 9 |
| yogurt | 54 | yogurt 20, milk 6, butter 6, blueberries 6 |
| cream | 51 | milk 35, sugar 4, flour 2, yogurt 2 |
| butter | 42 | milk 13, cheese 11, yogurt 3, sugar 3 |
| apple | 18 | tomato 5, cheese 4, egg 2, apple 1 |
| spinach | 12 | avocado 3, bacon 3, green_beans 2, chocolate 2 |
| chicken | 11 | milk 2, bacon 2, yogurt 2, cheese 2 |
| tomato | 10 | tomato 8, ham 1, egg 1 |
| lemon | 9 | egg 3, cheese 2, lemon 2, banana 1 |
| strawberries | 9 | strawberries 3, avocado 2, tomato 2, shrimp 1 |
| beef | 8 | shrimp 3, bread 2, ham 2, bacon 1 |
| onion | 8 | egg 6, sweet_potato 1, flour 1 |
| avocado | 7 | blueberries 2, avocado 1, lemon 1, yogurt 1 |
| bread | 6 | cheese 2, flour 2, shrimp 1, bread 1 |
| chocolate | 6 | cream 2, yogurt 1, lime 1, cheese 1 |
| bell_pepper | 5 | tomato 1, egg 1, yogurt 1, avocado 1 |
| mushrooms | 3 | spinach 1, cheese 1, egg 1 |
| banana | 1 | cheese 1 |
| lime | 1 | lime 1 |
| blueberries | 1 | milk 1 |
| ham | 1 | flour 1 |
| carrot | 1 | shrimp 1 |

## 20 worst crops

The 20 localized boxes with the wrong class that the model was most confident about (conf 0.001 run). Sheet: `ml/runs/real_fridge_diagnostics/confusion_heldout_worst20.png` (photo crops, not committed):

1. yogurt -> milk (0.93), `IMG_7992`
2. cream -> milk (0.92), `IMG_7994`
3. cream -> milk (0.89), `IMG_6568`
4. cream -> butter (0.88), `IMG_6569`
5. cream -> milk (0.87), `IMG_7992`
6. yogurt -> milk (0.86), `IMG_7995`
7. cream -> milk (0.79), `IMG_7995`
8. egg -> potato (0.77), `IMG_6686`
9. egg -> yogurt (0.75), `E301A6DE-6880-416E-A8ED-F12A802029F3 2`
10. yogurt -> milk (0.74), `IMG_7994`
11. cream -> milk (0.69), `IMG_7995`
12. cream -> milk (0.69), `6F610D76-46B0-424D-9A0E-62F44CF67106 2`
13. cream -> milk (0.69), `6F610D76-46B0-424D-9A0E-62F44CF67106 2`
14. cheese -> butter (0.67), `IMG_6566`
15. cream -> milk (0.67), `IMG_3763`
16. milk -> sugar (0.65), `IMG_6555`
17. cream -> milk (0.63), `IMG_3761`
18. butter -> cheese (0.57), `81613504558__B329DFEC-E856-4DB3-AE69-01C`
19. egg -> yogurt (0.56), `IMG_6568`
20. cream -> milk (0.56), `IMG_3758`
