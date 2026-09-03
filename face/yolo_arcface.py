"""Direct ONNX face pipeline used by the live attendance scanner.

The detector asset is deliberately contract-based: this project accepts a
licensed *decoded* YOLOv8-Face ONNX whose output is ``[x,y,w,h,score,10 kps]``
in detector-input pixels.  Different public exports use incompatible raw-head
layouts; accepting one silently would create wrong boxes and wrong embeddings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
import time
from typing import Iterable

import cv2
import numpy as np

from face.cascade import create_frontal_face_cascade


class FaceEngineError(RuntimeError):
    """Raised when a required licensed ONNX asset is unavailable or invalid."""


ARCFACE_TEMPLATE_112 = np.asarray([
    [38.2946, 51.6963], [73.5318, 51.6963], [56.0252, 71.7366],
    [41.5493, 92.3655], [70.7299, 92.3655],
], dtype=np.float32)


@dataclass(frozen=True)
class FaceDetection:
    bbox: tuple[int, int, int, int]
    landmarks: np.ndarray
    score: float


@dataclass
class FaceTrack:
    track_id: int
    bbox: tuple[int, int, int, int]
    landmarks: np.ndarray
    detector_score: float
    last_seen: float
    cached_embedding: np.ndarray | None = None
    cached_prediction: dict | None = None
    completed_prediction: dict | None = None
    appearance_signature: np.ndarray | None = None
    embedding_at: float = 0.0
    completed_at: float = 0.0


def bbox_iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = max(0, aw) * max(0, ah) + max(0, bw) * max(0, bh) - intersection
    return float(intersection / union) if union else 0.0


def nms(detections: Iterable[FaceDetection], threshold: float):
    candidates = list(detections)
    if not candidates:
        return []
    # C++ OpenCV NMS is materially faster than a Python O(n²) loop on raw
    # YOLO heads (up to 8,400 anchors at 640px).
    indices = cv2.dnn.NMSBoxes(
        [list(item.bbox) for item in candidates],
        [float(item.score) for item in candidates],
        score_threshold=0.0,
        nms_threshold=float(threshold),
    )
    return [candidates[int(index)] for index in np.asarray(indices).reshape(-1)]


def limit_detections(detections, max_detections):
    """Keep the strongest post-NMS detections within the per-frame budget."""
    limit = max(0, int(max_detections))
    return sorted(detections, key=lambda item: item.score, reverse=True)[:limit]


def _as_prediction_rows(output):
    """Normalise the declared decoded-YOLO output to rows of >=15 floats."""
    tensor = np.asarray(output, dtype=np.float32)
    if tensor.ndim == 3 and tensor.shape[0] == 1:
        tensor = tensor[0]
    if tensor.ndim != 2:
        raise FaceEngineError('Output YOLO khong dung contract decoded [N,15] / [15,N].')
    if tensor.shape[1] >= 15:
        return tensor
    if tensor.shape[0] >= 15:
        return tensor.T
    raise FaceEngineError('YOLO phai tra bbox, score va du 5 landmarks (toi thieu 15 gia tri).')


def _decoded_face_row(row):
    """Read either project decoded rows or Ultralytics NMS face rows.

    The public YOLOv8n-Face export used by this app emits
    ``x1,y1,x2,y2,score,class,5*(x,y,visibility)`` (21 values), whereas the
    original licensed export emits ``cx,cy,w,h,score,5*(x,y)`` (15 values).
    """
    row = np.asarray(row, dtype=np.float32).reshape(-1)
    if row.size >= 21:
        x1, y1, x2, y2, score = row[:5]
        points = row[6:21].reshape(5, 3)[:, :2]
        return (x1, y1, x2 - x1, y2 - y1), points, float(score)
    if row.size >= 15:
        cx, cy, width, height, score = row[:5]
        return (cx - width / 2, cy - height / 2, width, height), row[5:15].reshape(5, 2), float(score)
    raise FaceEngineError('YOLO khong tra du bbox va 5 landmarks.')


def _sigmoid(values):
    return 1.0 / (1.0 + np.exp(-np.clip(values, -80.0, 80.0)))


def _decode_raw_yolov8_face(outputs, confidence):
    """Decode YOLOv8-Face pose heads: [1, 80, H, W] for strides 8/16/32.

    80 channels = DFL bbox (64) + face score (1) + 5 keypoints * xyz (15).
    The z/visibility coordinate is not required by ArcFace's five-point
    alignment, so only x/y are retained.
    """
    if len(outputs) != 3:
        return None
    decoded = []
    for prediction, stride in zip(outputs, (8, 16, 32)):
        prediction = np.asarray(prediction, dtype=np.float32)
        if prediction.ndim != 4 or prediction.shape[0] != 1 or prediction.shape[1] != 80:
            return None
        _, _, height, width = prediction.shape
        rows = prediction.reshape(1, 80, -1).transpose(0, 2, 1)[0]
        scores = _sigmoid(rows[:, 64])
        mask = scores >= confidence
        if not np.any(mask):
            continue
        rows, scores = rows[mask], scores[mask]
        indices = np.flatnonzero(mask)
        grid_x = indices % width + 0.5
        grid_y = indices // width + 0.5
        dfl = rows[:, :64].reshape(-1, 4, 16)
        dfl = np.exp(dfl - np.max(dfl, axis=2, keepdims=True))
        distances = (dfl / np.sum(dfl, axis=2, keepdims=True)) @ np.arange(16, dtype=np.float32)
        x1, y1 = (grid_x - distances[:, 0]) * stride, (grid_y - distances[:, 1]) * stride
        x2, y2 = (grid_x + distances[:, 2]) * stride, (grid_y + distances[:, 3]) * stride
        keypoints = rows[:, 65:].reshape(-1, 5, 3)
        keypoints[:, :, 0] = (keypoints[:, :, 0] * 2.0 + (indices % width)[:, None]) * stride
        keypoints[:, :, 1] = (keypoints[:, :, 1] * 2.0 + (indices // width)[:, None]) * stride
        for index, score in enumerate(scores):
            decoded.append(FaceDetection(
                (int(round(x1[index])), int(round(y1[index])),
                 int(round(x2[index] - x1[index])), int(round(y2[index] - y1[index]))),
                keypoints[index, :, :2].copy(), float(score),
            ))
    return decoded


class YoloFaceDetector:
    """CPU ONNX adapter for the documented decoded YOLOv8n-Face contract."""

    def __init__(
        self, model_path, input_size, confidence, nms_iou, ort_threads=4,
        max_detections=10,
    ):
        if not os.path.isfile(model_path):
            raise FaceEngineError(
                f'Khong tim thay YOLOv8n-Face ONNX tai {model_path}. '
                'Hay cung cap model da duoc cap quyen va dung output contract 5 landmarks.'
            )
        try:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = max(1, int(ort_threads))
            self.session = ort.InferenceSession(
                model_path, sess_options=options, providers=['CPUExecutionProvider']
            )
        except Exception as exc:
            raise FaceEngineError(f'Khong mo duoc detector YOLO ONNX: {exc}') from exc
        self.model_path = os.path.abspath(model_path)
        self.input = self.session.get_inputs()[0]
        self.output_names = [item.name for item in self.session.get_outputs()]
        self.input_size = int(input_size)
        self.confidence = float(confidence)
        self.nms_iou = float(nms_iou)
        self.max_detections = max(1, int(max_detections))

    def _letterbox(self, image):
        height, width = image.shape[:2]
        scale = min(self.input_size / width, self.input_size / height)
        resized = cv2.resize(image, (round(width * scale), round(height * scale)))
        canvas = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        pad_x = (self.input_size - resized.shape[1]) // 2
        pad_y = (self.input_size - resized.shape[0]) // 2
        canvas[pad_y:pad_y + resized.shape[0], pad_x:pad_x + resized.shape[1]] = resized
        return canvas, scale, pad_x, pad_y

    def detect(self, image):
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return []
        if image.ndim == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        letterboxed, scale, pad_x, pad_y = self._letterbox(image)
        blob = cv2.dnn.blobFromImage(letterboxed, scalefactor=1 / 255.0, swapRB=True)
        outputs = self.session.run(self.output_names, {self.input.name: blob})
        letterbox_detections = _decode_raw_yolov8_face(outputs, self.confidence)
        if letterbox_detections is None:
            rows = _as_prediction_rows(outputs[0])
            letterbox_detections = []
            for row in rows:
                bbox, landmarks, score = _decoded_face_row(row)
                if score < self.confidence:
                    continue
                letterbox_detections.append(FaceDetection(
                    tuple(round(value) for value in bbox),
                    landmarks, score,
                ))
        frame_h, frame_w = image.shape[:2]
        detections = []
        for candidate in letterbox_detections:
            left0, top0, width0, height0 = candidate.bbox
            left = (left0 - pad_x) / scale
            top = (top0 - pad_y) / scale
            right = (left0 + width0 - pad_x) / scale
            bottom = (top0 + height0 - pad_y) / scale
            left, top = max(0, round(left)), max(0, round(top))
            right, bottom = min(frame_w, round(right)), min(frame_h, round(bottom))
            if right <= left or bottom <= top:
                continue
            landmarks = np.asarray(candidate.landmarks, dtype=np.float32).copy()
            landmarks[:, 0] = (landmarks[:, 0] - pad_x) / scale
            landmarks[:, 1] = (landmarks[:, 1] - pad_y) / scale
            detections.append(FaceDetection(
                (int(left), int(top), int(right - left), int(bottom - top)),
                landmarks, candidate.score,
            ))
        post_nms = nms(detections, self.nms_iou)
        return limit_detections(post_nms, self.max_detections)


class HaarCascadeFaceDetector:
    """OpenCV-only emergency detector for enrollment when YOLO assets fail.

    Haar does not predict facial keypoints.  The five points are a documented
    geometric estimate inside the detected frontal-face box so quality gating,
    cropping and the fallback feature extractor can continue safely.
    """

    is_fallback = True
    model_path = 'opencv-haar-cascade'

    def __init__(self, confidence=0.60, max_detections=10):
        self.cascade = create_frontal_face_cascade()
        self.confidence = float(confidence)
        self.max_detections = max(1, int(max_detections))

    @staticmethod
    def _landmarks(x, y, width, height):
        return np.asarray([
            [x + width * .30, y + height * .36], [x + width * .70, y + height * .36],
            [x + width * .50, y + height * .56], [x + width * .35, y + height * .78],
            [x + width * .65, y + height * .78],
        ], dtype=np.float32)

    def detect(self, image):
        if image is None or not isinstance(image, np.ndarray) or image.size == 0:
            return []
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        faces = self.cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        detections = [
            FaceDetection(tuple(int(value) for value in face), self._landmarks(*face), self.confidence)
            for face in faces
        ]
        return limit_detections(detections, self.max_detections)


class ArcFaceRecognizer:
    """Independent ArcFace ONNX session.  Alignment is mandatory."""

    def __init__(self, model_path, ort_threads=4):
        if not os.path.isfile(model_path):
            raise FaceEngineError(
                f'Khong tim thay ArcFace ONNX tai {model_path}. '
                'Hay cung cap recognition model da duoc cap quyen.'
            )
        try:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = max(1, int(ort_threads))
            self.session = ort.InferenceSession(
                model_path, sess_options=options, providers=['CPUExecutionProvider']
            )
        except Exception as exc:
            raise FaceEngineError(f'Khong mo duoc recognizer ArcFace ONNX: {exc}') from exc
        self.model_path = os.path.abspath(model_path)
        self.input = self.session.get_inputs()[0]
        self.output_name = self.session.get_outputs()[0].name

    def align(self, image, landmarks):
        points = np.asarray(landmarks, dtype=np.float32)
        if points.shape != (5, 2) or not np.isfinite(points).all():
            raise FaceEngineError('5 landmarks khong hop le, khong the alignment ArcFace.')
        matrix, _ = cv2.estimateAffinePartial2D(points, ARCFACE_TEMPLATE_112, method=cv2.LMEDS)
        if matrix is None:
            raise FaceEngineError('Khong uoc luong duoc affine transform tu 5 landmarks.')
        return cv2.warpAffine(image, matrix, (112, 112), borderValue=0.0)

    def embed(self, image, landmarks):
        aligned = self.align(image, landmarks)
        rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB).astype(np.float32)
        blob = ((rgb - 127.5) / 128.0).transpose(2, 0, 1)[None, ...]
        vector = np.asarray(self.session.run([self.output_name], {self.input.name: blob})[0]).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(norm) or norm == 0:
            raise FaceEngineError('ArcFace tra embedding khong hop le.')
        return vector.astype(np.float32) / norm


class HOGFaceRecognizer:
    """Deterministic local embedding fallback used only when ArcFace is absent."""

    is_fallback = True
    model_path = 'opencv-hog-normalized-image-vector'

    def __init__(self, *_args, **_kwargs):
        self.hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)

    def align(self, image, landmarks):
        points = np.asarray(landmarks, dtype=np.float32)
        if points.shape != (5, 2) or not np.isfinite(points).all():
            raise FaceEngineError('5 landmarks khong hop le, khong the can chinh khuon mat.')
        matrix, _ = cv2.estimateAffinePartial2D(points, ARCFACE_TEMPLATE_112, method=cv2.LMEDS)
        if matrix is None:
            raise FaceEngineError('Khong uoc luong duoc affine transform tu 5 landmarks.')
        return cv2.warpAffine(image, matrix, (64, 64), borderValue=0.0)

    def embed(self, image, landmarks):
        aligned = self.align(image, landmarks)
        gray = cv2.equalizeHist(cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY))
        vector = self.hog.compute(gray).reshape(-1).astype(np.float32)
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(norm) or norm == 0:
            raise FaceEngineError('Fallback HOG tra embedding khong hop le.')
        return vector / norm


def measure_quality(image, detection, *, min_size, min_brightness, max_brightness, min_blur):
    """Return the quality rejection reason and reusable ROI measurements."""
    x, y, width, height = detection.bbox
    if min(width, height) < min_size:
        return 'face_too_small', {}
    points = np.asarray(detection.landmarks)
    if points.shape != (5, 2) or not np.isfinite(points).all():
        return 'landmarks_invalid', {}
    if (points[:, 0] < x).any() or (points[:, 0] > x + width).any() or (points[:, 1] < y).any() or (points[:, 1] > y + height).any():
        return 'face_out_of_box', {}
    roi = image[y:y + height, x:x + width]
    if roi.size == 0:
        return 'face_out_of_frame', {}
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))
    # Laplacian variance changes substantially with bbox resolution. Measure
    # every face at one canonical scale so a close, sharp face is not rejected
    # merely because its detector box is larger than a previous frame.
    blur_size = 224
    interpolation = cv2.INTER_AREA if max(gray.shape) > blur_size else cv2.INTER_LINEAR
    blur_input = cv2.resize(gray, (blur_size, blur_size), interpolation=interpolation)
    blur_variance = float(cv2.Laplacian(blur_input, cv2.CV_64F).var())
    metrics = {'brightness': brightness, 'blur_variance': blur_variance}
    if brightness < min_brightness:
        return 'face_too_dark', metrics
    if brightness > max_brightness:
        return 'face_too_bright', metrics
    if blur_variance < min_blur:
        return 'face_blurry', metrics
    return None, metrics


def evaluate_quality(image, detection, *, min_size, min_brightness, max_brightness, min_blur):
    reason, _ = measure_quality(
        image, detection, min_size=min_size, min_brightness=min_brightness,
        max_brightness=max_brightness, min_blur=min_blur,
    )
    return reason


class SpatialFaceTracker:
    """Detector-first IoU tracking with short-lived embedding cache.

    It targets up to 10 concurrent faces. This remains a deliberately small
    IoU-only tracker, so crossings and heavy occlusion can still swap track IDs.
    The public interface allows replacing it without changing recognition or
    WebSocket contracts.
    """

    def __init__(self, iou_threshold, ttl_seconds):
        self.iou_threshold = float(iou_threshold)
        self.ttl_seconds = float(ttl_seconds)
        self._tracks: dict[int, FaceTrack] = {}
        self._next_id = 1

    def update(self, detections):
        now = time.monotonic()
        self._tracks = {
            track_id: track for track_id, track in self._tracks.items()
            if now - track.last_seen <= self.ttl_seconds
        }
        unmatched = set(self._tracks)
        assigned = []
        for detection in sorted(detections, key=lambda item: item.score, reverse=True):
            candidates = [(bbox_iou(detection.bbox, self._tracks[track_id].bbox), track_id)
                          for track_id in unmatched]
            score, track_id = max(candidates, default=(0.0, None))
            if track_id is None or score < self.iou_threshold:
                track_id = self._next_id
                self._next_id += 1
                self._tracks[track_id] = FaceTrack(track_id, detection.bbox, detection.landmarks,
                                                   detection.score, now)
            else:
                track = self._tracks[track_id]
                track.bbox = detection.bbox
                track.landmarks = detection.landmarks
                track.detector_score = detection.score
                track.last_seen = now
                unmatched.remove(track_id)
            assigned.append((self._tracks[track_id], detection))
        return assigned
