import cv2
import mediapipe as mp
import numpy as np

mp_face_mesh=mp.solutions.face_mesh

class DrowsinessDetector:
    def __init__(self):
        # All your landmark indices
        self.LEFT_EYE     = [362, 385, 387, 263, 373, 380]
        self.RIGHT_EYE    = [33,  160, 158, 133, 153, 144]
        self.MOUTH_TOP    = 13
        self.MOUTH_BOTTOM = 14
        self.MOUTH_LEFT   = 78
        self.MOUTH_RIGHT  = 308
        self.NOSE_TIP     = 1
        self.LEFT_EAR     = 234
        self.RIGHT_EAR    = 454

        # Thresholds
        self.EAR_THRESHOLD  = 0.28
        self.MAR_THRESHOLD  = 0.4
        self.HEAD_THRESHOLD = 30


        # Frame limits
        self.DROWSY_LIMIT   = 30
        self.YAWN_LIMIT     = 20
        self.DISTRACT_LIMIT = 90

        # Counters
        self.drowsy_counter   = 0
        self.yawn_counter     = 0
        self.distract_counter = 0


        # Cooldowns
        self.drowsy_cooldown   = False
        self.yawn_cooldown     = False
        self.distract_cooldown = False

        self.safety_score = 100

        # MediaPipe
        self.face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces            = 1,
            min_detection_confidence = 0.5,
            min_tracking_confidence  = 0.5
        )


    def distance(self,p1,p2):
        return np.linalg.norm(np.array(p1) - np.array(p2))


    def calculate_ear(self,landmarks,eye_pts,w,h):
        pts = [(int(landmarks[i].x * w),
                int(landmarks[i].y * h)) for i in eye_pts]
        A = self.distance(pts[1], pts[5])
        B = self.distance(pts[2], pts[4])
        C = self.distance(pts[0], pts[3])
        return round((A + B) / (2.0 * C), 3)

    def calculate_mar(self, landmarks, w, h):
        top    = (int(landmarks[self.MOUTH_TOP].x    * w),
                  int(landmarks[self.MOUTH_TOP].y    * h))
        bottom = (int(landmarks[self.MOUTH_BOTTOM].x * w),
                  int(landmarks[self.MOUTH_BOTTOM].y * h))
        left   = (int(landmarks[self.MOUTH_LEFT].x   * w),
                  int(landmarks[self.MOUTH_LEFT].y   * h))
        right  = (int(landmarks[self.MOUTH_RIGHT].x  * w),
                  int(landmarks[self.MOUTH_RIGHT].y  * h))
        return round(self.distance(top, bottom) / self.distance(left, right), 3)


    def calculate_head_angle(self, landmarks, w, h):
        nose  = np.array([landmarks[self.NOSE_TIP].x  * w,
                          landmarks[self.NOSE_TIP].y  * h])
        l_ear = np.array([landmarks[self.LEFT_EAR].x  * w,
                          landmarks[self.LEFT_EAR].y  * h])
        r_ear = np.array([landmarks[self.RIGHT_EAR].x * w,
                          landmarks[self.RIGHT_EAR].y * h])
        mid   = (l_ear + r_ear) / 2
        vec   = nose - mid
        return abs(round(np.degrees(np.arctan2(vec[0], vec[1])), 1))

    def get_risk(self):
        if self.safety_score >= 70:   return "Safe"
        elif self.safety_score >= 40: return "Warning"
        else:                         return "Danger"


    def reset(self):
        # Reset everything for a new session
        self.drowsy_counter    = 0
        self.yawn_counter      = 0
        self.distract_counter  = 0
        self.drowsy_cooldown   = False
        self.yawn_cooldown     = False
        self.distract_cooldown = False
        self.safety_score      = 100

    def process(self, frame):
        h, w    = frame.shape[:2]
        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)

        # Default state when no face detected
        state = {
            "face_detected": False,
            "ear":           0,
            "mar":           0,
            "angle":         0,
            "drowsy":        False,
            "yawning":       False,
            "distracted":    False,
            "safety_score":  self.safety_score,
            "risk":          self.get_risk(),
            "alert":         None
        }

        if not results.multi_face_landmarks:
            return state

        landmarks = results.multi_face_landmarks[0].landmark
        state["face_detected"] = True

        # Calculate
        left_ear  = self.calculate_ear(landmarks, self.LEFT_EYE,  w, h)
        right_ear = self.calculate_ear(landmarks, self.RIGHT_EYE, w, h)
        avg_ear   = round((left_ear + right_ear) / 2, 3)
        mar       = self.calculate_mar(landmarks, w, h)
        angle     = self.calculate_head_angle(landmarks, w, h)

        state["ear"]   = avg_ear
        state["mar"]   = mar
        state["angle"] = angle

        # Drowsiness check
        if avg_ear < self.EAR_THRESHOLD:
            self.drowsy_counter += 1
            if self.drowsy_counter >= self.DROWSY_LIMIT and not self.drowsy_cooldown:
                state["drowsy"]      = True
                state["alert"]       = "DROWSY DETECTED"
                self.safety_score    = max(0, self.safety_score - 10)
                self.drowsy_cooldown = True
                self.drowsy_counter  = 0
        else:
            self.drowsy_counter  = 0
            self.drowsy_cooldown = False

        # Yawning check
        if mar > self.MAR_THRESHOLD:
            self.yawn_counter += 1
            if self.yawn_counter >= self.YAWN_LIMIT and not self.yawn_cooldown:
                state["yawning"]    = True
                state["alert"]      = state["alert"] or "YAWNING DETECTED"
                self.safety_score   = max(0, self.safety_score - 5)
                self.yawn_cooldown  = True
                self.yawn_counter   = 0
        else:
            self.yawn_counter  = 0
            self.yawn_cooldown = False

        # Distraction check
        if angle > self.HEAD_THRESHOLD:
            self.distract_counter += 1
            if self.distract_counter >= self.DISTRACT_LIMIT and not self.distract_cooldown:
                state["distracted"]    = True
                state["alert"]         = state["alert"] or "DISTRACTED"
                self.safety_score      = max(0, self.safety_score - 7)
                self.distract_cooldown = True
                self.distract_counter  = 0
        else:
            self.distract_counter  = 0
            self.distract_cooldown = False

        state["safety_score"] = self.safety_score
        state["risk"]         = self.get_risk()
        return state



    
