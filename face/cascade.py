import os
import shutil
import tempfile

import cv2


CASCADE_FILENAME = 'haarcascade_frontalface_default.xml'


def get_frontal_face_cascade_path():
    """Return a cascade XML path OpenCV can open on Windows.

    OpenCV's C++ file reader can fail on non-ASCII project paths. The venv in
    this repo lives under a Vietnamese folder name, so fall back to an ASCII
    temp path while keeping the original cascade file.
    """
    source_path = os.path.join(cv2.data.haarcascades, CASCADE_FILENAME)

    try:
        source_path.encode('ascii')
        source_is_ascii = True
    except UnicodeEncodeError:
        source_is_ascii = False

    if source_is_ascii:
        test = cv2.CascadeClassifier(source_path)
        if not test.empty():
            return source_path

    fallback_dir = os.path.join(tempfile.gettempdir(), 'absensi_cv2_data')
    os.makedirs(fallback_dir, exist_ok=True)
    fallback_path = os.path.join(fallback_dir, CASCADE_FILENAME)

    fallback = cv2.CascadeClassifier(fallback_path) if os.path.exists(fallback_path) else None
    if fallback is None or fallback.empty():
        shutil.copyfile(source_path, fallback_path)

    return fallback_path


def create_frontal_face_cascade():
    cascade = cv2.CascadeClassifier(get_frontal_face_cascade_path())
    if cascade.empty():
        raise RuntimeError('Failed to load Haar Cascade for frontal face detection.')
    return cascade
