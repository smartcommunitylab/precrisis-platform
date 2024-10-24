#!/usr/bin/env python3

import argparse
import json
import os
import time

import cv2
from busca.precrisis_tracker import Tracker
from loguru import logger
from yolox.utils.visualize import plot_tracking

IMAGE_EXT = [".jpg", ".jpeg", ".webp", ".bmp", ".png"]


def make_parser():
    parser = argparse.ArgumentParser("BUSCA demo!")
    parser.add_argument(
        "--source",
        default="file",
        help="input type, eg. file or webcam",
        choices=["file", "webcam"],
    )

    parser.add_argument(
        "--path", default="./videos/palace.mp4", help="path to images or video"
    )
    parser.add_argument("--camid", type=int, default=0, help="webcam demo camera id")

    parser.add_argument(
        "--device",
        default="gpu",
        type=str,
        help="device to run our model, can either be cpu or gpu",
        choices=["cpu", "gpu"],
    )
    parser.add_argument(
        "--fp16",
        dest="fp16",
        default=False,
        action="store_true",
        help="Adopting mix precision evaluating.",
    )
    parser.add_argument(
        "--fuse",
        dest="fuse",
        default=False,
        action="store_true",
        help="Fuse conv and bn for testing.",
    )
    parser.add_argument(
        "--disable-busca",
        dest="disable_busca",
        default=False,
        action="store_true",
        help="Disable BUSCA module",
    )
    return parser


def main(args):
    tracker = Tracker(
        fuse=args.fuse,
        device=args.device,
        fp16=args.fp16,
        use_busca=not args.disable_busca,
    )

    data_influx = []
    cap = cv2.VideoCapture(args.path if args.source == "file" else args.camid)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)  # float
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  # float
    fps = cap.get(cv2.CAP_PROP_FPS)

    current_time = time.localtime()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S", current_time)
    save_folder = os.path.join("BUSCA_OUTPUT", "")
    os.makedirs(save_folder, exist_ok=True)
    if args.source == "file":
        save_path = os.path.join(save_folder, args.path.split("/")[-1])
    else:
        save_path = os.path.join(save_folder, "camera.mp4")
    logger.info(f"Video will be saved in {save_path}")
    vid_writer = cv2.VideoWriter(
        save_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (int(width), int(height))
    )

    frame_id = 0
    results = []
    while True:
        # logger.info('Processing frame {}'.format(frame_id))
        ret_val, frame = cap.read()

        if ret_val:
            outputs = tracker.track(frame)

            try:

                total = len(outputs)

                if total != 0:
                    avg_speed = sum([out["speed"] for out in outputs]) / total
                    high_speed = max([out["speed"] for out in outputs])
                    min_speed = min([out["speed"] for out in outputs])
                    high_age = max([out["age"] for out in outputs])
                    min_age = min(out["age"] for out in outputs)
                    avg_age = sum([out["age"] for out in outputs]) / total
                    objects_aspect = len(
                        [
                            out["aspect_ratio"]
                            for out in outputs
                            if out["aspect_ratio"] > 1
                        ]
                    )
                else:
                    avg_speed = 0
                    high_speed = 0
                    min_speed = 0
                    high_age = 0
                    min_age = 0
                    avg_age = 0
                    objects_aspect = 0

                base = {
                    "measurement": "object_tracker",
                    "tags": {
                        "city": "Vienna",
                        "camera": args.path.split("/")[-1],
                        "location": "MOT-04",
                    },
                    "fields": {
                        "city": "Vienna",
                        "camera": args.path.split("/")[-1],
                        "location": "MOT-04",
                        "number_objects": total,
                        "avg_speed": avg_speed,
                        "highest_speed": high_speed,
                        "min_speed": min_speed,
                        "objects_aspect": objects_aspect,
                        "avg_age": avg_age,
                        "high_age": high_age,
                        "min_age": min_age,
                    },
                }
                data_influx.append(base)
            except Exception as e:
                print(e)

            # We draw on top of the frame
            online_tlhw = []
            online_ids = []
            for track in outputs:
                track_tlhw = [track["t"], track["l"], track["h"], track["w"]]
                track_id = track["id"]
                online_tlhw.append(track_tlhw)
                online_ids.append(track_id)

            online_im = plot_tracking(
                frame, online_tlhw, online_ids, frame_id=frame_id + 1, fps=fps
            )
            vid_writer.write(online_im)

            ch = cv2.waitKey(1)
            if ch == 27 or ch == ord("q") or ch == ord("Q"):
                break
        else:
            break

        frame_id += 1

    logger.info(f"Done! Video saved in {save_path}")
    tracker.reset()

    cap.release()
    vid_writer.release()

    # Closes all the frames
    cv2.destroyAllWindows()

    # save json
    with open(save_path + ".json", "w") as f:
        json.dump(data_influx, f)


if __name__ == "__main__":
    args = make_parser().parse_args()

    main(args)
