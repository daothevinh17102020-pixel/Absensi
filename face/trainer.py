"""Build a compact, pose-diverse ArcFace gallery from enrollment samples."""

import json
import os
import tempfile

import cv2
import numpy as np

from config import (
    DATASET_PATH, FACE_GALLERY_MAX_TEMPLATES_PER_USER, FOTO_PER_USER,
    FACE_GALLERY_META_PATH, FACE_GALLERY_PATH,
)
from face.enrollment import ENROLLMENT_TOTAL, manifest_is_complete
from face.recognition import FaceEngineError, _faces_from_frame, _normalise_embedding, reload_model


_STAGE_QUOTAS = {'center': 3, 'left': 2, 'right': 2, 'near': 2, 'far': 2}


def _atomic_json_dump(path, payload):
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.face-gallery-', suffix='.json', dir=directory)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _atomic_npz_dump(path, user_ids, embeddings):
    directory = os.path.dirname(path) or '.'
    os.makedirs(directory, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.face-gallery-', suffix='.npz', dir=directory)
    os.close(handle)
    try:
        np.savez_compressed(temporary, user_ids=user_ids, embeddings=embeddings)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _read_manifest(user_path):
    """Return manifest samples and their enrollment state.

    A missing manifest denotes the legacy import format.  A present but
    malformed or incomplete manifest must never leak partial enrollment data
    into the realtime gallery.
    """
    path = os.path.join(user_path, 'enrollment_manifest.json')
    if not os.path.isfile(path):
        return {}, 'legacy'
    try:
        with open(path, 'r', encoding='utf-8') as file:
            payload = json.load(file)
        samples = payload.get('samples', [])
        if not isinstance(samples, list):
            return {}, 'invalid'
        manifest = {
            item.get('file'): item for item in samples
            if isinstance(item, dict) and isinstance(item.get('file'), str) and item.get('file')
        }
        target_total = min(FOTO_PER_USER, ENROLLMENT_TOTAL)
        if len(manifest) != len(samples) or not manifest_is_complete(samples, target_total=target_total):
            return manifest, 'incomplete'
        return manifest, 'complete'
    except (OSError, ValueError, json.JSONDecodeError):
        return {}, 'invalid'


def _candidate_score(manifest_sample, detection):
    metrics = manifest_sample.get('metrics', {}) if manifest_sample else {}
    try:
        return float(metrics.get('quality_score', getattr(detection, 'det_score', 0.0)))
    except (TypeError, ValueError):
        return float(getattr(detection, 'det_score', 0.0))


def _not_exact_duplicate(candidate, selected):
    return not any(np.allclose(candidate['embedding'], item['embedding'], rtol=1e-6, atol=1e-6) for item in selected)


def select_diverse_templates(candidates, limit=FACE_GALLERY_MAX_TEMPLATES_PER_USER):
    """Keep the best views per stage, then fill remaining slots by quality."""
    selected = []
    for stage, quota in _STAGE_QUOTAS.items():
        stage_candidates = sorted(
            (item for item in candidates if item['stage'] == stage),
            key=lambda item: item['quality_score'], reverse=True,
        )
        for item in stage_candidates:
            if len(selected) >= limit or sum(value['stage'] == stage for value in selected) >= quota:
                break
            if _not_exact_duplicate(item, selected):
                selected.append(item)
    for item in sorted(candidates, key=lambda value: value['quality_score'], reverse=True):
        if len(selected) >= limit:
            break
        if _not_exact_duplicate(item, selected):
            selected.append(item)
    return selected[:limit]


def train_model():
    """Prepare at most 12 normalised, diverse templates per enrolled student."""
    profiles, user_ids = [], []
    diagnostics = {
        'schema_version': 3,
        'gallery_strategy': 'pose_balanced_bounded_templates',
        'max_templates_per_user': FACE_GALLERY_MAX_TEMPLATES_PER_USER,
        'users': {}, 'accepted_total': 0, 'rejected_total': 0,
    }
    if not os.path.isdir(DATASET_PATH):
        print('[TRAINER] Folder dataset tidak ditemukan.')
        return False
    try:
        for folder_name in sorted(os.listdir(DATASET_PATH)):
            user_path = os.path.join(DATASET_PATH, folder_name)
            if not os.path.isdir(user_path):
                continue
            try:
                user_id = int(folder_name)
            except ValueError:
                continue
            manifest, manifest_state = _read_manifest(user_path)
            candidates, rejected = [], []
            if manifest_state in {'invalid', 'incomplete'}:
                rejected.append({'file': 'enrollment_manifest.json', 'reason': f'{manifest_state}_manifest'})
                diagnostics['rejected_total'] += len(rejected)
                diagnostics['users'][str(user_id)] = {
                    'accepted': 0, 'selected': 0, 'rejected': rejected,
                    'selected_files': [], 'manifest_state': manifest_state,
                }
                continue

            # New enrollment data is an allow-list: do not train from files
            # that the server did not accept into its completed manifest.
            filenames = (
                sorted(manifest)
                if manifest_state == 'complete'
                else sorted(os.listdir(user_path))
            )
            for filename in filenames:
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                image = cv2.imread(os.path.join(user_path, filename))
                if image is None:
                    rejected.append({'file': filename, 'reason': 'invalid_image'})
                    continue
                faces = _faces_from_frame(image)
                if len(faces) != 1:
                    rejected.append({'file': filename, 'reason': f'face_count_{len(faces)}'})
                    continue
                sample = manifest.get(filename, {})
                candidates.append({
                    'file': filename, 'stage': sample.get('stage', 'legacy'),
                    'quality_score': _candidate_score(sample, faces[0]),
                    'embedding': _normalise_embedding(faces[0].normed_embedding),
                })
            selected = select_diverse_templates(candidates)
            diagnostics['accepted_total'] += len(candidates)
            diagnostics['rejected_total'] += len(rejected)
            diagnostics['users'][str(user_id)] = {
                'accepted': len(candidates), 'selected': len(selected), 'rejected': rejected,
                'selected_files': [item['file'] for item in selected], 'manifest_state': manifest_state,
            }
            user_ids.extend([user_id] * len(selected))
            profiles.extend(item['embedding'] for item in selected)
        if not profiles:
            print('[TRAINER] Tidak ada foto dengan tepat satu wajah yang valid.')
            if os.path.exists(FACE_GALLERY_PATH):
                try:
                    os.remove(FACE_GALLERY_PATH)
                except OSError:
                    pass
            diagnostics['gallery_users'] = []
            diagnostics['gallery_templates'] = 0
            _atomic_json_dump(FACE_GALLERY_META_PATH, diagnostics)
            reload_model()
            return False
        _atomic_npz_dump(
            FACE_GALLERY_PATH,
            np.asarray(user_ids, dtype=np.int64),
            np.asarray(profiles, dtype=np.float32),
        )
        diagnostics['gallery_users'] = sorted(set(user_ids))
        diagnostics['gallery_templates'] = len(profiles)
        _atomic_json_dump(FACE_GALLERY_META_PATH, diagnostics)
        reload_model()
        print(f'[TRAINER] Gallery ready: {len(set(user_ids))} users / {len(profiles)} templates.')
        return True
    except FaceEngineError as exc:
        print(f'[TRAINER] Model InsightFace tidak siap: {exc}')
        return False
