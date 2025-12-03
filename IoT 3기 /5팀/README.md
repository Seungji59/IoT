# TIBO - Robo-Camera Management App

[![React Native](https://img.shields.io/badge/React%20Native-0.79.5-blue.svg)](https://reactnative.dev/)
[![Expo](https://img.shields.io/badge/Expo-53.0.20-blue.svg)](https://expo.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8.3-blue.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

TIBO는 React Native와 Expo를 기반으로 한 **로봇 카메라 관리 앱**입니다. 실시간 스트리밍, PTZ 제어, 녹화 관리, 사용자 인증 등을 제공하는 모던한 모바일 애플리케이션입니다.

## 📋 Table of Contents

- [🚀 기술 스택](#-기술-스택)
- [📁 프로젝트 구조](#-프로젝트-구조)
- [🔧 주요 기능](#-주요-기능)
- [🛠 설치 및 실행](#-설치-및-실행)
- [📱 앱 화면](#-앱-화면)
- [🔧 개발 환경](#-개발-환경)
- [🧪 테스트](#-테스트)
- [📝 변경 이력](#-변경-이력)
- [❓ FAQ & Troubleshooting](#-faq--troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 라이선스](#-라이선스)

## 🚀 기술 스택

### **Core Framework**
- **React Native** (v0.79.5) - 크로스 플랫폼 모바일 개발
- **Expo** (v53.0.20) - 개발 환경 및 빌드 도구
- **TypeScript** (v5.8.3) - 타입 안전 개발

### **Navigation & UI**
- **React Navigation** (v7.1.16) - 네비게이션 관리
- **React Native Reanimated** (v3.17.4) - 애니메이션
- **React Native Gesture Handler** (v2.24.0) - 제스처 처리
- **Styled Components** (v6.1.19) - 스타일링

### **State Management**
- **Redux Toolkit** (v2.5.1) - 상태 관리
- **Redux Persist** (v6.0.0) - 상태 영속화
- **Zustand** (v5.0.6) - 경량 상태 관리
- **React Query** (v5.83.0) - 서버 상태 관리

### **Authentication & Security**
- **Expo Auth Session** (v6.2.1) - OAuth 인증
- **Expo Secure Store** (v14.2.3) - 보안 저장소
- **Expo Local Authentication** (v16.0.5) - 생체 인증
- **React Native Encrypted Storage** (v4.0.3) - 암호화 저장소

### **Media & Communication**
- **Expo AV** (v15.1.7) - 오디오/비디오 재생
- **Expo Camera** (v16.1.11) - 카메라 접근
- **React Native Video** (v5.2.2) - 비디오 플레이어
- **React Native WebRTC** (v1.106.1) - 실시간 통신

### **Development Tools**
- **ESLint** (v9.31.0) - 코드 린팅
- **Prettier** (v3.6.2) - 코드 포맷팅
- **MSW** (v2.10.4) - API 모킹

## 📁 프로젝트 구조

```
frontend/
├── app.config.js              # Expo 앱 설정 (195 lines)
├── app.json                   # 앱 메타데이터
├── index.js                   # 앱 진입점
├── package.json               # 의존성 관리
├── tsconfig.json              # TypeScript 설정
├── src/
│   ├── App.tsx               # 메인 앱 컴포넌트 (120 lines)
│   ├── assets/               # 이미지 및 리소스
│   ├── components/           # UI 컴포넌트
│   │   ├── atoms/           # 기본 컴포넌트 (30개)
│   │   │   ├── Button.tsx (270 lines)
│   │   │   ├── Joystick.tsx (190 lines)
│   │   │   ├── VideoPlayer.tsx (262 lines)
│   │   │   ├── AnimatedProgressBar.tsx (111 lines)
│   │   │   └── ...          # 기타 25개 컴포넌트
│   │   ├── layout/          # 레이아웃 컴포넌트
│   │   ├── molecules/       # 분자 컴포넌트
│   │   └── organisms/       # 유기체 컴포넌트
│   ├── config/              # 설정 파일
│   │   └── api.ts          # API 설정 (31 lines)
│   ├── contexts/            # React Context
│   ├── hooks/               # 커스텀 훅
│   ├── mocks/               # 목 데이터
│   ├── navigation/          # 네비게이션
│   │   └── AppNavigator.tsx (316 lines)
│   ├── pages/               # 화면 컴포넌트 (8개)
│   │   ├── HomeScreen.tsx (947 lines)
│   │   ├── LiveScreen.tsx (790 lines)
│   │   ├── RecordingsScreen.tsx (1186 lines)
│   │   ├── SettingsScreen.tsx (829 lines)
│   │   ├── LoginScreen.tsx (542 lines)
│   │   ├── SignupScreen.tsx (1839 lines)
│   │   ├── AppLockScreen.tsx (601 lines)
│   │   └── IntroScreen.tsx (272 lines)
│   ├── screens/             # 추가 화면
│   ├── services/            # API 서비스 (9개)
│   │   ├── AuthService.ts (152 lines)
│   │   ├── GoogleAuthService.ts (392 lines)
│   │   ├── LiveStreamService.ts (163 lines)
│   │   ├── CameraService.ts (294 lines)
│   │   ├── EventService.ts (338 lines)
│   │   ├── UserDataService.ts (400 lines)
│   │   ├── SecureStorageService.ts (271 lines)
│   │   ├── ConnectionService.ts (205 lines)
│   │   └── QuietTimeService.ts (144 lines)
│   ├── store/               # Redux 스토어
│   │   └── index.ts (58 lines)
│   ├── styles/              # 테마 및 스타일
│   ├── types/               # TypeScript 타입 (325 lines)
│   └── utils/               # 유틸리티 함수
└── shared/                  # 공유 타입
```

## 🔧 주요 기능

### **1. 사용자 인증 시스템**
- **회원가입**: 이메일, 휴대폰 번호, 약관 동의 (3단계 프로세스)
- **휴대폰 인증**: SMS 인증번호 발송/확인
- **로그인**: 이메일/비밀번호 로그인
- **소셜 로그인**: Google OAuth 지원
- **아이디/비밀번호 찾기**: 휴대폰/이메일 기반 복구
- **앱 잠금**: 생체 인증 기반 앱 보안

### **2. 실시간 스트리밍**
- **라이브 스트림**: WebRTC 기반 실시간 비디오
- **PTZ 제어**: 팬/틸트/줌 제어
- **조이스틱 제어**: 직관적인 카메라 이동
- **화질 조정**: Low/Medium/High 품질 설정
- **상태 동기화**: 모든 화면 간 실시간 상태 공유

### **3. 녹화 관리**
- **녹화 시작/중지**: 원클릭 녹화 제어
- **녹화 목록**: 날짜별, 타입별 필터링
- **비디오 플레이어**: 내장 비디오 재생
- **다운로드/공유**: 녹화 파일 다운로드 및 공유
- **카테고리 분류**: 위험/경계/움직임/수동 녹화

### **4. 설정 관리**
- **사용자 프로필**: 닉네임, 비밀번호 변경
- **알림 설정**: 푸시 알림, 무음 시간 설정
- **화질 설정**: 녹화/스트림 품질 조정
- **데이터 보관**: 보관 기간 설정
- **네트워크 설정**: WiFi/모바일 데이터 설정

### **5. 보안 기능**
- **앱 잠금**: 생체 인증 기반 앱 보안
- **암호화 저장소**: 민감 정보 암호화 저장
- **자동 로그아웃**: 설정 기반 자동 로그아웃
- **토큰 관리**: JWT 토큰 자동 갱신

## 🛠 설치 및 실행

### **1. 의존성 설치**
```bash
# 저장소 클론
git clone <repository-url>
cd frontend

# 의존성 설치
npm install

# Expo CLI 설치 (전역)
npm install -g @expo/cli
```

### **2. 환경 설정**
```bash
# .env 파일 생성 (필요시)
touch .env
```

환경 변수 예시:
```env
EXPO_PUBLIC_API_URL=http://localhost:3000/api
EXPO_PUBLIC_WEBSOCKET_URL=ws://localhost:3000
EXPO_PUBLIC_TURN_SERVER=stun:localhost:3478
```

### **3. 개발 서버 실행**
```bash
# 개발 서버 시작
npm start

# iOS 시뮬레이터에서 실행
npm run ios

# Android 에뮬레이터에서 실행
npm run android

# 웹에서 실행
npm run web
```

### **4. 빌드 및 배포**
```bash
# iOS 빌드
npm run build:ios

# Android 빌드
npm run build:android

# 앱스토어 제출
npm run submit:ios
npm run submit:android
```

## 📱 앱 화면

### **🏠 홈 화면 (HomeScreen)**
- **로봇 상태 모니터링**: 온라인/오프라인, 이동 중 상태
- **실시간 비디오 피드**: 16:9 비율의 라이브 스트림
- **시스템 상태**: 배터리, WiFi 신호 강도
- **이벤트 목록**: 최근 모션 감지, 녹화 이벤트
- **상태 인디케이터**: LIVE, REC, MIC 실시간 표시

### **🎥 라이브 화면 (LiveScreen)**
- **고화질 스트림**: HD 1080p 실시간 비디오
- **로봇 이동 제어**: 조이스틱을 통한 방향 제어
- **액션 버튼**: 녹화, 캡처, 줌인/아웃, 음성 제어
- **이동모드 토글**: ON/OFF 스위치로 이동 제어
- **상태 동기화**: HomeScreen과 실시간 상태 공유

### **📋 녹화 기록 화면 (RecordingsScreen)**
- **모니터링 특화 카테고리**:
  - ⚠️ **위험**: 위험 구역 접근 감지
  - 🚫 **경계**: 안전 경계 이탈 감지
  - 👤 **움직임**: 비정상 움직임 감지
  - 📹 **수동**: 사용자 직접 녹화
- **심각도 시스템**: High/Medium/Low 우선순위
- **날짜별 필터링**: 특정 날짜의 모니터링 활동 조회
- **비디오 플레이어**: 내장 비디오 재생 및 다운로드

### **⚙️ 설정 화면 (SettingsScreen)**
- **내 정보**: 프로필, 구독 정보, 2단계 인증
- **알림 및 감지**: 푸시 알림, 움직임 감지, 무음 시간
- **녹화 및 저장**: 자동 녹화, 화질 설정, 데이터 보관
- **환경설정**: 네트워크 설정, 앱 잠금
- **지원**: 고객 지원, 앱 정보
- **계정 관리**: 로그아웃, Google 계정 연동

### **🔐 인증 화면들**
- **로그인 화면 (LoginScreen)**: 이메일/비밀번호, Google 로그인
- **회원가입 화면 (SignupScreen)**: 3단계 회원가입 프로세스
- **앱 잠금 화면 (AppLockScreen)**: 생체 인증 기반 보안
- **인트로 화면 (IntroScreen)**: 앱 소개 및 시작

## 🔧 개발 환경

### **필수 요구사항**
- Node.js 16+
- npm 또는 yarn
- Expo CLI
- iOS Simulator 또는 Android Emulator
- Xcode (iOS 개발용)
- Android Studio (Android 개발용)

### **개발 도구**
- **VS Code** - 권장 IDE
- **React Native Debugger** - 디버깅 도구
- **Flipper** - 네트워크 및 상태 디버깅

### **성능 최적화**
- **Hermes 엔진**: JavaScript 성능 최적화
- **Bundle Splitting**: 코드 분할로 로딩 속도 개선
- **Image Optimization**: 이미지 압축 및 최적화
- **Tree Shaking**: 사용하지 않는 코드 제거

## 🧪 테스트

### **단위 테스트**
```bash
# 현재 테스트 스크립트 없음
# 향후 Jest 도입 예정
```

### **API 테스트**
```bash
# MSW를 통한 API 모킹
# src/mocks/ 디렉터리의 모킹 데이터 사용
```

### **수동 테스트**
```bash
# 개발 모드에서 실시간 테스트
npm start

# 다양한 디바이스에서 테스트
# iOS Simulator, Android Emulator, 실제 디바이스
```

## 📝 변경 이력

### **v1.0.0 (2025-01-27)**
- ✅ 기본 앱 구조 구현
- ✅ 사용자 인증 시스템 (로그인/회원가입)
- ✅ Google OAuth 로그인 지원
- ✅ 실시간 스트리밍 시스템
- ✅ PTZ 제어 및 조이스틱 기능
- ✅ 녹화 관리 시스템
- ✅ 설정 화면 및 앱 잠금 기능
- ✅ 애니메이션 및 UI/UX 개선

### **주요 구현 기능**
1. **인증 시스템**: 휴대폰 인증, Google OAuth, 앱 잠금
2. **실시간 스트리밍**: WebRTC 기반 라이브 비디오
3. **PTZ 제어**: 조이스틱을 통한 카메라 제어
4. **녹화 관리**: 다운로드, 공유, 필터링 기능
5. **설정 관리**: 사용자 프로필, 알림, 보안 설정

## ❓ FAQ & Troubleshooting

### **Q: Expo 개발 서버가 시작되지 않습니다**
A: 다음을 확인해주세요:
- Node.js 버전이 16+인지 확인
- Expo CLI가 전역 설치되어 있는지 확인
- 포트 8081이 사용 가능한지 확인
- 방화벽 설정 확인

### **Q: iOS 시뮬레이터에서 실행되지 않습니다**
A: 다음을 확인해주세요:
- Xcode가 설치되어 있는지 확인
- iOS Simulator가 설치되어 있는지 확인
- `npm run ios` 명령어 사용
- Xcode에서 시뮬레이터를 먼저 실행

### **Q: Android 에뮬레이터에서 실행되지 않습니다**
A: 다음을 확인해주세요:
- Android Studio가 설치되어 있는지 확인
- Android SDK가 설정되어 있는지 확인
- 에뮬레이터가 실행 중인지 확인
- `npm run android` 명령어 사용

### **Q: API 연결이 되지 않습니다**
A: 다음을 확인해주세요:
- 백엔드 서버가 실행 중인지 확인
- `src/config/api.ts`의 API_BASE_URL 설정 확인
- 네트워크 연결 상태 확인
- CORS 설정 확인

### **Q: 빌드 오류가 발생합니다**
A: 다음을 확인해주세요:
- 모든 의존성이 설치되어 있는지 확인
- `npm install` 재실행
- 캐시 클리어: `npx expo start --clear`
- Metro 캐시 클리어: `npx expo start --reset-cache`

## 🤝 Contributing

### **개발 환경 설정**
1. 프로젝트 클론
2. 의존성 설치: `npm install`
3. 환경 변수 설정
4. 개발 서버 실행: `npm start`

### **코드 스타일**
- TypeScript 사용 필수
- ESLint 규칙 준수
- Prettier 자동 포맷팅
- 컴포넌트별 파일 분리

### **커밋 메시지 규칙**
- `FEAT`: 새로운 기능 추가
- `FIX`: 버그 수정
- `REFACTOR`: 코드 리팩토링
- `DOCS`: 문서 수정
- `TEST`: 테스트 코드 추가

### **PR 가이드라인**
1. 기능 브랜치 생성
2. 코드 작성 및 테스트
3. ESLint/Prettier 검사 통과
4. PR 생성 및 리뷰 요청

## 📄 라이선스

이 프로젝트는 [MIT 라이선스](LICENSE) 하에 배포됩니다.

---

**TIBO** - TIBO Robo-Camera Management App 📱🎥🤖

