# Google OAuth 크로스플랫폼 설정 가이드

## 📍 1단계: Google Cloud Console 설정

### 1.1 프로젝트 생성
1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. **API 및 서비스** > **사용자 인증 정보**로 이동

### 1.2 OAuth 동의 화면 설정
1. **OAuth 동의 화면** 탭으로 이동
2. **사용자 유형**: "외부" 선택
3. **앱 정보** 입력:
   - 앱 이름: "K-Digital"
   - 사용자 지원 이메일: your-email@gmail.com
   - 개발자 연락처 정보: your-email@gmail.com

### 1.3 플랫폼별 OAuth 2.0 클라이언트 ID 생성

#### 🔵 Web Application (웹용)
1. **사용자 인증 정보 만들기** > **OAuth 2.0 클라이언트 ID**
2. **애플리케이션 유형**: "웹 애플리케이션" 선택
3. **이름**: "K-Digital Web Client"
4. **승인된 리디렉션 URI** 추가:
   ```
   http://localhost:19000/--/auth/google/callback
   https://your-domain.com/auth/google/callback
   ```

#### 🟢 Android Application (안드로이드용)
1. **사용자 인증 정보 만들기** > **OAuth 2.0 클라이언트 ID**
2. **애플리케이션 유형**: "Android" 선택
3. **이름**: "K-Digital Android Client"
4. **패키지 이름**: `tuk.kdigital.login`
5. **SHA-1 인증서 지문**: 개발용/프로덕션용 각각 추가

#### 🟠 iOS Application (iOS용)
1. **사용자 인증 정보 만들기** > **OAuth 2.0 클라이언트 ID**
2. **애플리케이션 유형**: "iOS" 선택
3. **이름**: "K-Digital iOS Client"
4. **번들 ID**: `tuk.kdigital.login`

## 📍 2단계: 앱 설정 업데이트

### 2.1 app.json 설정
```json
{
  "expo": {
    "name": "K-Digital",
    "slug": "K-Digital",
    "scheme": "kdigital",
    "ios": {
      "bundleIdentifier": "tuk.kdigital.login",
      "infoPlist": {
        "CFBundleURLTypes": [
          {
            "CFBundleURLName": "Google OAuth",
            "CFBundleURLSchemes": ["kdigital"]
          }
        ]
      }
    },
    "android": {
      "package": "tuk.kdigital.login",
      "intentFilters": [
        {
          "action": "VIEW",
          "autoVerify": true,
          "data": [
            {
              "scheme": "kdigital"
            }
          ],
          "category": ["BROWSABLE", "DEFAULT"]
        }
      ]
    },
    "extra": {
      "googleWebClientId": "YOUR_WEB_CLIENT_ID.apps.googleusercontent.com",
      "googleIosClientId": "YOUR_IOS_CLIENT_ID.apps.googleusercontent.com",
      "googleAndroidClientId": "YOUR_ANDROID_CLIENT_ID.apps.googleusercontent.com"
    }
  }
}
```

### 2.2 Client ID 설정
Google Cloud Console에서 받은 Client ID를 `app.json`의 `extra` 섹션에 설정:

```json
"extra": {
  "googleWebClientId": "473996282426-fp1hmcggelgkvotg4p9gumtr4hn2o.apps.googleusercontent.com",
  "googleIosClientId": "YOUR_IOS_CLIENT_ID_HERE",
  "googleAndroidClientId": "YOUR_ANDROID_CLIENT_ID_HERE"
}
```

## 📍 3단계: 개발 환경별 Redirect URI

### 3.1 Expo Go (개발용)
```
https://auth.expo.io/@username/K-Digital
```

### 3.2 Development Build (개발용)
```
kdigital://oauthredirect
```

### 3.3 Production Build (배포용)
```
kdigital://oauthredirect
```

### 3.4 Web (개발용)
```
http://localhost:19000/--/auth/google/callback
```

### 3.5 Web (배포용)
```
https://your-domain.com/auth/google/callback
```

## 📍 4단계: Google Cloud Console Redirect URI 등록

### 4.1 Web Client 설정
**승인된 리디렉션 URI**에 다음 추가:
```
http://localhost:19000/--/auth/google/callback
https://your-domain.com/auth/google/callback
```

### 4.2 Android Client 설정
**패키지 이름**: `tuk.kdigital.login`
**SHA-1 인증서 지문**: 개발용/프로덕션용 각각 추가

### 4.3 iOS Client 설정
**번들 ID**: `tuk.kdigital.login`

## 📍 5단계: 테스트 및 검증

### 5.1 개발 환경 테스트
```bash
# Expo Go로 테스트
expo start

# Development Build로 테스트
expo run:ios
expo run:android
```

### 5.2 로그 확인
개발자 도구에서 다음 로그 확인:
```
🔍 [GOOGLE AUTH] 구글 로그인 시작
  🆔 Client ID: [플랫폼별 ID]
  🔗 Redirect URI: [플랫폼별 URI]
✅ [GOOGLE AUTH] 인증 코드 획득 성공
✅ [GOOGLE AUTH] 토큰 교환 성공
✅ [GOOGLE AUTH] 백엔드 검증 성공
```

## 📍 6단계: 문제 해결

### 6.1 404 에러 (리디렉션 URI 오류)
- Google Cloud Console의 Redirect URI가 정확한지 확인
- 플랫폼별 Client ID가 올바른지 확인
- scheme 설정이 올바른지 확인

### 6.2 인증 실패
- OAuth 동의 화면 설정 확인
- 테스트 사용자 추가 (외부 앱의 경우)
- Client ID가 올바른지 확인

### 6.3 토큰 검증 실패
- 백엔드 로그에서 Google API 응답 확인
- ID Token이 올바른지 확인
- 네트워크 연결 상태 확인

## 📍 7단계: 보안 고려사항

### 7.1 PKCE 플로우 사용
- Authorization Code Flow with PKCE 사용
- 클라이언트 시크릿 노출 방지

### 7.2 백엔드 검증
- 프론트엔드에서 받은 토큰을 백엔드에서 Google API로 재검증
- ID Token의 유효성과 만료 시간 확인

### 7.3 HTTPS 필수
- 프로덕션 환경에서는 반드시 HTTPS 사용
- HTTP는 localhost 개발 환경에서만 허용

## 📍 8단계: 배포 준비

### 8.1 Production Build
```bash
# iOS
eas build --platform ios

# Android
eas build --platform android
```

### 8.2 App Store/Play Store 등록
- 각 플랫폼의 정책에 맞는 설정
- 개인정보 처리방침 URL 설정
- 앱 심사 가이드라인 준수

### 8.3 도메인 설정
- 프로덕션 도메인을 Google Cloud Console에 등록
- SSL 인증서 설정
- DNS 설정 확인

---

## 🎯 핵심 체크리스트

- [ ] Google Cloud Console에서 3개 플랫폼별 Client ID 생성
- [ ] app.json에 플랫폼별 Client ID 설정
- [ ] 올바른 Redirect URI 등록
- [ ] OAuth 동의 화면 설정
- [ ] 테스트 사용자 추가 (외부 앱)
- [ ] 백엔드 Google ID Token 검증 구현
- [ ] 개발/프로덕션 환경 테스트
- [ ] 보안 설정 확인

이 설정을 완료하면 iOS, Android, Web 모든 플랫폼에서 안전하고 일관된 Google 로그인을 사용할 수 있습니다. 