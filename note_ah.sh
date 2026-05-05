
lerobot-find-cameras opencv # or realsense for Intel Realsense cameras

sudo apt install v4l-utils
$ v4l2-ctl --list-devices
USB Camera: USB Camera (usb-0000:00:14.0-2.3):
	/dev/video0
	/dev/video1
	/dev/media0

USB Camera: USB Camera (usb-0000:00:14.0-2.4):
	/dev/video2
	/dev/video3
	/dev/media1


lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --display_data=true

lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, side: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=my_awesome_leader_arm \
    --display_data=true



lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=my_awesome_follower_arm \
    --robot.cameras="{ front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"}, side: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM2 \
    --teleop.id=my_awesome_leader_arm \
    --display_data=true







sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1


rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/test123
rm -rf /home/bob/datasets/test123
rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/test123B

export HF_HUB_OFFLINE=1
export HF_DATASETS_OFFLINE=1

#录制
lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_awesome_follower_arm \
  --robot.cameras='{
    front: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 30, fourcc: "MJPG"},
    side:  {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"}
  }' \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_awesome_leader_arm \
  --display_data=true \
  --dataset.repo_id=seeedstudio123/test123B \
  --dataset.num_episodes=5 \
  --dataset.single_task="Grab the black cube" \
  --dataset.push_to_hub=false \
  --dataset.episode_time_s=5 \
  --dataset.reset_time_s=5


##################################################
F. 串口权限：别再用 chmod 666，用 group 更稳

临时 chmod 666 /dev/ttyACM* 重启/拔插会丢。建议：

sudo usermod -aG dialout $USER
newgrp dialout


然后重新插拔机械臂，再跑。
###############################################

sudo chmod 666 /dev/ttyACM*
sudo chmod 666 /dev/ttyACM1

export HF_HUB_OFFLINE=1
export HF_DATASETS_OFFLINE=1

rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/test123
rm -rf /home/bob/datasets/test123
rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/test123B



clear


lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_awesome_follower_arm \
  --robot.cameras='{
    front: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"},
    side:  {type: opencv, index_or_path: 4, width: 640, height: 480, fps: 30, fourcc: "MJPG"}
  }' \
  --teleop.type=so101_leader \
  --teleop.port=/dev/ttyACM1 \
  --teleop.id=my_awesome_leader_arm \
  --display_data=true \
  --dataset.repo_id=seeedstudio123/test123D \
  --dataset.num_episodes=10 \
  --dataset.single_task="Grab the black cube" \
  --dataset.push_to_hub=false 



###################################
## 重播

lerobot-replay \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=my_awesome_follower_arm \
    --dataset.repo_id=seeedstudio123/test123D \
    --dataset.episode=9


###################################
## 训练

lerobot-train \
  --dataset.repo_id=seeedstudio123/test123D \
  --policy.type=act \
  --output_dir=outputs/train/act_so101_test \
  --job_name=act_so101_test \
  --policy.device=cuda \
  --wandb.enable=false \
  --policy.push_to_hub=false\
  --steps=10000 

###################################
## 评估
rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/eval_test123D*

lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_awesome_follower_arm \
  --robot.cameras='{
    front: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 30, fourcc: "MJPG"},
    side:  {type: opencv, index_or_path: 4, width: 640, height: 480, fps: 30, fourcc: "MJPG"}
  }' \
  --display_data=true \
  --dataset.repo_id=seeedstudio123/eval_test123D \
  --dataset.single_task="Grab the black cube" \
  --policy.push_to_hub=false\
  --policy.path=outputs/train/act_so101_test/checkpoints/last/pretrained_model



rm -rf /home/bob/.cache/huggingface/lerobot/seeedstudio123/eval_test123D*

lerobot-record \
  --robot.type=so101_follower \
  --robot.port=/dev/ttyACM0 \
  --robot.id=my_awesome_follower_arm \
  --robot.cameras='{
    front: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 20, fourcc: "MJPG"},
    side:  {type: opencv, index_or_path: 4, width: 640, height: 480, fps: 20, fourcc: "MJPG"}
  }' \
  --display_data=true \
  --dataset.repo_id=seeedstudio123/eval_test123D \
  --dataset.single_task="Grab the black cube" \
  --policy.push_to_hub=false\
  --policy.path=outputs/train/act_so101_test/checkpoints/last/pretrained_model


