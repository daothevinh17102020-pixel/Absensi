"""Server-side quality gate for face enrollment.

The public functions in this module deliberately use the same YOLO 5-point
landmarks as the recognition engine.  This keeps enrollment deterministic on
the CPU machines already supported by the application; a deeper PAD model can
be added later without weakening this gate.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from config import (
    ENROLLMENT_FACE_MAX_RATIO,
    ENROLLMENT_FACE_MIN_RATIO,
    ENROLLMENT_MAX_BRIGHTNESS,
    ENROLLMENT_MIN_BLUR_VARIANCE,
    ENROLLMENT_MIN_SIZE,
    ENROLLMENT_MIN_BRIGHTNESS,
    ENROLLMENT_NEAR_MIN_RATIO,
    ENROLLMENT_FAR_MAX_RATIO,
    ENROLLMENT_FAR_MIN_RATIO,
    ENROLLMENT_POSE_YAW_RATIO,
)
from face.yolo_arcface import measure_quality


ENROLLMENT_STAGES = (
    {'id': 'center', 'label': 'Nhìn thẳng vào camera', 'target': 6},
    {'id': 'left', 'label': 'Quay nhẹ mặt sang trái', 'target': 5},
    {'id': 'right', 'label': 'Quay nhẹ mặt sang phải', 'target': 5},
    {'id': 'near', 'label': 'Đưa mặt lại gần camera', 'target': 4},
    {'id': 'far', 'label': 'Lùi mặt ra xa camera', 'target': 4},
)
ENROLLMENT_TOTAL = sum(stage['target'] for stage in ENROLLMENT_STAGES)

# The browser renders a tall oval in the centre of its 4:3 preview.  These
# normalized radii deliberately include the oval plus a small tolerance for
# object-cover camera crops, while keeping faces at the edge out of enrollment.
_GUIDE_CENTER_X = 0.50
_GUIDE_CENTER_Y = 0.50
_GUIDE_RADIUS_X = 0.24
_GUIDE_RADIUS_Y = 0.42


@dataclass(frozen=True)
class EnrollmentCheck:
    accepted: bool
    reason: str | None
    message: str
    stage: str | None = None
    metrics: dict | None = None
    detection: object | None = None


def stage_for_count(accepted_count: int):
    """Return the server-authoritative stage for the next accepted image."""
    remaining = max(0, int(accepted_count))
    for stage in ENROLLMENT_STAGES:
        if remaining < stage['target']:
            return stage, remaining
        remaining -= stage['target']
    return None, remaining


def stages_for_total(target_total):
    """Return the visible stage plan for the configured enrollment total."""
    remaining = max(0, min(int(target_total), ENROLLMENT_TOTAL))
    stages = []
    for stage in ENROLLMENT_STAGES:
        target = min(stage['target'], remaining)
        if target <= 0:
            break
        stages.append({**stage, 'target': target})
        remaining -= target
    return stages


def manifest_is_complete(samples, target_total=None):
    """Validate the complete, server-authoritative enrollment distribution."""
    if target_total is None:
        target_total = ENROLLMENT_TOTAL
    if not isinstance(samples, list):
        return False
    counts = {stage['id']: 0 for stage in ENROLLMENT_STAGES}
    for sample in samples:
        if isinstance(sample, dict) and sample.get('stage') in counts:
            counts[sample['stage']] += 1
    if target_total == ENROLLMENT_TOTAL:
        return all(counts[stage['id']] >= stage['target'] for stage in ENROLLMENT_STAGES)
    return len(samples) >= target_total


def _pose_metrics(frame, detection, quality_metrics=None):
    x, y, width, height = (float(value) for value in detection.bbox)
    points = np.asarray(detection.landmarks, dtype=np.float32)
    left_eye, right_eye, nose = points[0], points[1], points[2]
    eye_distance = float(np.linalg.norm(right_eye - left_eye))
    eye_midpoint = (left_eye + right_eye) / 2.0
    yaw_ratio = 0.0 if eye_distance < 1.0 else float((nose[0] - eye_midpoint[0]) / eye_distance)
    frame_height, frame_width = frame.shape[:2]
    face_ratio = float((width * height) / float(frame_width * frame_height))
    quality_metrics = quality_metrics or {}
    brightness = float(quality_metrics.get('brightness', 0.0))
    blur = float(quality_metrics.get('blur_variance', 0.0))
    # Higher is better; it is used only to rank already-valid samples.
    brightness_score = max(0.0, 1.0 - abs(brightness - 128.0) / 128.0)
    quality_score = float(
        0.40 * min(1.0, blur / max(1.0, ENROLLMENT_MIN_BLUR_VARIANCE * 2))
        + 0.35 * brightness_score
        + 0.25 * min(1.0, float(detection.score))
    )
    return {
        'yaw_ratio': round(yaw_ratio, 4),
        'face_ratio': round(face_ratio, 4),
        'brightness': round(brightness, 2),
        'blur_variance': round(blur, 2),
        'detector_score': round(float(detection.score), 4),
        'quality_score': round(quality_score, 4),
    }


def _stage_error(stage_id, metrics):
    yaw = metrics['yaw_ratio']
    ratio = metrics['face_ratio']
    if stage_id == 'center' and abs(yaw) > ENROLLMENT_POSE_YAW_RATIO:
        return 'look_center', 'Hãy nhìn thẳng vào camera.'
    # The preview is mirrored, while canvas frames sent to the server are raw.
    # A physical turn to the user's left therefore moves the raw-frame nose to
    # positive X relative to the eye midpoint.
    if stage_id == 'left' and yaw < ENROLLMENT_POSE_YAW_RATIO:
        return 'turn_left', 'Hãy quay nhẹ mặt sang trái rồi giữ yên.'
    if stage_id == 'right' and yaw > -ENROLLMENT_POSE_YAW_RATIO:
        return 'turn_right', 'Hãy quay nhẹ mặt sang phải rồi giữ yên.'
    if stage_id == 'near':
        if ratio < ENROLLMENT_NEAR_MIN_RATIO:
            return 'move_nearer', 'Hãy đưa mặt lại gần camera một chút.'
        if ratio > ENROLLMENT_FACE_MAX_RATIO:
            return 'too_close', 'Bạn đang quá gần camera, hãy lùi ra một chút.'
    if stage_id == 'far':
        if ratio > ENROLLMENT_FAR_MAX_RATIO:
            return 'move_farther', 'Hãy lùi mặt ra xa camera một chút.'
        if ratio < ENROLLMENT_FAR_MIN_RATIO:
            return 'too_far', 'Bạn đang quá xa camera, hãy tiến lại gần một chút.'
    return None, None


def _select_detection_in_guide(detections, frame_shape):
    """Choose the face whose centre best matches the central enrollment oval."""
    frame_height, frame_width = frame_shape[:2]
    candidates = []
    for detection in detections:
        try:
            x, y, width, height = (float(value) for value in detection.bbox)
        except (TypeError, ValueError, AttributeError):
            continue
        if width <= 0 or height <= 0:
            continue
        center_x = (x + width / 2) / frame_width
        center_y = (y + height / 2) / frame_height
        guide_distance = (
            ((center_x - _GUIDE_CENTER_X) / _GUIDE_RADIUS_X) ** 2
            + ((center_y - _GUIDE_CENTER_Y) / _GUIDE_RADIUS_Y) ** 2
        )
        if guide_distance <= 1.0:
            candidates.append((guide_distance, detection))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def validate_enrollment_frame(frame, detector, stage_id):
    """Validate one raw webcam frame for the requested enrollment stage."""
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return EnrollmentCheck(False, 'invalid_image', 'Không đọc được ảnh từ camera.', stage_id)
    detections = detector.detect(frame)
    if not detections:
        return EnrollmentCheck(False, 'face_count', 'Đưa khuôn mặt vào giữa khung hình.', stage_id)
    # Other people outside the guide are harmless.  The only face considered
    # for quality, pose and storage is the one closest to the central oval.
    detection = _select_detection_in_guide(detections, frame.shape)
    if detection is None:
        return EnrollmentCheck(
            False, 'face_outside_guide',
            'Đưa khuôn mặt cần đăng ký vào trong khung oval ở giữa.', stage_id,
        )
    quality_reason, quality_metrics = measure_quality(
        frame, detection,
        min_size=ENROLLMENT_MIN_SIZE,
        min_brightness=ENROLLMENT_MIN_BRIGHTNESS,
        max_brightness=ENROLLMENT_MAX_BRIGHTNESS,
        min_blur=ENROLLMENT_MIN_BLUR_VARIANCE,
    )
    messages = {
        'face_too_small': 'Hãy đưa mặt lại gần camera.',
        'face_too_dark': 'Khuôn mặt quá tối, hãy tăng ánh sáng.',
        'face_too_bright': 'Khuôn mặt quá sáng, hãy tránh ánh đèn chiếu trực tiếp.',
        'face_blurry': 'Khuôn mặt bị mờ, hãy giữ máy và đầu ổn định.',
        'face_out_of_frame': 'Đưa toàn bộ khuôn mặt vào trong khung.',
        'face_out_of_box': 'Đưa khuôn mặt vào giữa khung hình.',
        'landmarks_invalid': 'Không đọc được khuôn mặt, hãy thử lại.',
    }
    if quality_reason:
        return EnrollmentCheck(False, quality_reason, messages.get(quality_reason, 'Ảnh chưa đạt chất lượng.'), stage_id)
    metrics = _pose_metrics(frame, detection, quality_metrics)
    if stage_id not in ('near', 'far') and not ENROLLMENT_FACE_MIN_RATIO <= metrics['face_ratio'] <= ENROLLMENT_FACE_MAX_RATIO:
        message = 'Hãy điều chỉnh khoảng cách để khuôn mặt vừa với khung hướng dẫn.'
        return EnrollmentCheck(False, 'face_size_out_of_range', message, stage_id, metrics, detection)
    stage_reason, message = _stage_error(stage_id, metrics)
    if stage_reason:
        return EnrollmentCheck(False, stage_reason, message, stage_id, metrics, detection)
    return EnrollmentCheck(True, None, 'Ảnh đạt yêu cầu.', stage_id, metrics, detection)


def crop_detected_face(frame, detection, padding=0.20):
    """Crop the detected face with context instead of a fixed centre crop."""
    x, y, width, height = (int(value) for value in detection.bbox)
    frame_height, frame_width = frame.shape[:2]
    pad_x, pad_y = round(width * padding), round(height * padding)
    x0, y0 = max(0, x - pad_x), max(0, y - pad_y)
    x1, y1 = min(frame_width, x + width + pad_x), min(frame_height, y + height + pad_y)
    return frame[y0:y1, x0:x1].copy(), (x0, y0, x1 - x0, y1 - y0)
