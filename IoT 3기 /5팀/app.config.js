import { ExpoConfig } from 'expo/config';

export default ({ config }) => ({
    ...config,
    name: 'TIBO',
    slug: 'tibo-robo-camera',
    version: '1.0.0',
    orientation: 'portrait',
    icon: './assets/icon.png',
    userInterfaceStyle: 'automatic',
    splash: {
        image: './assets/icon.png',
        resizeMode: 'contain',
        backgroundColor: '#4A90E2'
    },
    assetBundlePatterns: [
        '**/*'
    ],
    ios: {
        supportsTablet: true,
        bundleIdentifier: 'com.tibo.robo-camera',
        buildNumber: '1',
        infoPlist: {
            NSCameraUsageDescription: 'TIBO needs camera access to provide live video streaming and recording capabilities.',
            NSMicrophoneUsageDescription: 'TIBO needs microphone access for two-way audio communication with cameras.',
            NSLocationWhenInUseUsageDescription: 'TIBO uses location to help identify camera locations and provide contextual information.',
            NSPhotoLibraryUsageDescription: 'TIBO needs photo library access to save captured images and recordings.',
            NSPhotoLibraryAddUsageDescription: 'TIBO saves captured images and recordings to your photo library.',
            // 생체인증 관련 권한 추가
            NSFaceIDUsageDescription: 'TIBO uses Face ID to securely unlock the app.',
            UIBackgroundModes: [
                'audio',
                'fetch',
                'remote-notification'
            ],
            UIRequiresPersistentWiFi: true,
            UIStatusBarStyle: 'light-content',
            // ATS 예외: 개발용 HTTP 통신 허용
            NSAppTransportSecurity: {
                NSAllowsArbitraryLoads: true,
                NSExceptionDomains: {
                    '192.168.0.8': {
                        NSExceptionAllowsInsecureHTTPLoads: true,
                        NSIncludesSubdomains: true,
                    },
                    '192.168.0.9': {
                        NSExceptionAllowsInsecureHTTPLoads: true,
                        NSIncludesSubdomains: true,
                    },
                },
            },
        },
    },
    android: {
        adaptiveIcon: {
            foregroundImage: './assets/adaptive-icon.png',
            backgroundColor: '#4A90E2'
        },
        package: 'com.tibo.robocamera',
        versionCode: 1,
        permissions: [
            'android.permission.CAMERA',
            'android.permission.RECORD_AUDIO',
            'android.permission.ACCESS_FINE_LOCATION',
            'android.permission.ACCESS_COARSE_LOCATION',
            'android.permission.WRITE_EXTERNAL_STORAGE',
            'android.permission.READ_EXTERNAL_STORAGE',
            'android.permission.INTERNET',
            'android.permission.ACCESS_NETWORK_STATE',
            'android.permission.WAKE_LOCK',
            'android.permission.FOREGROUND_SERVICE',
            'android.permission.VIBRATE'
        ],
        intentFilters: [
            {
                action: 'VIEW',
                data: [
                    {
                        scheme: 'tibo',
                        host: 'camera'
                    }
                ],
                category: ['BROWSABLE', 'DEFAULT']
            }
        ]
    },
    web: {
        favicon: './assets/favicon.png',
        bundler: 'metro'
    },
    plugins: [
        "expo-video",
        [
            'expo-camera',
            {
                cameraPermission: 'Allow TIBO to access your camera for live streaming and recording.',
                microphonePermission: 'Allow TIBO to access your microphone for two-way audio.'
            }
        ],
        [
            'expo-splash-screen',
            {
                image: './assets/icon.png',
                resizeMode: 'contain',
                backgroundColor: '#4A90E2'
            }
        ]
    ],
    extra: {
        eas: {
            projectId: 'your-project-id'
        },
        apiUrl: process.env.EXPO_PUBLIC_API_URL || 'http://localhost:3000',
        websocketUrl: process.env.EXPO_PUBLIC_WEBSOCKET_URL || 'ws://localhost:3000',
        mqttWsUrl: process.env.EXPO_PUBLIC_MQTT_WS_URL || 'ws://localhost:8083/mqtt',
        mqttUsername: process.env.EXPO_PUBLIC_MQTT_USERNAME || 'tibo',
        mqttPassword: process.env.EXPO_PUBLIC_MQTT_PASSWORD || 'tibo123',
        turnServer: process.env.EXPO_PUBLIC_TURN_SERVER || 'stun:localhost:3478',
        googleWebClientId: '706502232476-22nfajuo4f4luvs0n8ofp9h1svjd1s9m.apps.googleusercontent.com',
        googleIosClientId: '706502232476-22nfajuo4f4luvs0n8ofp9h1svjd1s9m.apps.googleusercontent.com',
        googleAndroidClientId: '706502232476-22nfajuo4f4luvs0n8ofp9h1svjd1s9m.apps.googleusercontent.com'
    },
    experiments: {
        tsconfigPaths: true
    },
    // Performance optimizations
    metro: {
        transformer: {
            getTransformOptions: async () => ({
                transform: {
                    experimentalImportSupport: false,
                    inlineRequires: true,
                },
            }),
        },
    },
    // Hermes engine for better performance
    jsEngine: 'hermes',
    // Enable new architecture
    newArchEnabled: true,
    // Bundle splitting for better performance
    bundleSplitting: true,
    // Enable tree shaking
    treeShaking: true,
    // Optimize images
    imageOptimization: {
        enabled: true,
        quality: 0.8
    },
    // Enable code splitting
    codeSplitting: {
        enabled: true,
        strategy: 'all'
    },
    // Cache configuration
    cache: {
        enabled: true,
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        maxSize: 100 * 1024 * 1024 // 100MB
    },
    // Network optimization
    network: {
        timeout: 30000,
        retries: 3,
        cachePolicy: 'cache-first'
    },
    // Security configuration
    security: {
        certificatePinning: true,
        sslPinning: true,
        jailbreakDetection: true
    },
    // Analytics and monitoring
    analytics: {
        enabled: true,
        provider: 'expo',
        events: [
            'app_open',
            'camera_connect',
            'recording_start',
            'ptz_command',
            'event_detected'
        ]
    },
    // Error reporting
    errorReporting: {
        enabled: true,
        provider: 'expo',
        includeSourceMaps: false
    },
    // Performance monitoring
    performance: {
        enabled: true,
        provider: 'expo',
        metrics: [
            'app_start_time',
            'bundle_load_time',
            'api_response_time',
            'video_stream_latency'
        ]
    }
}); 