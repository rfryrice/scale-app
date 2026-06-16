import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import cv2
import numpy as np
from picamera2 import Picamera2


FRAME_WIDTH = 640
FRAME_HEIGHT = 480
MIN_CONTOUR_AREA = 120
BINARY_THRESHOLD = 30
MORPH_KERNEL_SIZE = 5
MAX_MATCH_DISTANCE = 60.0
DEAD_ZONE_PX = 15
LOG_FILENAME = "vision_crossings.csv"


@dataclass
class Track:
    track_id: int
    centroid: Tuple[int, int]
    zone: str
    missed_frames: int = 0


def classify_zone(x_value: int, gate_x: int, dead_zone_px: int) -> str:
    if x_value < gate_x - dead_zone_px:
        return "left"
    if x_value > gate_x + dead_zone_px:
        return "right"
    return "dead"


def detect_centroids(
    gray_frame: np.ndarray,
    static_background: np.ndarray,
    threshold_value: int,
    min_area: int,
    kernel: np.ndarray,
) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
    diff = cv2.absdiff(gray_frame, static_background)
    _, binary = cv2.threshold(diff, threshold_value, 255, cv2.THRESH_BINARY)

    cleaned = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    centroids: List[Tuple[int, int]] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        moments = cv2.moments(contour)
        if moments["m00"] == 0:
            continue

        c_x = int(moments["m10"] / moments["m00"])
        c_y = int(moments["m01"] / moments["m00"])
        centroids.append((c_x, c_y))

    return cleaned, centroids


def match_tracks(
    tracks: Dict[int, Track],
    detections: List[Tuple[int, int]],
    max_distance: float,
) -> Tuple[Dict[int, Track], List[Tuple[int, int]], Dict[int, int]]:
    if not tracks:
        return {}, detections.copy(), {}

    unmatched_track_ids = set(tracks.keys())
    unmatched_det_indices = set(range(len(detections)))
    matched_pairs: List[Tuple[int, int, float]] = []

    for track_id, track in tracks.items():
        tx, ty = track.centroid
        for det_index, (dx, dy) in enumerate(detections):
            distance = float(np.hypot(dx - tx, dy - ty))
            if distance <= max_distance:
                matched_pairs.append((track_id, det_index, distance))

    matched_pairs.sort(key=lambda item: item[2])

    track_to_detection: Dict[int, int] = {}
    for track_id, det_index, _ in matched_pairs:
        if track_id in unmatched_track_ids and det_index in unmatched_det_indices:
            track_to_detection[track_id] = det_index
            unmatched_track_ids.remove(track_id)
            unmatched_det_indices.remove(det_index)

    new_tracks: Dict[int, Track] = {}
    for track_id, det_index in track_to_detection.items():
        prior = tracks[track_id]
        new_tracks[track_id] = Track(
            track_id=track_id,
            centroid=detections[det_index],
            zone=prior.zone,
            missed_frames=0,
        )

    return new_tracks, [detections[i] for i in unmatched_det_indices], track_to_detection


def main() -> None:
    picam2 = Picamera2()
    picam2.preview_configuration.main.size = (FRAME_WIDTH, FRAME_HEIGHT)
    picam2.preview_configuration.main.format = "RGB888"
    picam2.preview_configuration.align()
    picam2.configure("preview")
    picam2.start()

    gate_x = FRAME_WIDTH // 2
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE)
    )

    # Build a static background from the first grayscale frame.
    initial_frame = picam2.capture_array()
    static_background = cv2.cvtColor(initial_frame, cv2.COLOR_RGB2GRAY)

    tracks: Dict[int, Track] = {}
    next_track_id = 1

    crossing_left_to_right = 0
    crossing_right_to_left = 0

    csv_path = os.path.join(os.path.dirname(__file__), LOG_FILENAME)
    csv_exists = os.path.exists(csv_path)

    with open(csv_path, "a", newline="") as csv_file:
        writer = csv.writer(csv_file)
        if not csv_exists:
            writer.writerow(["timestamp", "track_id", "direction", "x", "y"])

        while True:
            frame_rgb = picam2.capture_array()
            gray = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2GRAY)

            motion_mask, centroids = detect_centroids(
                gray,
                static_background,
                BINARY_THRESHOLD,
                MIN_CONTOUR_AREA,
                kernel,
            )

            matched_tracks, unmatched_detections, track_to_detection = match_tracks(
                tracks,
                centroids,
                MAX_MATCH_DISTANCE,
            )

            # Update matched tracks and check for gate crossings.
            for track_id, det_index in track_to_detection.items():
                centroid = centroids[det_index]
                current_zone = classify_zone(centroid[0], gate_x, DEAD_ZONE_PX)

                prior_zone = tracks[track_id].zone
                if prior_zone == "left" and current_zone == "right":
                    crossing_left_to_right += 1
                    writer.writerow(
                        [
                            datetime.now().isoformat(timespec="seconds"),
                            track_id,
                            "L->R",
                            centroid[0],
                            centroid[1],
                        ]
                    )
                    csv_file.flush()
                elif prior_zone == "right" and current_zone == "left":
                    crossing_right_to_left += 1
                    writer.writerow(
                        [
                            datetime.now().isoformat(timespec="seconds"),
                            track_id,
                            "R->L",
                            centroid[0],
                            centroid[1],
                        ]
                    )
                    csv_file.flush()

                # Preserve last meaningful side while inside dead zone.
                if current_zone in {"left", "right"}:
                    matched_tracks[track_id].zone = current_zone
                else:
                    matched_tracks[track_id].zone = prior_zone

            # Start new tracks for unmatched detections.
            for centroid in unmatched_detections:
                zone = classify_zone(centroid[0], gate_x, DEAD_ZONE_PX)
                if zone == "dead":
                    # Initialize as left or right by nearest side to avoid ambiguous starts.
                    zone = "left" if centroid[0] < gate_x else "right"

                matched_tracks[next_track_id] = Track(
                    track_id=next_track_id,
                    centroid=centroid,
                    zone=zone,
                    missed_frames=0,
                )
                next_track_id += 1

            tracks = matched_tracks

            # Visualization
            display = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            cv2.line(display, (gate_x, 0), (gate_x, FRAME_HEIGHT), (0, 255, 255), 2)
            cv2.line(
                display,
                (gate_x - DEAD_ZONE_PX, 0),
                (gate_x - DEAD_ZONE_PX, FRAME_HEIGHT),
                (255, 255, 0),
                1,
            )
            cv2.line(
                display,
                (gate_x + DEAD_ZONE_PX, 0),
                (gate_x + DEAD_ZONE_PX, FRAME_HEIGHT),
                (255, 255, 0),
                1,
            )

            for track in tracks.values():
                c_x, c_y = track.centroid
                cv2.circle(display, (c_x, c_y), 4, (0, 255, 0), -1)
                cv2.putText(
                    display,
                    f"ID {track.track_id}",
                    (c_x + 6, c_y - 6),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

            cv2.putText(
                display,
                f"L->R: {crossing_left_to_right}",
                (10, 24),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.putText(
                display,
                f"R->L: {crossing_right_to_left}",
                (10, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow("Cricket Crossing Tracker", display)
            cv2.imshow("Motion Mask", motion_mask)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
