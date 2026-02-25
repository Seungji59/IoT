# Smartpot-for-Singleperson-Households

**1인 가구를 위한 IoT 기반 스마트 화분 시스템**

ESP32 기반 식물 재배 디바이스와 Raspberry Pi 게이트웨이,
AWS 클라우드 및 Android 애플리케이션을 연동한
End-to-End IoT 시스템입니다.

- **KDT IoT 과정 1등(대상) 수상**
- Team project
<img width="893" height="501" alt="image" src="https://github.com/user-attachments/assets/4c7a1664-9381-4465-8f8b-55442bcdd9e9" />

- 동작 시연 동영상 : https://www.youtube.com/watch?v=KUTwimrqj4c&t=3s



##  System Overview

- 센서 데이터 수집 및 제어를 ESP32에서 수행
- MQTT 기반 비동기 통신으로 디바이스–클라우드 연동
- AWS(Node-RED, MySQL)에서 데이터 저장 및 제어 로직 관리
- Android 앱을 통해 식물 생장 단계 분석 결과 확인

---

## 🔹 System Architecture

본 프로젝트의 전체 시스템 아키텍처는
하드웨어 단 통신 구조와 소프트웨어/클라우드 처리 구조로 분리하여 설계하였습니다.
이를 통해 디바이스 제어와 데이터 처리를 역할별로 명확히 구분하였습니다.

---
### 🔸 Hardware & MQTT Architecture

ESP32 기반 디바이스에서 센서 데이터를 수집하고 제어 동작을 수행합니다.
수집된 센서 데이터 및 제어 명령은 MQTT 프로토콜을 통해
비동기 방식으로 전달됩니다.


<img width="1170" height="632" alt="Hardware & MQTT Architecture" src="https://github.com/user-attachments/assets/49ff1ee0-3fd4-4094-a954-ceebf7e8efdf" />

<p align="center"><em>ESP32 디바이스와 MQTT 기반 하드웨어 통신 구조</em></p>

---

### 🔸 Software Architecture

소프트웨어 아키텍처는 수집된 데이터를 처리 및 저장하고,
Android 애플리케이션과의 연동을 담당합니다.


<img width="1305" height="731" alt="Software Architecture" src="https://github.com/user-attachments/assets/3b229806-606b-4718-8d76-b5eda2cfa8c4" />

<p align="center"><em>AWS, Node-RED, MySQL 및 Android 애플리케이션 연동 구조</em></p>

---


## 🔹 Architecture Components

### ESP32
- 센서 데이터 수집
- 제어 동작 수행

### MQTT
- 센서 데이터 및 제어 명령을 위한 비동기 통신

### AWS (Docker 기반)
- **Node-RED**: 데이터 흐름 및 제어 로직 관리
- **MySQL**: 센서 및 제어 데이터 저장

### Flask
- 클라우드–애플리케이션 간 API 서버 역할 수행

### Android Application
- 식물 생장 단계 분류 결과 확인
- 이미지 업로드 및 분석 결과 수신
<img width="951" height="560" alt="image" src="https://github.com/user-attachments/assets/f37bdd78-72f8-4b1b-af72-5a09b8f89f82" />


---

## 🔹 Reference & Attribution

본 프로젝트는 PyTorch 팀에서 제공하는 Android Object Detection 데모를 참고하였습니다.

- https://github.com/pytorch/android-demo-app/tree/master/ObjectDetection

해당 레포지토리는 BSD 3-Clause License를 따르며,
Android 환경에서의 객체 탐지 워크플로우를 이해하기 위한 참고 자료로 활용되었습니다.

본 프로젝트의 전체 시스템 아키텍처 설계, IoT 네트워크 구성,
센서 연동, MQTT 통신 및 전체 구현은
본 프로젝트 팀에서 독립적으로 설계 및 구현하였습니다.
