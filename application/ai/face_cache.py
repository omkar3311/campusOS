import os
import numpy as np
import face_recognition
from core.config import CACHE_DIR, LOCAL_IMAGE_ROOT, PARENT_DIR


def get_cache_paths(class_name):
    clean_name = str(class_name).strip().lower().replace(" ", "_")
    return {
        "student_enc": os.path.join(CACHE_DIR, f"{clean_name}_encodings.npy"),
        "student_names": os.path.join(CACHE_DIR, f"{clean_name}_names.npy"),
        "teacher_enc": os.path.join(CACHE_DIR, "teacher_encodings.npy"),
        "teacher_names": os.path.join(CACHE_DIR, "teacher_names.npy"),
        "legacy_student_enc": os.path.join(PARENT_DIR, f"{clean_name}_encodings.npy"),
        "legacy_student_names": os.path.join(PARENT_DIR, f"{clean_name}_names.npy"),
        "legacy_teacher_enc": os.path.join(PARENT_DIR, "teacher_encodings.npy"),
        "legacy_teacher_names": os.path.join(PARENT_DIR, "teacher_names.npy")
    }


def find_student_directories(class_name):
    clean_name = str(class_name).strip().lower().replace(" ", "_")
    candidates = [
        os.path.join(LOCAL_IMAGE_ROOT, clean_name),
        os.path.join(LOCAL_IMAGE_ROOT, f"{clean_name}_faces"),
        os.path.join(PARENT_DIR, "local_filestore", clean_name),
        os.path.join(PARENT_DIR, "local_filestore", f"{clean_name}_faces")
    ]
    return [p for p in candidates if os.path.isdir(p)]


def find_teacher_directories():
    candidates = [
        os.path.join(LOCAL_IMAGE_ROOT, "teachers_faces"),
        os.path.join(PARENT_DIR, "local_filestore", "teachers_faces")
    ]
    return [p for p in candidates if os.path.isdir(p)]


def load_cached_faces(class_name, force_reload=False):
    paths = get_cache_paths(class_name)
    known_faces = []
    known_names = []

    student_encodings = []
    student_names = []
    if not force_reload:
        if os.path.exists(paths["student_enc"]) and os.path.exists(paths["student_names"]):
            try:
                student_encodings = list(np.load(paths["student_enc"], allow_pickle=True))
                student_names = list(np.load(paths["student_names"], allow_pickle=True))
            except Exception:
                student_encodings = []
                student_names = []
        elif os.path.exists(paths["legacy_student_enc"]) and os.path.exists(paths["legacy_student_names"]):
            try:
                student_encodings = list(np.load(paths["legacy_student_enc"], allow_pickle=True))
                student_names = list(np.load(paths["legacy_student_names"], allow_pickle=True))
            except Exception:
                student_encodings = []
                student_names = []

    existing_students = set(student_names)
    student_dirs = find_student_directories(class_name)
    new_found = False

    for s_dir in student_dirs:
        for file_name in os.listdir(s_dir):
            if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            name = os.path.splitext(file_name)[0].lower()
            if name in existing_students:
                continue
            img_path = os.path.join(s_dir, file_name)
            try:
                image = face_recognition.load_image_file(img_path)
                encs = face_recognition.face_encodings(image)
                if encs:
                    student_encodings.append(encs[0])
                    student_names.append(name)
                    existing_students.add(name)
                    new_found = True
            except Exception:
                continue

    if new_found or not os.path.exists(paths["student_enc"]):
        try:
            np.save(paths["student_enc"], student_encodings)
            np.save(paths["student_names"], student_names)
        except Exception:
            pass

    teacher_encodings = []
    teacher_names = []
    if not force_reload:
        if os.path.exists(paths["teacher_enc"]) and os.path.exists(paths["teacher_names"]):
            try:
                teacher_encodings = list(np.load(paths["teacher_enc"], allow_pickle=True))
                teacher_names = list(np.load(paths["teacher_names"], allow_pickle=True))
            except Exception:
                teacher_encodings = []
                teacher_names = []
        elif os.path.exists(paths["legacy_teacher_enc"]) and os.path.exists(paths["legacy_teacher_names"]):
            try:
                teacher_encodings = list(np.load(paths["legacy_teacher_enc"], allow_pickle=True))
                teacher_names = list(np.load(paths["legacy_teacher_names"], allow_pickle=True))
            except Exception:
                teacher_encodings = []
                teacher_names = []

    existing_teachers = set(teacher_names)
    teacher_dirs = find_teacher_directories()
    new_teacher_found = False

    for t_dir in teacher_dirs:
        for file_name in os.listdir(t_dir):
            if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
                continue
            name = os.path.splitext(file_name)[0].lower()
            if name in existing_teachers:
                continue
            img_path = os.path.join(t_dir, file_name)
            try:
                image = face_recognition.load_image_file(img_path)
                encs = face_recognition.face_encodings(image)
                if encs:
                    teacher_encodings.append(encs[0])
                    teacher_names.append(name)
                    existing_teachers.add(name)
                    new_teacher_found = True
            except Exception:
                continue

    if new_teacher_found or not os.path.exists(paths["teacher_enc"]):
        try:
            np.save(paths["teacher_enc"], teacher_encodings)
            np.save(paths["teacher_names"], teacher_names)
        except Exception:
            pass

    for enc, name in zip(student_encodings, student_names):
        known_faces.append(enc)
        known_names.append(f"student_{name}")

    for enc, name in zip(teacher_encodings, teacher_names):
        known_faces.append(enc)
        known_names.append(f"teacher_{name}")

    return known_faces, known_names
