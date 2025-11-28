# # app/services/sam_service.py
# import cv2
# import numpy as np
# from typing import List, Tuple, Optional, Dict, Any
# from threading import Lock

# from sam_model import predictor  # imported from sam_model.py

# # single lock for predictor usage because SamPredictor uses internal state
# _predictor_lock = Lock()

# def _box_to_center_point(box: List[float]) -> Tuple[int, int]:
#     x1, y1, x2, y2 = box
#     cx = int(round((x1 + x2) / 2.0))
#     cy = int(round((y1 + y2) / 2.0))
#     return cx, cy

# def masks_to_polygons(mask: np.ndarray) -> List[List[List[int]]]:
#     # mask: HxW boolean/0-1
#     contours, _ = cv2.findContours(
#         mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
#     )
#     polygons: List[List[List[int]]] = []
#     for c in contours:
#         if len(c) < 3:
#             continue
#         pts = c.reshape(-1, 2).tolist()  # [[x,y], ...]
#         polygons.append([[int(x), int(y)] for (x, y) in pts])
#     return polygons

# def run_sam_on_image(
#     image_path: str,
#     input_points: Optional[List[Tuple[int, int, int]]] = None,
#     input_box: Optional[List[float]] = None,
#     multimask_output: bool = True,
# ) -> List[Dict[str, Any]]:
#     """
#     Runs SAM and returns a list of results:
#     [
#       { "id": 0, "score": 0.95, "polygons": [[[x,y],[x,y],...], ...] },
#       ...
#     ]

#     - input_points: list of (x, y, label) using image natural pixel coords.
#     - input_box: [x1, y1, x2, y2] in natural pixel coords (will be converted to a center point).
#     """

#     if predictor is None:
#         raise RuntimeError("SAM predictor is not loaded (predictor is None)")

#     img = cv2.imread(image_path)
#     if img is None:
#         raise FileNotFoundError(f"Unable to read image: {image_path}")

#     h, w = img.shape[:2]

#     # Build point prompt(s)
#     points = None
#     labels = None

#     if input_points:
#         coords = [[int(p[0]), int(p[1])] for p in input_points]
#         lbs = [int(p[2]) for p in input_points]
#         points = np.array(coords)
#         labels = np.array(lbs)
#     elif input_box:
#         cx, cy = _box_to_center_point(input_box)
#         points = np.array([[cx, cy]])
#         labels = np.array([1])
#     else:
#         # default: center point
#         points = np.array([[w // 2, h // 2]])
#         labels = np.array([1])

#     with _predictor_lock:
#         # set image (updates internal feature maps)
#         predictor.set_image(img)

#         masks, scores, logits = predictor.predict(
#             point_coords=points,
#             point_labels=labels,
#             multimask_output=multimask_output
#         )

#     results = []
#     for i, mask in enumerate(masks):
#         polygons = masks_to_polygons(mask)
#         results.append({
#             "id": i,
#             "score": float(scores[i]) if scores is not None else None,
#             "polygons": polygons,   # polygons in natural pixel coords
#         })
#     return results
