"""PROPOSED relabelling of Hien_Fridge 'others' clusters (cluster ids from cluster_others.py).

Clusters not listed stay dropped. Reviewed by eye on contact sheets 01-04 only (top 160 of 568 clusters).
"""
CLUSTER_LABELS = {
    "jar": [0, 6, 12, 23, 30, 36, 45, 49, 59, 75, 77, 90, 98, 99, 101, 102, 118, 124, 137, 138, 147, 149, 157],
    "orange": [5, 7, 8, 14, 25, 28, 33, 38, 41, 61, 64, 88, 89, 92, 93, 105, 107, 109, 110, 121, 131, 159],
    "pomegranate": [4, 100, 108, 117, 130, 132, 145],
    # candidates NOT in your approved list; need your decision
    "mango": [3, 46, 47, 48, 76, 82, 94, 111, 112, 113, 114, 115, 116, 150],
    "persimmon": [57, 71, 80, 122, 123, 126, 141, 154],
}

# Stage 2: refined subcluster keys ("<prior>:<n>" from refine_others.py) -> final class.
# jar clusters were pure and are used as-is from CLUSTER_LABELS["jar"]. Unlisted subclusters are dropped
# (mango:9 and mango:13 are blown-out yellow blobs of unclear identity).
REFINED_LABELS = {
    "orange": [f"orange:{i}" for i in (0, 1, 2, 3, 4, 5, 7, 9, 10, 11, 12, 13, 15, 17, 19, 20, 22, 24, 25)]
              + [f"pomegranate:{i}" for i in (10, 11, 12)],
    "pomegranate": ["orange:8", "orange:16", "orange:18", "orange:21"]
                   + [f"pomegranate:{i}" for i in range(0, 10)],
    "persimmon": ["orange:6", "orange:14"] + [f"persimmon:{i}" for i in range(3)],
    "mango": [f"mango:{i}" for i in range(18) if i not in (9, 13)],
}

# Stage 3: clusters 160-567 (from cluster_others.py), reviewed by eye on sheets 05-15. Cluster-level labels;
# unlisted clusters stay dropped. Many of these are singletons, so verify_stage3_<class>.jpg spot-checks purity.
STAGE3_LABELS = {
    "jar": [162, 167, 168, 170, 173, 177, 206, 213, 214, 215, 222, 230, 231, 239, 245, 260, 261, 262, 275, 276,
            284, 290, 300, 302, 316, 325, 339, 342, 343, 348, 350, 359, 369, 373, 374, 376, 379, 396,
            412, 414, 421, 423, 425, 426, 439, 443, 461, 465, 475, 478, 481, 488, 493, 495, 497, 498, 500,
            506, 515, 517, 518, 519, 526],
    "orange": [164, 165, 169, 178, 181, 186, 189, 191, 208, 219, 223, 238, 246, 295, 296, 311, 319, 328, 335,
               336, 346, 370, 372, 378, 440, 450, 451, 456, 482, 486, 505, 516, 523, 566],
    "pomegranate": [190, 263, 318, 327, 329, 330, 331, 406, 422, 437, 438, 562, 563, 564],
    "mango": [160, 209, 332, 405, 558, 560, 561],
    "persimmon": [196, 232, 236, 240, 241, 242, 267, 270, 277, 282, 283, 286, 288, 298, 338, 351, 352, 354,
                  366, 367, 371, 464, 466, 467, 468, 469, 474, 477, 480, 496, 520, 525],
    "milk": [211, 253, 254, 326],       # green "Southern Star" milk carton labelled as others
    "apple": [441, 447, 448, 546],
}
