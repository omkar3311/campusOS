import math


def calculate_ear(eye_points):
    if len(eye_points) < 6:
        return 0.3
    p1 = eye_points[0]
    p2 = eye_points[1]
    p3 = eye_points[2]
    p4 = eye_points[3]
    p5 = eye_points[4]
    p6 = eye_points[5]

    def dist(a, b):
        return math.hypot(a[0] - b[0], a[1] - b[1])

    ear = (dist(p2, p6) + dist(p3, p5)) / (2.0 * max(dist(p1, p4), 1e-6))
    return ear


def evaluate_liveness(landmarks):
    if not landmarks:
        return True
    left_eye = landmarks.get("left_eye")
    right_eye = landmarks.get("right_eye")
    if not left_eye or not right_eye:
        return True
    left_ear = calculate_ear(left_eye)
    right_ear = calculate_ear(right_eye)
    avg_ear = (left_ear + right_ear) / 2.0
    return 0.12 <= avg_ear <= 0.45
