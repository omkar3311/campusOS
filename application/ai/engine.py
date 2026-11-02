import cv2
import time
import numpy as np
import face_recognition
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
from core.config import YOLO_MODEL_PATH
from ai.face_cache import load_cached_faces
from ai.liveness import evaluate_liveness

_shared_yolo = None


def get_shared_yolo_model():
    global _shared_yolo
    if _shared_yolo is None:
        _shared_yolo = YOLO(YOLO_MODEL_PATH)
    return _shared_yolo


class FaceRecognitionEngine:
    def __init__(self, class_name):
        self.class_name = class_name
        self.model = get_shared_yolo_model()
        self.tracker = DeepSort(max_age=40)
        self.known_faces = []
        self.known_names = []
        self.faces_loaded = False
        self.track_identities = {}

    def clear_tracking_state(self):
        self.track_identities.clear()

    def load_known_faces(self, force_reload=False):
        if force_reload:
            self.faces_loaded = False
            self.clear_tracking_state()
        if self.faces_loaded:
            return
        self.known_faces, self.known_names = load_cached_faces(self.class_name, force_reload=force_reload)
        self.faces_loaded = True

    def reload_known_faces(self):
        self.load_known_faces(force_reload=True)

    def detect_and_recognize(self, frame):
        self.load_known_faces()
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return frame, [], [], []

        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.ndim == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        frame = np.ascontiguousarray(frame)

        results = self.model(frame, conf=0.4, classes=[0], verbose=False)
        detections = []
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            scores = result.boxes.conf.cpu().numpy()
            for box, score in zip(boxes, scores):
                x1, y1, x2, y2 = box
                w = x2 - x1
                h = y2 - y1
                if w > 0 and h > 0:
                    detections.append(([float(x1), float(y1), float(w), float(h)], float(score), "person"))

        tracks = self.tracker.update_tracks(detections, frame=frame)
        people = []
        frame_height, frame_width = frame.shape[:2]
        now_ts = time.time()

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            l, t, r, b = map(int, track.to_ltrb())
            l = max(0, min(l, frame_width))
            r = max(0, min(r, frame_width))
            t = max(0, min(t, frame_height))
            b = max(0, min(b, frame_height))

            cached_entry = self.track_identities.get(track_id)
            name = None

            if cached_entry and cached_entry.get("confirmed", 0) >= 3 and (now_ts - cached_entry.get("last_check", 0) < 6.0):
                name = cached_entry.get("name")
            else:
                if r > l and b > t:
                    head_h = max(30, int((b - t) * 0.45))
                    head_crop = frame[t:min(t + head_h, frame_height), l:r]
                    if head_crop.size > 0:
                        try:
                            rgb = cv2.cvtColor(head_crop, cv2.COLOR_BGR2RGB)
                            rgb = np.ascontiguousarray(rgb, dtype=np.uint8)
                            if rgb.ndim == 3 and rgb.shape[0] >= 20 and rgb.shape[1] >= 20:
                                encs = face_recognition.face_encodings(rgb)
                                if encs and len(self.known_faces) > 0:
                                    landmarks = face_recognition.face_landmarks(rgb)
                                    is_live = evaluate_liveness(landmarks[0]) if landmarks else True
                                    if is_live:
                                        dists = face_recognition.face_distance(self.known_faces, encs[0])
                                        idx = np.argmin(dists)
                                        if dists[idx] < 0.58:
                                            matched_name = self.known_names[idx]
                                            prev_count = cached_entry.get("confirmed", 0) if cached_entry else 0
                                            self.track_identities[track_id] = {
                                                "name": matched_name,
                                                "confirmed": prev_count + 1,
                                                "last_check": now_ts
                                            }
                                            name = matched_name
                        except Exception:
                            pass

            people.append((track_id, name, l, t, r, b))

            if name:
                label = name
                color = (0, 255, 0)
            else:
                label = "Unknown"
                color = (0, 255, 255)

            cv2.rectangle(frame, (l, t), (r, b), color, 2)
            cv2.putText(frame, label, (l, max(20, t - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        students = []
        teachers = []
        for _, n, _, _, _, _ in people:
            if not n:
                continue
            if n.startswith("teacher_"):
                teachers.append(n.replace("teacher_", ""))
            elif n.startswith("student_"):
                students.append(n.replace("student_", ""))

        return frame, students, teachers, people
