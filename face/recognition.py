"""YOLOv8n-Face (5 landmarks) + aligned ArcFace gallery recognition."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace
import threading
import time

import cv2
import numpy as np

from config import (
    FACE_DETECTOR_CONFIDENCE, FACE_DETECTOR_MODEL_PATH, FACE_DETECTOR_NMS_IOU,
    FACE_COMPLETED_TRACK_TTL_SECONDS, FACE_DET_SIZE, FACE_EMBEDDING_REFRESH_SECONDS, FACE_GALLERY_META_PATH,
    FACE_GALLERY_PATH, FACE_MATCH_THRESHOLD, FACE_MAX_BRIGHTNESS,
    FACE_MAX_DETECTIONS, FACE_MIN_BLUR_VARIANCE, FACE_MIN_BRIGHTNESS, FACE_MIN_SIZE,
    FACE_RECOGNITION_MODEL_PATH, FACE_TRACK_IOU_THRESHOLD, FACE_TRACK_TTL_SECONDS,
    FACE_ORT_THREADS, FACE_MATCH_MIN_MARGIN, FACE_GALLERY_STAT_INTERVAL_SECONDS,
)
from face.yolo_arcface import (
    ArcFaceRecognizer, FaceEngineError, HaarCascadeFaceDetector, HOGFaceRecognizer,
    SpatialFaceTracker, YoloFaceDetector,
    evaluate_quality,
)


_detector = None
_recognizer = None
_trackers = {}
_tracker_lock = threading.RLock()
_gallery_ids = np.empty((0,), dtype=np.int64)
_gallery_embeddings = np.empty((0, 0), dtype=np.float32)
_gallery_metadata = {}
_gallery_source_mtime = None
_gallery_groups = ()
_gallery_group_source_id = None
_gallery_last_stat_at = None
_model_lock = threading.RLock()


def _normalise_embedding(embedding):
    vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(vector))
    if not np.isfinite(norm) or norm == 0.0:
        raise FaceEngineError('Embedding khuon mat rong hoac khong hop le.')
    return vector / norm


def _load_engine():
    global _detector, _recognizer
    with _model_lock:
        if _detector is None:
            try:
                _detector = YoloFaceDetector(
                    FACE_DETECTOR_MODEL_PATH, FACE_DET_SIZE,
                    FACE_DETECTOR_CONFIDENCE, FACE_DETECTOR_NMS_IOU, FACE_ORT_THREADS,
                    FACE_MAX_DETECTIONS,
                )
            except FaceEngineError:
                _detector = HaarCascadeFaceDetector(
                    FACE_DETECTOR_CONFIDENCE, FACE_MAX_DETECTIONS,
                )
        if _recognizer is None:
            try:
                _recognizer = ArcFaceRecognizer(FACE_RECOGNITION_MODEL_PATH, FACE_ORT_THREADS)
            except FaceEngineError:
                _recognizer = HOGFaceRecognizer()
    return _detector, _recognizer, _get_tracker('default')


def _get_tracker(tracker_key='default'):
    key = str(tracker_key or 'default')
    with _tracker_lock:
        tracker = _trackers.get(key)
        if tracker is None:
            tracker = SpatialFaceTracker(FACE_TRACK_IOU_THRESHOLD, FACE_TRACK_TTL_SECONDS)
            _trackers[key] = tracker
        return tracker


def reset_tracker(tracker_key):
    with _tracker_lock:
        _trackers.pop(str(tracker_key or 'default'), None)


def mark_track_completed(tracker_key, track_id, user_id, confidence=None, match_score=None):
    """Pin a successfully attended identity to an active tracker track."""
    with _tracker_lock:
        tracker = _trackers.get(str(tracker_key or 'default'))
        if tracker is None:
            return False
        track = tracker._tracks.get(int(track_id))
        if track is None:
            return False
        score = match_score if match_score is not None else confidence
        track.completed_prediction = {
            'user_id': int(user_id),
            'confidence': confidence,
            'match_score': score,
            'dikenali': True,
            'recognition_status': 'recognized',
            'completed_track': True,
        }
        track.completed_at = time.monotonic()
        return True


def ensure_model_ready(download=False):
    """Health-check ONNX engine, or report the safe local fallback."""
    if download:
        raise FaceEngineError('Tu dong tai model da bi vo hieu hoa. Hay cai dat ONNX da duoc cap quyen.')
    detector, recognizer, _ = _load_engine()
    return {
        'detector': detector.model_path,
        'recognizer': recognizer.model_path,
        'provider': 'CPUExecutionProvider',
        'fallback_active': bool(getattr(detector, 'is_fallback', False) or getattr(recognizer, 'is_fallback', False)),
        'detector_contract': (
            'YOLOv8-Face raw heads [1,80,H,W] x3 (5 landmarks) or decoded '
            '[N,15]/[15,N]: cx,cy,w,h,score,5 landmarks'
        ),
    }


def get_engine_health():
    try:
        model = ensure_model_ready()
        gallery_ready = _load_gallery()
        return {
            'ready': True, 'model': model, 'gallery_ready': gallery_ready,
            'gallery_templates': int(len(_gallery_ids)),
            'gallery_users': int(len(set(_gallery_ids.tolist()))),
            'threshold': FACE_MATCH_THRESHOLD,
            'automatic_attendance_ready': bool(gallery_ready and FACE_MATCH_THRESHOLD is not None),
        }
    except FaceEngineError as exc:
        return {'ready': False, 'error': str(exc), 'gallery_ready': False,
                'automatic_attendance_ready': False}


def _build_gallery_groups(gallery_ids):
    """Pre-index template positions once instead of masking for every face."""
    return tuple(
        (int(user_id), np.flatnonzero(gallery_ids == user_id))
        for user_id in np.unique(gallery_ids)
    )


def _load_gallery(force=False):
    global _gallery_ids, _gallery_embeddings, _gallery_metadata, _gallery_source_mtime
    global _gallery_groups, _gallery_group_source_id, _gallery_last_stat_at
    with _model_lock:
        stat_now = time.monotonic()
        if (
            not force and _gallery_last_stat_at is not None
            and stat_now - _gallery_last_stat_at < FACE_GALLERY_STAT_INTERVAL_SECONDS
        ):
            return bool(len(_gallery_ids))
        if not os.path.isfile(FACE_GALLERY_PATH):
            _gallery_ids = np.empty((0,), dtype=np.int64)
            _gallery_embeddings = np.empty((0, 0), dtype=np.float32)
            _gallery_metadata = {}
            _gallery_source_mtime = None
            _gallery_groups = ()
            _gallery_group_source_id = id(_gallery_ids)
            _gallery_last_stat_at = stat_now
            return False
        source_mtime = (
            os.path.getmtime(FACE_GALLERY_PATH),
            os.path.getmtime(FACE_GALLERY_META_PATH) if os.path.isfile(FACE_GALLERY_META_PATH) else None,
        )
        if _gallery_source_mtime == source_mtime:
            _gallery_last_stat_at = stat_now
            return bool(len(_gallery_ids))
        try:
            with np.load(FACE_GALLERY_PATH, allow_pickle=False) as gallery:
                ids = np.asarray(gallery['user_ids'], dtype=np.int64)
                embeddings = np.asarray(gallery['embeddings'], dtype=np.float32)
            metadata = {}
            if os.path.isfile(FACE_GALLERY_META_PATH):
                with open(FACE_GALLERY_META_PATH, 'r', encoding='utf-8') as file:
                    metadata = json.load(file)
            if ids.ndim != 1 or embeddings.ndim != 2 or len(ids) != len(embeddings) or not len(ids):
                raise ValueError('gallery phai co user_ids va embeddings cung kich thuoc')
            if metadata.get('schema_version') not in (2, 3):
                raise ValueError('gallery khong dung schema version duoc ho tro; hay chay lai train embedding')
            _gallery_ids = ids
            _gallery_embeddings = np.vstack([_normalise_embedding(row) for row in embeddings])
            _gallery_metadata = metadata
            _gallery_source_mtime = source_mtime
            _gallery_groups = _build_gallery_groups(_gallery_ids)
            _gallery_group_source_id = id(_gallery_ids)
            _gallery_last_stat_at = stat_now
            return True
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise FaceEngineError(f'Khong doc duoc embedding gallery: {exc}') from exc


def reload_model():
    return _load_gallery(force=True)


def _match_embedding_details(embedding):
    with _model_lock:
        gallery_ids = _gallery_ids
        gallery_embeddings = _gallery_embeddings
        gallery_groups = _gallery_groups
        group_source_id = _gallery_group_source_id
    if not len(gallery_ids):
        return None, None, None, None
    if group_source_id != id(gallery_ids):
        gallery_groups = _build_gallery_groups(gallery_ids)
    scores = gallery_embeddings @ _normalise_embedding(embedding)
    user_scores = [
        (user_id, float(np.max(scores[indices])))
        for user_id, indices in gallery_groups
    ]
    user_scores.sort(key=lambda item: item[1], reverse=True)
    best_user, best_score = user_scores[0]
    runner_up_user, runner_up_score = (user_scores[1] if len(user_scores) > 1 else (None, None))
    return best_user, best_score, runner_up_user, runner_up_score


def _match_embedding(embedding):
    """Backward-compatible two-value matcher for existing callers and tests."""
    best_user, best_score, _, _ = _match_embedding_details(embedding)
    return best_user, best_score


def _faces_from_frame(frame):
    """Compatibility adapter for the enrollment trainer: one object per face."""
    if frame is None or not isinstance(frame, np.ndarray):
        return []
    detector, recognizer, _ = _load_engine()
    result = []
    for detection in detector.detect(frame):
        quality_reason = evaluate_quality(
            frame, detection, min_size=FACE_MIN_SIZE, min_brightness=FACE_MIN_BRIGHTNESS,
            max_brightness=FACE_MAX_BRIGHTNESS, min_blur=FACE_MIN_BLUR_VARIANCE,
        )
        if quality_reason:
            continue
        embedding = recognizer.embed(frame, detection.landmarks)
        x, y, width, height = detection.bbox
        result.append(SimpleNamespace(
            bbox=np.asarray([x, y, x + width, y + height], dtype=np.float32),
            kps=detection.landmarks, det_score=detection.score,
            normed_embedding=embedding,
        ))
    return result


def detect_faces(frame):
    detector, _, _ = _load_engine()
    return [item.bbox for item in detector.detect(frame)]


def _appearance_signature(frame, bbox):
    """Small luminance fingerprint used only to invalidate a stale track cache."""
    x, y, width, height = bbox
    roi = frame[y:y + height, x:x + width]
    if roi.size == 0:
        return None
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (16, 16), interpolation=cv2.INTER_AREA).astype(np.float32)


def _appearance_changed(current, previous, threshold=18.0):
    if current is None or previous is None:
        return True
    return float(np.mean(np.abs(current - previous))) >= threshold


def predict(frame, tracker_key='default'):
    """Detect every face quickly; only refresh an ArcFace embedding per track."""
    if frame is None or not isinstance(frame, np.ndarray):
        return []
    started = time.perf_counter()
    _load_gallery()
    detector, recognizer, _ = _load_engine()
    tracker = _get_tracker(tracker_key)

    t_det_start = time.perf_counter()
    detections = detector.detect(frame)
    detector_latency_ms = round((time.perf_counter() - t_det_start) * 1000, 1)

    with _tracker_lock:
        tracked = tracker.update(detections)
    predictions = []
    embedding_latency_total = 0.0
    now = time.monotonic()
    for track, detection in tracked:
        quality_reason = evaluate_quality(
            frame, detection, min_size=FACE_MIN_SIZE, min_brightness=FACE_MIN_BRIGHTNESS,
            max_brightness=FACE_MAX_BRIGHTNESS, min_blur=FACE_MIN_BLUR_VARIANCE,
        )
        signature = _appearance_signature(frame, detection.bbox)
        if track.completed_prediction is not None:
            completed_fresh = now - track.completed_at <= FACE_COMPLETED_TRACK_TTL_SECONDS
            same_appearance = not _appearance_changed(signature, track.appearance_signature)
            if completed_fresh and same_appearance:
                result = dict(track.completed_prediction)
                result.update({
                    'bbox': detection.bbox, 'track_id': track.track_id,
                    'quality_reason': None, 'detector_score': round(detection.score, 4),
                    'landmarks': detection.landmarks.round(1).tolist(),
                })
                predictions.append(result)
                continue
            track.completed_prediction = None
            track.completed_at = 0.0

        if quality_reason:
            track.cached_prediction = None
            predictions.append({
                'user_id': None, 'confidence': None, 'match_score': None,
                'bbox': detection.bbox, 'track_id': track.track_id,
                'dikenali': False, 'recognition_status': 'low_quality',
                'quality_reason': quality_reason, 'detector_score': round(detection.score, 4),
                'landmarks': detection.landmarks.round(1).tolist(),
            })
            continue

        refresh = (track.cached_embedding is None or
                   now - track.embedding_at >= FACE_EMBEDDING_REFRESH_SECONDS or
                   _appearance_changed(signature, track.appearance_signature))
        if refresh:
            t_emb_start = time.perf_counter()
            track.cached_embedding = recognizer.embed(frame, detection.landmarks)
            embedding_latency_total += time.perf_counter() - t_emb_start
            track.appearance_signature = signature
            track.embedding_at = now
            user_id, score, runner_up_user, runner_up_score = _match_embedding_details(track.cached_embedding)
            match_margin = None if runner_up_score is None or score is None else score - runner_up_score
            if user_id is None:
                state, recognised = 'unknown', False
            elif FACE_MATCH_THRESHOLD is None:
                state, recognised = 'needs_calibration', False
            elif score >= FACE_MATCH_THRESHOLD and (match_margin is None or match_margin >= FACE_MATCH_MIN_MARGIN):
                state, recognised = 'recognized', True
            else:
                state, recognised = ('ambiguous', False) if score >= FACE_MATCH_THRESHOLD else ('unknown', False)
            track.cached_prediction = {
                'user_id': user_id, 'confidence': round(score, 4) if score is not None else None,
                'match_score': round(score, 4) if score is not None else None,
                'match_margin': round(match_margin, 4) if match_margin is not None else None,
                'runner_up_user_id': runner_up_user,
                'runner_up_score': round(runner_up_score, 4) if runner_up_score is not None else None,
                'dikenali': recognised, 'recognition_status': state,
            }
        result = dict(track.cached_prediction or {})
        result.update({
            'bbox': detection.bbox, 'track_id': track.track_id,
            'quality_reason': None, 'detector_score': round(detection.score, 4),
            'landmarks': detection.landmarks.round(1).tolist(),
        })
        predictions.append(result)
    embedding_latency_ms = round(embedding_latency_total * 1000, 1)
    pipeline_latency_ms = round((time.perf_counter() - started) * 1000, 1)
    for prediction in predictions:
        prediction['detector_latency_ms'] = detector_latency_ms
        prediction['embedding_latency_ms'] = embedding_latency_ms
        prediction['pipeline_latency_ms'] = pipeline_latency_ms
    return predictions


def predict_single(frame):
    results = predict(frame)
    return max(results, key=lambda item: item['match_score'] or -1) if results else None


def draw_prediction(frame, predictions):
    annotated = frame.copy()
    colors = {'recognized': (0, 255, 0), 'needs_calibration': (0, 215, 255),
              'low_quality': (0, 0, 255), 'unknown': (0, 0, 255), 'ambiguous': (0, 165, 255)}
    for prediction in predictions:
        x, y, width, height = prediction['bbox']
        color = colors.get(prediction.get('recognition_status'), (0, 0, 255))
        cv2.rectangle(annotated, (x, y), (x + width, y + height), color, 2)
    return annotated
