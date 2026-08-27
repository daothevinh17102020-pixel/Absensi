"""Recommend a safe ArcFace cosine threshold from consented evaluation images.

Layout:
  evaluation/<user_id>/*.jpg   known student, not used for enrollment
  evaluation/unknown/*.jpg     people not enrolled in the gallery
"""

import argparse
import json
import os

import cv2

from face.recognition import (
    FaceEngineError,
    _faces_from_frame,
    _load_gallery,
    _match_embedding,
    ensure_model_ready,
)


def _scores_for_image(path):
    image = cv2.imread(path)
    if image is None:
        return []
    return [
        _match_embedding(face.normed_embedding)
        for face in _faces_from_frame(image)
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--evaluation-dir', default='evaluation')
    parser.add_argument('--output', default='models/face_calibration.json')
    args = parser.parse_args()

    try:
        ensure_model_ready(download=True)
        if not _load_gallery():
            raise FaceEngineError('Gallery chua co. Hay chay train_model truoc.')
    except FaceEngineError as exc:
        raise SystemExit(f'[CALIBRATION] {exc}')

    known_scores = []
    unknown_scores = []
    detail = {'known': [], 'unknown': []}
    for folder_name in sorted(os.listdir(args.evaluation_dir)):
        folder = os.path.join(args.evaluation_dir, folder_name)
        if not os.path.isdir(folder):
            continue
        is_unknown = folder_name.lower() == 'unknown'
        try:
            expected_id = None if is_unknown else int(folder_name)
        except ValueError:
            continue
        for filename in sorted(os.listdir(folder)):
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            for candidate_id, score in _scores_for_image(os.path.join(folder, filename)):
                if score is None:
                    continue
                record = {'file': filename, 'candidate_id': candidate_id, 'score': round(score, 5)}
                if is_unknown:
                    unknown_scores.append(score)
                    detail['unknown'].append(record)
                elif candidate_id == expected_id:
                    known_scores.append(score)
                    detail['known'].append(record)

    if not known_scores or not unknown_scores:
        raise SystemExit(
            '[CALIBRATION] Can co it nhat mot score dung va mot score nguoi la. '
            'Khong dat threshold tu du lieu thieu.'
        )

    min_known = min(known_scores)
    max_unknown = max(unknown_scores)
    safe_gap = min_known > max_unknown
    result = {
        'accepted': safe_gap,
        'recommended_face_match_threshold': round((min_known + max_unknown) / 2, 5) if safe_gap else None,
        'min_correct_known_score': round(min_known, 5),
        'max_unknown_score': round(max_unknown, 5),
        'known_score_count': len(known_scores),
        'unknown_score_count': len(unknown_scores),
        'message': (
            'Dat FACE_MATCH_THRESHOLD bang gia tri de xuat va test lai tren camera.'
            if safe_gap else
            'Khong co nguong an toan; bo sung anh dang ky/test, khong bat auto-attendance.'
        ),
        'detail': detail,
    }
    output_dir = os.path.dirname(args.output) or '.'
    os.makedirs(output_dir, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
