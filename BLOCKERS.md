# Blockers

- **GitHub CLI:** unavailable in the execution environment; publishing used the GitHub connector.
- **Direct container network access:** unavailable; external datasets could not be downloaded.
- **ROS2:** no ROS2 installation or middleware runtime was available. Status: Pending ROS2 Validation.
- **Hardware:** no robots or physical sensors were connected. Status: Pending Hardware Validation.
- **External datasets:** none were available in the repository or execution session. Status: Pending Dataset Validation.
- **Docker daemon:** no validated daemon execution was available during the implementation run. The Dockerfile is supplied but not claimed as locally validated.
- **Binary artifact publication:** GIF and MP4 were generated locally from real synthetic runs, but the text-only GitHub connector could not upload binary files. The generation pipeline is committed and CI/local users can reproduce them.
